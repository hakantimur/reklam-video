import uuid

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.jobs.queue import job_queue

router = APIRouter(tags=["generation"])


class GenerateSceneRequest(BaseModel):
    video_model: str
    text_model: str = "anthropic/claude-haiku-4.5"
    ratio: str = "9:16"
    resolution: str | None = None


class GenerateVoiceRequest(BaseModel):
    voice_id: str
    language: str | None = None


class GenerationJobOut(BaseModel):
    job_id: str
    state: str


@router.post(
    "/projects/{project_id}/shots/{shot_id}/generate-scene", response_model=GenerationJobOut, status_code=202
)
def start_generate_scene(
    project_id: str,
    shot_id: str,
    body: GenerateSceneRequest,
    session: Session = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    payload = {
        "shot_id": shot_id,
        "video_model": body.video_model,
        "text_model": body.text_model,
        "ratio": body.ratio,
    }
    if body.resolution is not None:
        payload["resolution"] = body.resolution

    job = job_queue.enqueue(
        session,
        project_id=project_id,
        kind="generate_ai_scene",
        idempotency_key=idempotency_key or str(uuid.uuid4()),
        payload=payload,
    )
    return GenerationJobOut(job_id=job.id, state=job.state)


@router.post(
    "/projects/{project_id}/shots/{shot_id}/generate-voice", response_model=GenerationJobOut, status_code=202
)
def start_generate_voice(
    project_id: str,
    shot_id: str,
    body: GenerateVoiceRequest,
    session: Session = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    payload = {"shot_id": shot_id, "voice_id": body.voice_id}
    if body.language is not None:
        payload["language"] = body.language

    job = job_queue.enqueue(
        session,
        project_id=project_id,
        kind="generate_voice",
        idempotency_key=idempotency_key or str(uuid.uuid4()),
        payload=payload,
    )
    return GenerationJobOut(job_id=job.id, state=job.state)
