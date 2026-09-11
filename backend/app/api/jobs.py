from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import error_response
from app.core.db import get_session
from app.jobs.queue import job_queue
from app.models.jobs import Job
from app.schemas.job import JobOut
from app.services.errors import NotFoundError, ServiceError

router = APIRouter(tags=["jobs"])


@router.get("/projects/{project_id}/jobs", response_model=list[JobOut])
def list_jobs(project_id: str, state: str | None = None, session: Session = Depends(get_session)):
    """Spec §5.2 "İşler" ekranı: kalıcı iş geçmişi, en yeni önce."""

    query = select(Job).where(Job.project_id == project_id)
    if state is not None:
        query = query.where(Job.state == state)
    query = query.order_by(Job.created_at.desc())
    jobs = session.execute(query).scalars().all()
    return [JobOut.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if job is None:
        return error_response(NotFoundError(f"Job {job_id} not found", details={"job_id": job_id}))
    return JobOut.model_validate(job)


@router.post("/jobs/{job_id}/pause", response_model=JobOut)
def pause_job(job_id: str, session: Session = Depends(get_session)):
    try:
        job = job_queue.pause(session, job_id)
    except ServiceError as exc:
        return error_response(exc)
    return JobOut.model_validate(job)


@router.post("/jobs/{job_id}/resume", response_model=JobOut)
def resume_job(job_id: str, session: Session = Depends(get_session)):
    try:
        job = job_queue.resume(session, job_id)
    except ServiceError as exc:
        return error_response(exc)
    return JobOut.model_validate(job)


@router.post("/jobs/{job_id}/cancel", response_model=JobOut)
def cancel_job(job_id: str, session: Session = Depends(get_session)):
    try:
        job = job_queue.cancel(session, job_id)
    except ServiceError as exc:
        return error_response(exc)
    return JobOut.model_validate(job)
