"""Spec §21 Safha 8: AI-generated video scenes + voice-over TTS.

Video: the `submit -> poll -> download` cycle Safha 3 built and
contract-tested against OpenRouter's real (documented, no-key-needed)
`/videos*` endpoints, but never exercised live because no key existed at
the time. Only `source_type == "ai_generated"` shots go through this path
— `gameplay` shots use `app.services.capture` instead.

Voice: ElevenLabs `synthesize()`, likewise built and contract-tested in
Safha 3 (`list_voices()` was verified live once a real key existed) but
never exercised end-to-end. A voice-over asset is not tied to a specific
Take — a shot can be gameplay *and* have a voice-over — so it is stored as
its own `Asset` tagged with the shot id in `metadata_json`, not as a Take.
"""

import hashlib
import time
import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.director import generate_scene_prompt
from app.media import technical_qc
from app.models.asset import Asset
from app.models.creative import Revision, Shot, Take
from app.providers.base import SpeechProvider, TextVisionProvider, VideoGenerationRequest, VideoProvider
from app.services import projects as projects_service
from app.services.errors import BlockedError, NotFoundError, ValidationAppError

DEFAULT_POLL_INTERVAL_S = 5.0
DEFAULT_MAX_WAIT_S = 300.0
_ASSUMED_FPS = 30


def _get_shot_in_revision(session: Session, project_id: str, shot_id: str) -> Shot:
    shot = session.get(Shot, shot_id)
    if shot is None:
        raise NotFoundError(f"Shot {shot_id} not found", details={"shot_id": shot_id})
    revision = session.get(Revision, shot.revision_id)
    if revision is None or revision.project_id != project_id:
        raise NotFoundError(f"Shot {shot_id} not found for this project", details={"shot_id": shot_id})
    return shot


def _get_ai_shot(session: Session, project_id: str, shot_id: str) -> Shot:
    shot = _get_shot_in_revision(session, project_id, shot_id)
    if shot.source_type != "ai_generated":
        raise ValidationAppError(
            f"Shot {shot_id} is source_type='{shot.source_type}', not 'ai_generated'.",
            details={"shot_id": shot_id, "source_type": shot.source_type},
        )
    return shot


def _next_attempt(session: Session, shot_id: str) -> int:
    return (
        session.execute(select(func.coalesce(func.max(Take.attempt), 0)).where(Take.shot_id == shot_id)).scalar_one()
        + 1
    )


def generate_ai_scene_take(
    session: Session,
    project_id: str,
    shot_id: str,
    *,
    text_provider: TextVisionProvider,
    text_model: str,
    video_provider: VideoProvider,
    video_model: str,
    ratio: str = "9:16",
    resolution: str | None = None,
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
    max_wait_s: float = DEFAULT_MAX_WAIT_S,
) -> Take:
    project = projects_service.get_project(session, project_id)
    shot = _get_ai_shot(session, project_id, shot_id)
    brand = projects_service.get_brand_profile(session, project_id)
    if brand is None:
        raise ValidationAppError("Marka bilgisi kaydedilmeden sahne üretilemez.", details={"shot_id": shot_id})

    if not shot.generation_prompt:
        shot.generation_prompt = generate_scene_prompt(text_provider, text_model, shot=shot, brand=brand)
        session.commit()
        session.refresh(shot)

    duration_s = max(shot.target_frames / _ASSUMED_FPS, 1.0)
    request = VideoGenerationRequest(
        model_id=video_model, prompt=shot.generation_prompt, duration_s=duration_s, ratio=ratio, resolution=resolution
    )
    validation = video_provider.validate_request(request)
    if not validation.ok:
        raise ValidationAppError(
            f"Video üretim isteği geçersiz: {'; '.join(validation.errors)}",
            details={"errors": validation.errors},
        )

    attempt = _next_attempt(session, shot_id)
    remote_id = video_provider.submit(request, idempotency_key=f"{shot_id}-attempt{attempt}")

    started = time.monotonic()
    result = video_provider.poll(remote_id)
    while result.state in ("queued", "running") and (time.monotonic() - started) < max_wait_s:
        time.sleep(poll_interval_s)
        result = video_provider.poll(remote_id)

    if result.state != "completed":
        raise BlockedError(
            f"Video üretimi tamamlanamadı (durum: {result.state}, hata: {result.error})",
            details={"remote_id": remote_id, "state": result.state, "error": result.error},
        )

    generated_dir = Path(project.root_path) / "generated" / "video"
    generated_dir.mkdir(parents=True, exist_ok=True)
    destination = generated_dir / f"shot-{shot.id}-take{attempt}.mp4"
    video_provider.download(remote_id, destination)

    report = technical_qc.run_technical_qc(destination)
    digest = hashlib.sha256()
    with destination.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    duration_us = int(report.probe.duration_s * 1_000_000) if report.probe else None
    asset = Asset(
        project_id=project_id,
        type="video",
        origin="provider_generation",
        relative_path=str(destination.relative_to(Path(project.root_path))),
        sha256=digest.hexdigest(),
        byte_size=destination.stat().st_size,
        duration_us=duration_us,
        dimensions_json={"width": report.probe.width, "height": report.probe.height} if report.probe else {},
        metadata_json={
            "technical_qc": {"outcome": report.outcome, "checks": report.checks, "errors": report.errors},
            "provider": {
                "model": video_model,
                "remote_id": remote_id,
                "prompt": shot.generation_prompt,
                # Real, provider-confirmed spend (OpenRouter's `usage.cost`)
                # — never an estimate. None when the provider didn't report one.
                "actual_cost_usd": result.cost_usd,
            },
        },
    )
    session.add(asset)
    session.flush()

    if report.outcome == "fail":
        status = "rejected"
    elif report.outcome == "uncertain":
        status = "uncertain"
    else:
        status = "pending"

    take = Take(
        shot_id=shot.id,
        asset_id=asset.id,
        attempt=attempt,
        status=status,
        in_us=0,
        out_us=duration_us or 0,
        event_evidence_json={"video_generation": {"remote_id": remote_id, "model": video_model}},
        quality_json={"technical_qc": {"outcome": report.outcome, "checks": report.checks}},
        rejection_reason=f"Teknik QC başarısız: {report.checks}" if status == "rejected" else None,
    )
    session.add(take)
    session.commit()
    session.refresh(take)
    return take


def generate_voice_asset(
    session: Session,
    project_id: str,
    shot_id: str,
    *,
    speech_provider: SpeechProvider,
    voice_id: str,
    language: str | None = None,
) -> Asset:
    project = projects_service.get_project(session, project_id)
    shot = _get_shot_in_revision(session, project_id, shot_id)
    if not shot.voice_text:
        raise ValidationAppError("Bu sahne için seslendirme metni yok.", details={"shot_id": shot_id})

    brief = projects_service.get_latest_brief(session, project_id)
    resolved_language = language or (brief.language if brief else "tr")

    audio_bytes = speech_provider.synthesize(shot.voice_text, voice_id, resolved_language)

    audio_dir = Path(project.root_path) / "audio" / "voice"
    audio_dir.mkdir(parents=True, exist_ok=True)
    destination = audio_dir / f"shot-{shot.id}-voice-{uuid.uuid4().hex[:8]}.mp3"
    destination.write_bytes(audio_bytes)

    try:
        probe = technical_qc.probe_media(destination)
        duration_us = int(probe.duration_s * 1_000_000) if probe.duration_s else None
    except technical_qc.ToolMissingError:
        duration_us = None

    asset = Asset(
        project_id=project_id,
        type="audio",
        origin="provider_generation",
        relative_path=str(destination.relative_to(Path(project.root_path))),
        sha256=hashlib.sha256(audio_bytes).hexdigest(),
        byte_size=len(audio_bytes),
        duration_us=duration_us,
        metadata_json={
            "shot_id": shot.id,
            "role": "voice_over",
            "voice_id": voice_id,
            "language": resolved_language,
            "text": shot.voice_text,
        },
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset
