import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.errors import error_response
from app.core.db import get_session
from app.jobs.queue import job_queue
from app.models.creative import Shot
from app.services import review as review_service
from app.services import timeline as timeline_service
from app.services.errors import ServiceError

router = APIRouter(tags=["review"])


class ReviewRequest(BaseModel):
    model: str = "anthropic/claude-haiku-4.5"


class ReviewJobOut(BaseModel):
    job_id: str
    state: str


class ReviewOut(BaseModel):
    outcome: str
    reasoning: str
    defects: list[str]
    reviewer_model: str | None
    created_at: datetime


@router.get(
    "/projects/{project_id}/shots/{shot_id}/review", response_model=ReviewOut | None
)
def get_shot_review(project_id: str, shot_id: str, session: Session = Depends(get_session)):
    """Spec §10: the latest content review for this shot's current take, or
    null if it was never reviewed — content review is optional (see
    `app.services.qa`), so "never reviewed" is a real, distinct state from
    "reviewed and passed"."""

    shot = session.get(Shot, shot_id)
    if shot is None:
        return error_response(ServiceError(f"Shot {shot_id} not found"))

    take = timeline_service.selected_or_best_take(session, shot)
    if take is None:
        return None

    report = review_service.get_latest_content_review_for_asset(session, take.asset_id)
    if report is None:
        return None

    return ReviewOut(
        outcome=report.outcome,
        reasoning=report.checks_json.get("reasoning", ""),
        defects=report.checks_json.get("defects") or [],
        reviewer_model=report.reviewer_model,
        created_at=report.created_at,
    )


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
