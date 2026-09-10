"""Append-only event log (spec 8.4): every state change the UI cares about
is appended here, and `GET /api/v1/events` streams it over SSE keyed by the
`sequence` autoincrement column so a dropped connection can resume with
`Last-Event-ID`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.qa import EventLog


def append_event(
    session: Session,
    *,
    project_id: str,
    type: str,
    payload: dict | None = None,
    job_id: str | None = None,
) -> EventLog:
    event = EventLog(
        project_id=project_id,
        job_id=job_id,
        type=type,
        payload_json=payload or {},
        created_at=utcnow(),
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def list_events_since(session: Session, *, after_sequence: int = 0, limit: int = 200) -> list[EventLog]:
    return list(
        session.execute(
            select(EventLog)
            .where(EventLog.sequence > after_sequence)
            .order_by(EventLog.sequence.asc())
            .limit(limit)
        ).scalars()
    )
