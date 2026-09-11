from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.errors import error_response
from app.core.db import get_session
from app.providers.openrouter import OpenRouterClient, OpenRouterTextVisionProvider
from app.services import credentials as credentials_service
from app.services import plans as plans_service
from app.services import revisions as revisions_service
from app.services.errors import BlockedError, ServiceError

router = APIRouter(tags=["revisions"])

_DEFAULT_DIRECTOR_MODEL = "anthropic/claude-haiku-4.5"


class VariationRequest(BaseModel):
    shot_instructions: dict[str, str]
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
    selected_take_id: str | None
    locks: dict


class RevisionOut(BaseModel):
    id: str
    parent_id: str | None
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
        selected_take_id=shot.selected_take_id,
        locks=shot.locks_json or {},
    )


@router.post(
    "/projects/{project_id}/revisions/{revision_id}/variation", response_model=RevisionOut, status_code=201
)
def create_variation(
    project_id: str, revision_id: str, body: VariationRequest, session: Session = Depends(get_session)
):
    api_key = credentials_service.get_credential_value("openrouter")
    if not api_key:
        return error_response(
            BlockedError(
                "OpenRouter API anahtarı girilmeden varyasyon üretilemez.",
                details={"missing": "openrouter_api_key"},
            )
        )

    client = OpenRouterClient(api_key=api_key)
    try:
        provider = OpenRouterTextVisionProvider(client)
        try:
            new_revision = revisions_service.create_revision_variation(
                session,
                project_id,
                revision_id,
                shot_instructions=body.shot_instructions,
                provider=provider,
                model=body.model,
            )
        except ServiceError as exc:
            return error_response(exc)
        except Exception as exc:  # noqa: BLE001 - real model/provider failure, not a 500 crash
            return error_response(ServiceError(f"Varyasyon üretimi başarısız: {exc}"))
    finally:
        client.close()

    shots = plans_service.get_shots_for_revision(session, new_revision.id)
    return RevisionOut(
        id=new_revision.id,
        parent_id=new_revision.parent_id,
        sequence_no=new_revision.sequence_no,
        status=new_revision.status,
        change_summary=new_revision.change_summary,
        shots=[_shot_out(s) for s in shots],
    )
