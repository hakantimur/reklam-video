"""Spec §21 Safha 7: real gameplay shot capture.

Reuses the vision-based operator loop that Safha 5 discovery already
verified live (same `OperatorDecision` schema — `finish_discovery` here
means "this shot's desired event is captured", not "I understand the game"),
but now records real video underneath via `CaptureManager` and persists a
real `Asset`/`Take` pair at the end, technical-QC'd like any other clip
(spec 12.2).

Only `source_type == "gameplay"` shots go through this path. `ai_generated`
shots need a video-generation provider call instead of device control and
are explicitly out of scope here (see docs/KNOWN_LIMITATIONS.md).
"""

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents import operator as operator_agent
from app.device import adb
from app.device.actions import DeviceController, StaleObservationError
from app.device.capture import CaptureManager
from app.media import technical_qc
from app.models.asset import Asset
from app.models.creative import Revision, Shot, Take
from app.models.device import DeviceProfile, GameProfile
from app.providers.base import TextVisionProvider
from app.services import projects as projects_service
from app.services.errors import BlockedError, NotFoundError, ValidationAppError

DEFAULT_MAX_ACTIONS = 30
DEFAULT_MAX_SECONDS = 180
_ASSUMED_FPS = 30  # only used to size the action/time budget, never written to the Asset


class CaptureTakeoverRequested(RuntimeError):
    """The operator asked a human to take over (spec §11.8) mid-capture.
    Unlike a plain crash, the partial recording is kept and persisted as a
    rejected Take rather than silently discarded — evidence over silence."""

    def __init__(self, note: str | None, take_id: str | None):
        super().__init__(note or "request_takeover")
        self.note = note
        self.take_id = take_id


def _get_shot(session: Session, project_id: str, shot_id: str) -> Shot:
    shot = session.get(Shot, shot_id)
    if shot is None:
        raise NotFoundError(f"Shot {shot_id} not found", details={"shot_id": shot_id})
    revision = session.get(Revision, shot.revision_id)
    if revision is None or revision.project_id != project_id:
        raise NotFoundError(f"Shot {shot_id} not found for this project", details={"shot_id": shot_id})
    if shot.source_type != "gameplay":
        raise ValidationAppError(
            f"Shot {shot_id} is source_type='{shot.source_type}', not 'gameplay' — this "
            "capture path only drives real device gameplay.",
            details={"shot_id": shot_id, "source_type": shot.source_type},
        )
    return shot


def _latest_game_profile(session: Session, project_id: str) -> GameProfile:
    profile = (
        session.execute(
            select(GameProfile)
            .where(GameProfile.project_id == project_id)
            .order_by(GameProfile.created_at.desc())
        )
        .scalars()
        .first()
    )
    if profile is None:
        raise ValidationAppError(
            "Çekim yapmadan önce Keşif adımıyla bu proje için bir GameProfile üretilmelidir.",
            details={"project_id": project_id},
        )
    return profile


def _next_attempt(session: Session, shot_id: str) -> int:
    return (
        session.execute(select(func.coalesce(func.max(Take.attempt), 0)).where(Take.shot_id == shot_id)).scalar_one()
        + 1
    )


def _capture_goal(shot: Shot) -> str:
    parts = [f"Purpose: {shot.purpose}."]
    if shot.desired_event:
        parts.append(f"Capture this specific event: {shot.desired_event}.")
    if shot.success_predicate_json:
        parts.append(f"Success predicate: {shot.success_predicate_json}.")
    parts.append(
        "This is a real ad shot capture, not exploration — once the desired event has "
        "visibly happened on screen, use finish_discovery to end the take."
    )
    return " ".join(parts)


def _execute_action(controller: DeviceController, observation, decision: operator_agent.OperatorDecision) -> None:
    action = decision.action
    if action.type == "tap":
        controller.tap(observation, action.x or 0.5, action.y or 0.5)
    elif action.type == "swipe":
        controller.swipe(
            observation,
            action.x or 0.5,
            action.y or 0.5,
            action.x2 or 0.5,
            action.y2 or 0.5,
            action.duration_ms or 300,
        )
    elif action.type == "press_back":
        controller.press_back(observation)
    elif action.type == "wait":
        time.sleep(min((action.duration_ms or 1000) / 1000, 5.0))


def _finalize_take(
    session: Session,
    *,
    project_root: Path,
    project_id: str,
    shot: Shot,
    attempt: int,
    video_path: Path,
    actions_log: list[dict],
    status_override: str | None = None,
    rejection_reason: str | None = None,
) -> Take:
    report = technical_qc.run_technical_qc(video_path)

    digest = hashlib.sha256()
    with video_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    duration_us = int(report.probe.duration_s * 1_000_000) if report.probe else None
    asset = Asset(
        project_id=project_id,
        type="video",
        origin="emulator_capture",
        relative_path=str(video_path.relative_to(project_root)),
        sha256=digest.hexdigest(),
        byte_size=video_path.stat().st_size,
        duration_us=duration_us,
        dimensions_json={"width": report.probe.width, "height": report.probe.height} if report.probe else {},
        metadata_json={"technical_qc": {"outcome": report.outcome, "checks": report.checks, "errors": report.errors}},
    )
    session.add(asset)
    session.flush()

    if status_override is not None:
        status = status_override
    elif report.outcome == "fail":
        status = "rejected"
    elif report.outcome == "uncertain":
        status = "uncertain"
    else:
        status = "pending"

    if rejection_reason is None and status == "rejected" and report.outcome == "fail":
        rejection_reason = f"Teknik QC başarısız: {report.checks}"

    take = Take(
        shot_id=shot.id,
        asset_id=asset.id,
        attempt=attempt,
        status=status,
        in_us=0,
        out_us=duration_us or 0,
        event_evidence_json={"actions_log": actions_log},
        quality_json={"technical_qc": {"outcome": report.outcome, "checks": report.checks}},
        rejection_reason=rejection_reason,
    )
    session.add(take)
    session.commit()
    session.refresh(take)
    return take


def capture_gameplay_shot(
    session: Session,
    project_id: str,
    shot_id: str,
    *,
    serial: str,
    provider: TextVisionProvider,
    model: str,
    max_actions: int = DEFAULT_MAX_ACTIONS,
    max_seconds: int = DEFAULT_MAX_SECONDS,
    capture_manager: CaptureManager | None = None,
) -> Take:
    project = projects_service.get_project(session, project_id)
    shot = _get_shot(session, project_id, shot_id)
    game_profile = _latest_game_profile(session, project_id)
    device_profile = session.get(DeviceProfile, game_profile.device_profile_id)
    package_id = device_profile.package_id if device_profile else None
    if not package_id:
        raise ValidationAppError("GameProfile için paket kimliği bilinmiyor.", details={"shot_id": shot_id})

    devices = {d.serial: d for d in adb.list_devices()}
    if serial not in devices or devices[serial].state != "device":
        raise BlockedError(f"Device {serial} is not connected", details={"serial": serial})

    adb.launch_app(serial, package_id)
    time.sleep(2)

    manager = capture_manager or CaptureManager()
    controller = DeviceController(serial)
    project_root = Path(project.root_path)
    capture_dir = project_root / "captures" / "raw"
    attempt = _next_attempt(session, shot_id)
    recording_name = f"shot-{shot.id}-take{attempt}"

    goal = _capture_goal(shot)
    working_memory: dict = {}
    actions_log: list[dict] = []
    started_at = time.monotonic()
    takeover_note: str | None = None

    # Budget: give real gameplay room to reach the desired event, bounded by
    # a generous multiple of the shot's target duration plus a hard ceiling.
    time_budget = min(max(max_seconds, (shot.target_frames / _ASSUMED_FPS) * 4), max_seconds)

    manager.start_recording(serial, capture_dir, recording_name)
    manager.mark_event(serial, "capture_started", {"shot_id": shot.id, "goal": shot.purpose})

    actions_taken = 0
    try:
        while actions_taken < max_actions and (time.monotonic() - started_at) < time_budget:
            observation = controller.observe()
            decision = operator_agent.decide_next_action(
                provider,
                model,
                screenshot_png=observation.png_bytes,
                package_id=package_id,
                working_memory=working_memory,
                actions_taken=actions_taken,
                max_actions=max_actions,
                discovery_goal=goal,
            )
            working_memory.update(decision.memory_update)
            actions_log.append(
                {
                    "index": actions_taken,
                    "screen_classification": decision.screen_classification,
                    "reasoning": decision.reasoning,
                    "action": decision.action.model_dump(),
                }
            )

            if decision.action.type == "finish_discovery":
                manager.mark_event(serial, "desired_event_reached", {"note": decision.action.note})
                break
            if decision.action.type == "request_takeover":
                takeover_note = decision.action.note
                break

            try:
                _execute_action(controller, observation, decision)
                manager.mark_event(serial, "action", {"index": actions_taken, "action": decision.action.model_dump()})
            except StaleObservationError:
                continue
            actions_taken += 1
    finally:
        video_path = manager.stop_recording(serial)

    if takeover_note is not None:
        take = _finalize_take(
            session,
            project_root=project_root,
            project_id=project_id,
            shot=shot,
            attempt=attempt,
            video_path=video_path,
            actions_log=actions_log,
            status_override="rejected",
            rejection_reason=f"Kontrol devri istendi: {takeover_note}",
        )
        raise CaptureTakeoverRequested(takeover_note, take.id)

    if not actions_log:
        raise ValidationAppError("Capture loop produced no actions before the budget ran out.")

    return _finalize_take(
        session,
        project_root=project_root,
        project_id=project_id,
        shot=shot,
        attempt=attempt,
        video_path=video_path,
        actions_log=actions_log,
    )
