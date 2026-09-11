import uuid

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.jobs.queue import job_queue

router = APIRouter(tags=["capture"])


class CaptureRequest(BaseModel):
    serial: str
    model: str = "anthropic/claude-haiku-4.5"
    max_actions: int | None = None
    max_seconds: int | None = None


class CaptureJobOut(BaseModel):
    job_id: str
    state: str


@router.post("/projects/{project_id}/shots/{shot_id}/capture", response_model=CaptureJobOut, status_code=202)
def start_capture(
    project_id: str,
    shot_id: str,
    body: CaptureRequest,
    session: Session = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    payload = {"shot_id": shot_id, "serial": body.serial, "model": body.model}
    if body.max_actions is not None:
        payload["max_actions"] = body.max_actions
    if body.max_seconds is not None:
        payload["max_seconds"] = body.max_seconds

    job = job_queue.enqueue(
        session,
        project_id=project_id,
        kind="capture_shot",
        idempotency_key=idempotency_key or str(uuid.uuid4()),
        payload=payload,
    )
    return CaptureJobOut(job_id=job.id, state=job.state)
