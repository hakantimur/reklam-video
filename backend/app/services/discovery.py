"""Spec §11.3/§21 Safha 5: bounded autonomous game discovery.

Explicitly NOT a shot capture — spec §4.4: "Keşif kayıtları reklam çekimi
olarak otomatik kabul edilmez" (discovery footage is never auto-accepted as
ad footage), so this loop never records video, only observes and acts to
build a `GameProfile`.
"""

import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import operator as operator_agent
from app.agents.director import generate_game_profile_summary
from app.device import adb
from app.device.actions import DeviceController, StaleObservationError
from app.models.device import DeviceProfile, GameProfile
from app.providers.base import TextVisionProvider
from app.services.errors import BlockedError, ValidationAppError

DEFAULT_MAX_ACTIONS = 60
DEFAULT_MAX_SECONDS = 600  # spec §3.2: 60 actions or 10 minutes, whichever first


class DiscoveryTakeoverRequested(RuntimeError):
    """The operator asked a human to take over (spec §11.8) — not a crash."""

    def __init__(self, note: str | None, actions_log: list[dict], working_memory: dict):
        super().__init__(note or "request_takeover")
        self.note = note
        self.actions_log = actions_log
        self.working_memory = working_memory


def _upsert_device_profile(session: Session, serial: str) -> DeviceProfile:
    profile = session.execute(
        select(DeviceProfile).where(DeviceProfile.serial == serial)
    ).scalar_one_or_none()

    width, height = adb.screen_size(serial)
    orientation = adb.orientation(serial)

    if profile is None:
        profile = DeviceProfile(serial=serial)
        session.add(profile)
    profile.width = width
    profile.height = height
    profile.orientation = orientation
    session.flush()
    return profile


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
    # finish_discovery / request_takeover are handled by the caller, not here.


def run_discovery(
    session: Session,
    project_id: str,
    *,
    serial: str,
    package_id: str,
    provider: TextVisionProvider,
    model: str,
    discovery_goal: str = "Learn the core gameplay mechanic well enough to plan a real ad shot.",
    max_actions: int = DEFAULT_MAX_ACTIONS,
    max_seconds: int = DEFAULT_MAX_SECONDS,
) -> GameProfile:
    devices = {d.serial: d for d in adb.list_devices()}
    if serial not in devices or devices[serial].state != "device":
        raise BlockedError(f"Device {serial} is not connected", details={"serial": serial})

    device_profile = _upsert_device_profile(session, serial)
    device_profile.package_id = package_id
    session.flush()

    adb.launch_app(serial, package_id)
    time.sleep(2)  # let the app cold-start before the first observation

    controller = DeviceController(serial)
    working_memory: dict = {}
    actions_log: list[dict] = []
    started_at = time.monotonic()
    takeover_note: str | None = None

    actions_taken = 0
    while actions_taken < max_actions and (time.monotonic() - started_at) < max_seconds:
        observation = controller.observe()
        decision = operator_agent.decide_next_action(
            provider,
            model,
            screenshot_png=observation.png_bytes,
            package_id=package_id,
            working_memory=working_memory,
            actions_taken=actions_taken,
            max_actions=max_actions,
            discovery_goal=discovery_goal,
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
            break
        if decision.action.type == "request_takeover":
            takeover_note = decision.action.note
            break

        try:
            _execute_action(controller, observation, decision)
        except StaleObservationError:
            continue  # re-observe next loop iteration rather than acting blind
        actions_taken += 1

    if takeover_note is not None:
        raise DiscoveryTakeoverRequested(takeover_note, actions_log, working_memory)

    if not actions_log:
        raise ValidationAppError("Discovery loop produced no actions to summarize.")

    summary = generate_game_profile_summary(
        provider, model, package_id=package_id, working_memory=working_memory, actions_log=actions_log
    )

    game_profile = GameProfile(
        project_id=project_id,
        device_profile_id=device_profile.id,
        mechanic_summary=summary.mechanic_summary,
        navigation_json=summary.navigation,
        state_signals_json=summary.state_signals,
        supported_actions_json=summary.supported_actions,
        confidence=summary.confidence,
        verified_at=datetime.now(timezone.utc),
    )
    session.add(game_profile)
    session.commit()
    session.refresh(game_profile)
    return game_profile
