import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.errors import error_response
from app.core.db import get_session
from app.jobs.queue import job_queue
from app.services import takes as takes_service
from app.services.errors import ServiceError

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


class TakeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shot_id: str
    asset_id: str
    attempt: int
    status: str
    rejection_reason: str | None
    quality_json: dict
    created_at: datetime


class ShotTakeOut(BaseModel):
    shot_id: str
    selected_take_id: str | None


@router.get("/projects/{project_id}/shots/{shot_id}/takes", response_model=list[TakeOut])
def list_takes(project_id: str, shot_id: str, session: Session = Depends(get_session)):
    try:
        takes = takes_service.list_takes_for_shot(session, project_id, shot_id)
    except ServiceError as exc:
        return error_response(exc)
    return [TakeOut.model_validate(t) for t in takes]


@router.post(
    "/projects/{project_id}/shots/{shot_id}/takes/{take_id}/select", response_model=ShotTakeOut
)
def select_take(project_id: str, shot_id: str, take_id: str, session: Session = Depends(get_session)):
    try:
        shot = takes_service.select_take(session, project_id, shot_id, take_id)
    except ServiceError as exc:
        return error_response(exc)
    return ShotTakeOut(shot_id=shot.id, selected_take_id=shot.selected_take_id)
