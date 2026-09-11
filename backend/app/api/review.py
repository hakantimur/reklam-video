import uuid

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.jobs.queue import job_queue

router = APIRouter(tags=["review"])


class ReviewRequest(BaseModel):
    model: str = "anthropic/claude-haiku-4.5"


class ReviewJobOut(BaseModel):
    job_id: str
    state: str


@router.post("/projects/{project_id}/shots/{shot_id}/review", response_model=ReviewJobOut, status_code=202)
def start_review(
    project_id: str,
    shot_id: str,
    body: ReviewRequest,
    session: Session = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    job = job_queue.enqueue(
        session,
        project_id=project_id,
        kind="review_take",
        idempotency_key=idempotency_key or str(uuid.uuid4()),
        payload={"shot_id": shot_id, "model": body.model},
    )
    return ReviewJobOut(job_id=job.id, state=job.state)
