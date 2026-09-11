import uuid

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.jobs.queue import job_queue

router = APIRouter(tags=["discover"])


class DiscoverRequest(BaseModel):
    serial: str
    package_id: str
    model: str = "anthropic/claude-haiku-4.5"
    max_actions: int | None = None
    max_seconds: int | None = None


class DiscoverJobOut(BaseModel):
    job_id: str
    revision_id: str | None
    state: str


@router.post("/projects/{project_id}/discover", response_model=DiscoverJobOut, status_code=202)
def start_discovery(
    project_id: str,
    body: DiscoverRequest,
    session: Session = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    payload = {"serial": body.serial, "package_id": body.package_id, "model": body.model}
    if body.max_actions is not None:
        payload["max_actions"] = body.max_actions
    if body.max_seconds is not None:
        payload["max_seconds"] = body.max_seconds

    job = job_queue.enqueue(
        session,
        project_id=project_id,
        kind="discover",
        idempotency_key=idempotency_key or str(uuid.uuid4()),
        payload=payload,
    )
    return DiscoverJobOut(job_id=job.id, revision_id=job.revision_id, state=job.state)
