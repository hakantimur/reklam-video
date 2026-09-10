"""SSE event stream (spec 8.1, 8.4).

Events are appended to `event_log` by services/jobs as they happen; this
endpoint just tails that table. `Last-Event-ID` (header, per the SSE spec,
or a `last_event_id` query param as a fallback for clients that can't set
custom headers on the initial `EventSource` request) lets a client that
dropped its connection resume exactly where it left off instead of
replaying or losing events.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from app.core.db import SessionLocal
from app.models.qa import EventLog
from app.services.events import list_events_since

router = APIRouter(tags=["events"])

_POLL_INTERVAL_SECONDS = 0.5
# Safety ceiling so a connection FastAPI/Starlette fails to notice as
# disconnected can't spin forever inside a worker thread.
_MAX_IDLE_POLLS = 7200  # ~1 hour at the default poll interval


def _format_sse(event: EventLog) -> str:
    data = json.dumps(
        {
            "sequence": event.sequence,
            "project_id": event.project_id,
            "job_id": event.job_id,
            "type": event.type,
            "payload": event.payload_json,
            "created_at": event.created_at.isoformat(),
        }
    )
    return f"id: {event.sequence}\nevent: {event.type}\ndata: {data}\n\n"


async def _event_stream(request: Request, last_event_id: int):
    cursor = last_event_id
    idle_polls = 0
    while idle_polls < _MAX_IDLE_POLLS:
        if await request.is_disconnected():
            break
        with SessionLocal() as session:
            events = list_events_since(session, after_sequence=cursor, limit=200)
        if events:
            idle_polls = 0
            for event in events:
                cursor = event.sequence
                yield _format_sse(event)
        else:
            idle_polls += 1
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)


def _parse_last_event_id(request: Request) -> int:
    raw = request.headers.get("last-event-id") or request.query_params.get("last_event_id")
    try:
        return int(raw) if raw else 0
    except ValueError:
        return 0


@router.get("/events")
async def stream_events(request: Request):
    last_event_id = _parse_last_event_id(request)
    return StreamingResponse(
        _event_stream(request, last_event_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
