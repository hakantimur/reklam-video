from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.errors import error_response
from app.core.db import get_session
from app.providers.openrouter import OpenRouterClient, OpenRouterTextVisionProvider
from app.services import credentials as credentials_service
from app.services import plans as plans_service
from app.services.errors import BlockedError, ServiceError

router = APIRouter(tags=["plans"])

_DEFAULT_DIRECTOR_MODEL = "anthropic/claude-haiku-4.5"


class PlanGenerateRequest(BaseModel):
    concept_id: str
    model: str = _DEFAULT_DIRECTOR_MODEL


class ShotOut(BaseModel):
    id: str
    order_index: int
    source_type: str
    purpose: str
    desired_event: str | None
    target_frames: int
    caption_text: str | None
    voice_text: str | None
    locks: dict


class RevisionOut(BaseModel):
    id: str
    sequence_no: int
    status: str
    change_summary: str | None
    shots: list[ShotOut]


def _shot_out(shot) -> ShotOut:
    return ShotOut(
        id=shot.id,
        order_index=shot.order_index,
        source_type=shot.source_type,
        purpose=shot.purpose,
        desired_event=shot.desired_event,
        target_frames=shot.target_frames,
        caption_text=shot.caption_text,
        voice_text=shot.voice_text,
        locks=shot.locks_json or {},
    )


@router.post("/projects/{project_id}/plan", response_model=RevisionOut, status_code=201)
def create_plan(project_id: str, body: PlanGenerateRequest, session: Session = Depends(get_session)):
    api_key = credentials_service.get_credential_value("openrouter")
    if not api_key:
        return error_response(
            BlockedError(
                "OpenRouter API anahtarı girilmeden çekim planı üretilemez.",
                details={"missing": "openrouter_api_key"},
            )
        )

    client = OpenRouterClient(api_key=api_key)
    try:
        provider = OpenRouterTextVisionProvider(client)
        try:
            revision = plans_service.create_plan_for_project(
                session, project_id, body.concept_id, provider=provider, model=body.model
            )
        except ServiceError as exc:
            return error_response(exc)
        except Exception as exc:  # noqa: BLE001 - real model/provider failure, not a 500 crash
            return error_response(ServiceError(f"Çekim planı üretimi başarısız: {exc}"))
    finally:
        client.close()

    shots = plans_service.get_shots_for_revision(session, revision.id)
    return RevisionOut(
        id=revision.id,
        sequence_no=revision.sequence_no,
        status=revision.status,
        change_summary=revision.change_summary,
        shots=[_shot_out(s) for s in shots],
    )


@router.get("/projects/{project_id}/plan", response_model=RevisionOut | None)
def get_plan(project_id: str, session: Session = Depends(get_session)):
    revision = plans_service.get_latest_revision(session, project_id)
    if revision is None:
        return None
    shots = plans_service.get_shots_for_revision(session, revision.id)
    return RevisionOut(
        id=revision.id,
        sequence_no=revision.sequence_no,
        status=revision.status,
        change_summary=revision.change_summary,
        shots=[_shot_out(s) for s in shots],
    )


class RevisionSummaryOut(BaseModel):
    id: str
    parent_id: str | None
    sequence_no: int
    status: str
    change_summary: str | None
    shot_count: int
    created_at: str


@router.get("/projects/{project_id}/revisions", response_model=list[RevisionSummaryOut])
def list_revisions(project_id: str, session: Session = Depends(get_session)):
    """Spec §5.3 "önceki sürümle karşılaştırma" (read side): the full
    revision history for a project, newest first."""

    revisions = plans_service.list_revisions(session, project_id)
    return [
        RevisionSummaryOut(
            id=r.id,
            parent_id=r.parent_id,
            sequence_no=r.sequence_no,
            status=r.status,
            change_summary=r.change_summary,
            shot_count=len(plans_service.get_shots_for_revision(session, r.id)),
            created_at=r.created_at.isoformat(),
        )
        for r in revisions
    ]
