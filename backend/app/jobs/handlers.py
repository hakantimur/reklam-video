"""Job kind -> handler registry, plus a synchronous single-step worker runner.

Spec 2.3 forbids fake/placeholder behavior ("her zaman success dönen sahte
job yok"), so `dummy_echo` is not a lie: it is a real, minimal job kind that
genuinely reads its payload and returns it — proving the engine's
claim/execute/complete/event-log path end to end — rather than a handler
that unconditionally reports success without doing anything. Real
production kinds (`discover`, `plan`, `produce`, ...) register themselves
the same way in later rounds; none of that domain logic is in scope here.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.jobs.queue import JobQueue, job_queue
from app.models.jobs import Job
from app.services.events import append_event

JobHandler = Callable[[Session, Job], dict]

JOB_HANDLERS: dict[str, JobHandler] = {}


def register_handler(kind: str) -> Callable[[JobHandler], JobHandler]:
    def _decorator(func: JobHandler) -> JobHandler:
        JOB_HANDLERS[kind] = func
        return func

    return _decorator


@register_handler("dummy_echo")
def _dummy_echo(session: Session, job: Job) -> dict:
    return {"echo": job.payload_json}


@register_handler("discover")
def _discover(session: Session, job: Job) -> dict:
    """Spec §8.1 POST /projects/{id}/discover, run out-of-band since a real
    discovery pass can take up to spec §3.2's 10-minute budget."""

    from app.providers.openrouter import OpenRouterClient, OpenRouterTextVisionProvider
    from app.services import credentials as credentials_service
    from app.services import discovery as discovery_service
    from app.services.errors import BlockedError

    payload = job.payload_json
    api_key = credentials_service.get_credential_value("openrouter")
    if not api_key:
        raise BlockedError("OpenRouter API anahtarı olmadan keşif çalıştırılamaz.")

    client = OpenRouterClient(api_key=api_key)
    try:
        provider = OpenRouterTextVisionProvider(client)
        game_profile = discovery_service.run_discovery(
            session,
            job.project_id,
            serial=payload["serial"],
            package_id=payload["package_id"],
            provider=provider,
            model=payload.get("model", "anthropic/claude-haiku-4.5"),
            max_actions=payload.get("max_actions", discovery_service.DEFAULT_MAX_ACTIONS),
            max_seconds=payload.get("max_seconds", discovery_service.DEFAULT_MAX_SECONDS),
        )
    finally:
        client.close()

    return {
        "game_profile_id": game_profile.id,
        "mechanic_summary": game_profile.mechanic_summary,
        "confidence": game_profile.confidence,
    }


@register_handler("capture_shot")
def _capture_shot(session: Session, job: Job) -> dict:
    """Spec §8.1 POST /projects/{id}/shots/{shot_id}/capture (Safha 7)."""

    from app.providers.openrouter import OpenRouterClient, OpenRouterTextVisionProvider
    from app.services import capture as capture_service
    from app.services import credentials as credentials_service
    from app.services.errors import BlockedError

    payload = job.payload_json
    api_key = credentials_service.get_credential_value("openrouter")
    if not api_key:
        raise BlockedError("OpenRouter API anahtarı olmadan çekim yapılamaz.")

    client = OpenRouterClient(api_key=api_key)
    try:
        provider = OpenRouterTextVisionProvider(client)
        take = capture_service.capture_gameplay_shot(
            session,
            job.project_id,
            payload["shot_id"],
            serial=payload["serial"],
            provider=provider,
            model=payload.get("model", "anthropic/claude-haiku-4.5"),
            max_actions=payload.get("max_actions", capture_service.DEFAULT_MAX_ACTIONS),
            max_seconds=payload.get("max_seconds", capture_service.DEFAULT_MAX_SECONDS),
        )
    finally:
        client.close()

    return {
        "take_id": take.id,
        "asset_id": take.asset_id,
        "status": take.status,
        "attempt": take.attempt,
    }


@register_handler("generate_ai_scene")
def _generate_ai_scene(session: Session, job: Job) -> dict:
    """Spec §8.1 POST /projects/{id}/shots/{shot_id}/generate-scene (Safha 8)."""

    from app.providers.openrouter import OpenRouterClient, OpenRouterTextVisionProvider, OpenRouterVideoProvider
    from app.services import credentials as credentials_service
    from app.services import generation as generation_service
    from app.services.errors import BlockedError

    payload = job.payload_json
    api_key = credentials_service.get_credential_value("openrouter")
    if not api_key:
        raise BlockedError("OpenRouter API anahtarı olmadan AI sahne üretilemez.")

    client = OpenRouterClient(api_key=api_key)
    try:
        take = generation_service.generate_ai_scene_take(
            session,
            job.project_id,
            payload["shot_id"],
            text_provider=OpenRouterTextVisionProvider(client),
            text_model=payload.get("text_model", "anthropic/claude-haiku-4.5"),
            video_provider=OpenRouterVideoProvider(client),
            video_model=payload["video_model"],
            ratio=payload.get("ratio", "9:16"),
            resolution=payload.get("resolution"),
        )
    finally:
        client.close()

    _settle_real_cost(session, job, asset_id=take.asset_id)

    return {"take_id": take.id, "asset_id": take.asset_id, "status": take.status, "attempt": take.attempt}


def _settle_real_cost(session: Session, job: Job, *, asset_id: str) -> None:
    """Best-effort: record the video provider's own confirmed spend
    (`Asset.metadata_json.provider.actual_cost_usd`, from OpenRouter's
    `usage.cost` — never an estimate) as a `BudgetEntry` settlement.
    Deliberately never lets a bookkeeping failure fail an otherwise
    successful generation job — this is real spend tracking, not a gate."""

    from app.models.asset import Asset
    from app.services import budget as budget_service

    try:
        asset = session.get(Asset, asset_id)
        if asset is None:
            return
        cost_usd = (asset.metadata_json or {}).get("provider", {}).get("actual_cost_usd")
        if not cost_usd:
            return
        budget_service.settle(
            session, job.project_id, job_id=job.id, actual_amount_microusd=round(cost_usd * 1_000_000)
        )
    except Exception:  # noqa: BLE001 - spend bookkeeping must never fail a real, already-succeeded job
        logging.getLogger(__name__).exception("Failed to settle real cost for job %s", job.id)


@register_handler("generate_voice")
def _generate_voice(session: Session, job: Job) -> dict:
    """Spec §8.1 POST /projects/{id}/shots/{shot_id}/generate-voice (Safha 8)."""

    from app.providers.elevenlabs import ElevenLabsProvider
    from app.services import credentials as credentials_service
    from app.services import generation as generation_service
    from app.services.errors import BlockedError

    payload = job.payload_json
    api_key = credentials_service.get_credential_value("elevenlabs")
    if not api_key:
        raise BlockedError("ElevenLabs API anahtarı olmadan seslendirme üretilemez.")

    provider = ElevenLabsProvider(api_key=api_key)
    try:
        asset = generation_service.generate_voice_asset(
            session,
            job.project_id,
            payload["shot_id"],
            speech_provider=provider,
            voice_id=payload["voice_id"],
            language=payload.get("language"),
        )
    finally:
        provider.close()

    return {"asset_id": asset.id, "byte_size": asset.byte_size}


@register_handler("render_preview")
def _render_preview(session: Session, job: Job) -> dict:
    """Spec §8.1 POST /projects/{id}/render/preview (Safha 9)."""

    from app.services import render as render_service

    asset = render_service.render_preview_job(session, job.project_id)
    return {"asset_id": asset.id, "byte_size": asset.byte_size, "duration_us": asset.duration_us}


@register_handler("export_final")
def _export_final(session: Session, job: Job) -> dict:
    """Spec §8.1 POST /projects/{id}/revisions/{revision_id}/export (Safha 11)."""

    from app.services import export as export_service

    asset = export_service.export_final(session, job.project_id, job.payload_json["revision_id"])
    return {"asset_id": asset.id, "byte_size": asset.byte_size, "duration_us": asset.duration_us}


@register_handler("review_take")
def _review_take(session: Session, job: Job) -> dict:
    """Spec §8.1 POST /projects/{id}/shots/{shot_id}/review (Safha 10/11)."""

    from app.providers.openrouter import OpenRouterClient, OpenRouterTextVisionProvider
    from app.services import credentials as credentials_service
    from app.services import review as review_service
    from app.services.errors import BlockedError

    payload = job.payload_json
    api_key = credentials_service.get_credential_value("openrouter")
    if not api_key:
        raise BlockedError("OpenRouter API anahtarı olmadan içerik incelemesi yapılamaz.")

    client = OpenRouterClient(api_key=api_key)
    try:
        report = review_service.review_shot_take(
            session,
            job.project_id,
            payload["shot_id"],
            provider=OpenRouterTextVisionProvider(client),
            model=payload.get("model", "anthropic/claude-haiku-4.5"),
        )
    finally:
        client.close()

    return {
        "report_id": report.id,
        "outcome": report.outcome,
        "reasoning": report.checks_json.get("reasoning"),
        "defects": report.checks_json.get("defects"),
    }


def run_worker_once(
    session: Session, *, queue: JobQueue = job_queue, kinds: list[str] | None = None
) -> Job | None:
    """Claim and fully execute at most one job. Returns `None` if the queue
    was empty. Intended to be called in a loop from a worker thread/process;
    kept synchronous and single-step so it is trivial to drive from tests."""

    job = queue.claim_next(session, kinds=kinds)
    if job is None:
        return None

    append_event(session, project_id=job.project_id, job_id=job.id, type="job.started", payload={"kind": job.kind})
    handler = JOB_HANDLERS.get(job.kind)
    if handler is None:
        job = queue.fail(session, job.id, error_code="unknown_job_kind")
        append_event(
            session,
            project_id=job.project_id,
            job_id=job.id,
            type="job.failed",
            payload={"error_code": "unknown_job_kind"},
        )
        return job

    try:
        result = handler(session, job)
    except Exception as exc:  # noqa: BLE001 - any handler failure becomes a recorded job failure, not a crash
        job = queue.fail(session, job.id, error_code="handler_error")
        append_event(
            session, project_id=job.project_id, job_id=job.id, type="job.failed", payload={"error": str(exc)}
        )
        return job

    job = queue.complete(session, job.id, result=result)
    append_event(session, project_id=job.project_id, job_id=job.id, type="job.succeeded", payload={"result": result})
    return job
