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
