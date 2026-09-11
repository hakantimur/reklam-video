import uuid

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.errors import error_response
from app.core.db import get_session
from app.jobs.queue import job_queue
from app.services import plans as plans_service
from app.services import timeline as timeline_service
from app.services.errors import ServiceError

router = APIRouter(tags=["render"])


class TimelineOut(BaseModel):
    schema_version: int
    revision_id: str
    fps: dict
    duration_frames: int
    canvas: dict
    tracks: list


@router.post("/projects/{project_id}/timeline/build", response_model=TimelineOut)
def build_timeline(project_id: str, session: Session = Depends(get_session)):
    try:
        timeline = timeline_service.build_timeline(session, project_id)
    except ServiceError as exc:
        return error_response(exc)
    return timeline


@router.get("/projects/{project_id}/timeline", response_model=TimelineOut | None)
def get_timeline(project_id: str, session: Session = Depends(get_session)):
    revision = plans_service.get_latest_revision(session, project_id)
    if revision is None or not revision.timeline_json:
        return None
    return revision.timeline_json


class RenderJobOut(BaseModel):
    job_id: str
    state: str


@router.post("/projects/{project_id}/render/preview", response_model=RenderJobOut, status_code=202)
def start_render_preview(
    project_id: str,
    session: Session = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    job = job_queue.enqueue(
        session,
        project_id=project_id,
        kind="render_preview",
        idempotency_key=idempotency_key or str(uuid.uuid4()),
        payload={},
    )
    return RenderJobOut(job_id=job.id, state=job.state)
