import uuid

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.jobs.queue import job_queue

router = APIRouter(tags=["export"])


class ExportJobOut(BaseModel):
    job_id: str
    state: str


@router.post(
    "/projects/{project_id}/revisions/{revision_id}/export", response_model=ExportJobOut, status_code=202
)
def start_export(
    project_id: str,
    revision_id: str,
    session: Session = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    job = job_queue.enqueue(
        session,
        project_id=project_id,
        kind="export_final",
        idempotency_key=idempotency_key or str(uuid.uuid4()),
        payload={"revision_id": revision_id},
    )
    return ExportJobOut(job_id=job.id, state=job.state)
