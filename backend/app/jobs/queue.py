"""Persistent SQLite-backed job queue engine (spec 8.2, 8.3).

Designed to be driven from any Python thread or process that shares the
app's SQLite file (a real worker would run this loop on a background
thread or a separate process; this round wires up the engine itself plus
one dummy job kind — see `app/jobs/handlers.py` — end to end).

Claiming is a compare-and-swap: `UPDATE jobs SET state='running', ...
WHERE id=? AND state='queued'`, so only one caller's UPDATE can ever affect
a row — a second, racing caller's UPDATE affects zero rows and is told "no
job" rather than double-claiming. A process-local `threading.Lock` also
serializes claims made *within this process*, which removes a benign but
wasteful SELECT/UPDATE race between threads of the same worker. Note that
`app/core/db.py` is out of scope for this round's changes, so no
`PRAGMA busy_timeout` is configured there; a genuinely concurrent second
*process* writing to the same file could occasionally see "database is
locked" rather than waiting. Acceptable for a single-user local app with
effectively one worker process at a time; worth revisiting if multiple
worker processes become real.
"""

from __future__ import annotations

import threading
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.base import utcnow
from app.models.jobs import Job
from app.services.errors import ConflictError, NotFoundError
from app.services.events import append_event

TERMINAL_STATES = {"succeeded", "cancelled", "failed"}
_PAUSABLE_STATES = {"queued", "running", "waiting_provider", "blocked"}


def _get_job(session: Session, job_id: str) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise NotFoundError(f"Job {job_id} not found", details={"job_id": job_id})
    return job


class JobQueue:
    def __init__(self, worker_id: str = "worker-1") -> None:
        self.worker_id = worker_id
        self._claim_lock = threading.Lock()

    def enqueue(
        self,
        session: Session,
        *,
        project_id: str,
        kind: str,
        idempotency_key: str,
        payload: dict | None = None,
        revision_id: str | None = None,
        parent_id: str | None = None,
    ) -> Job:
        """Create a job, or return the existing one for a repeated
        `Idempotency-Key` (spec 8.3: `(project_id, idempotency_key)` is
        unique — a retried UI request must not double-enqueue work)."""

        existing = (
            session.execute(
                select(Job).where(Job.project_id == project_id, Job.idempotency_key == idempotency_key)
            )
            .scalars()
            .first()
        )
        if existing is not None:
            return existing

        job = Job(
            project_id=project_id,
            revision_id=revision_id,
            kind=kind,
            state="queued",
            payload_json=payload or {},
            parent_id=parent_id,
            idempotency_key=idempotency_key,
        )
        session.add(job)
        try:
            session.commit()
        except IntegrityError:
            # Lost a race against another caller inserting the same
            # (project_id, idempotency_key) between our SELECT and INSERT.
            session.rollback()
            existing = (
                session.execute(
                    select(Job).where(Job.project_id == project_id, Job.idempotency_key == idempotency_key)
                )
                .scalars()
                .first()
            )
            if existing is None:
                raise
            return existing
        session.refresh(job)
        append_event(session, project_id=project_id, job_id=job.id, type="job.queued", payload={"kind": kind})
        return job

    def claim_next(self, session: Session, *, kinds: list[str] | None = None) -> Job | None:
        with self._claim_lock:
            query = select(Job.id).where(Job.state == "queued")
            if kinds:
                query = query.where(Job.kind.in_(kinds))
            query = query.order_by(Job.created_at.asc()).limit(1)
            job_id = session.execute(query).scalars().first()
            if job_id is None:
                return None

            now = utcnow()
            lease_until = now + timedelta(seconds=settings.job_lease_seconds)
            result = session.execute(
                update(Job)
                .where(Job.id == job_id, Job.state == "queued")
                .values(
                    state="running",
                    lease_owner=self.worker_id,
                    lease_until=lease_until,
                    heartbeat_at=now,
                    attempt=Job.attempt + 1,
                )
            )
            session.commit()
            if result.rowcount != 1:
                return None
            job = session.get(Job, job_id)
            append_event(session, project_id=job.project_id, job_id=job.id, type="job.claimed", payload={})
            return job

    def heartbeat(self, session: Session, job_id: str) -> Job:
        job = _get_job(session, job_id)
        if job.lease_owner != self.worker_id:
            raise ConflictError(f"Job {job_id} is not leased by worker '{self.worker_id}'")
        now = utcnow()
        job.heartbeat_at = now
        job.lease_until = now + timedelta(seconds=settings.job_lease_seconds)
        session.commit()
        session.refresh(job)
        return job

    def complete(self, session: Session, job_id: str, *, result: dict | None = None) -> Job:
        job = _get_job(session, job_id)
        job.state = "succeeded"
        job.result_json = result or {}
        job.lease_owner = None
        job.lease_until = None
        session.commit()
        session.refresh(job)
        return job

    def fail(self, session: Session, job_id: str, *, error_code: str) -> Job:
        job = _get_job(session, job_id)
        job.state = "failed"
        job.error_code = error_code
        job.lease_owner = None
        job.lease_until = None
        session.commit()
        session.refresh(job)
        return job

    def pause(self, session: Session, job_id: str) -> Job:
        job = _get_job(session, job_id)
        if job.state not in _PAUSABLE_STATES:
            raise ConflictError(f"Job {job_id} cannot be paused from state '{job.state}'")
        job.state = "paused"
        session.commit()
        session.refresh(job)
        append_event(session, project_id=job.project_id, job_id=job.id, type="job.paused", payload={})
        return job

    def resume(self, session: Session, job_id: str) -> Job:
        job = _get_job(session, job_id)
        if job.state != "paused":
            raise ConflictError(f"Job {job_id} cannot be resumed from state '{job.state}'")
        job.state = "queued"
        job.lease_owner = None
        job.lease_until = None
        session.commit()
        session.refresh(job)
        append_event(session, project_id=job.project_id, job_id=job.id, type="job.resumed", payload={})
        return job

    def cancel(self, session: Session, job_id: str) -> Job:
        job = _get_job(session, job_id)
        if job.state in TERMINAL_STATES or job.state == "cancel_requested":
            return job
        # Spec 8.2: a running job needs its subprocesses to stop first, so it
        # moves to `cancel_requested`; anything not actively running can be
        # cancelled outright.
        job.state = "cancel_requested" if job.state == "running" else "cancelled"
        session.commit()
        session.refresh(job)
        append_event(session, project_id=job.project_id, job_id=job.id, type="job.cancel_requested", payload={"final_state": job.state})
        return job

    def reap_expired_leases(self, session: Session) -> list[Job]:
        """Spec 8.2 `interrupted`: a `running` job whose lease has expired
        (worker crashed/killed) needs recovery classification, not a silent
        retry."""

        now = utcnow()
        stale = list(
            session.execute(
                select(Job).where(
                    Job.state == "running", Job.lease_until.isnot(None), Job.lease_until < now
                )
            ).scalars()
        )
        for job in stale:
            job.state = "interrupted"
        if stale:
            session.commit()
            for job in stale:
                append_event(session, project_id=job.project_id, job_id=job.id, type="job.interrupted", payload={})
        return stale


job_queue = JobQueue()
