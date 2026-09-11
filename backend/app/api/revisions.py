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


class ShotLocksPatch(BaseModel):
    visual: bool | None = None
    voice: bool | None = None
    caption: bool | None = None
    timing: bool | None = None


class ShotCaptionPatch(BaseModel):
    caption_text: str | None = None


class ReorderRequest(BaseModel):
    shot_order: list[str]


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


@router.patch("/projects/{project_id}/shots/{shot_id}/locks", response_model=ShotOut)
def update_shot_locks(
    project_id: str, shot_id: str, body: ShotLocksPatch, session: Session = Depends(get_session)
):
    """Spec §5.3 "sahne kilidi, ses kilidi": lock/unlock which of a shot's
    visual/voice/caption/timing fields a future variation is allowed to
    change. Only the fields present in the request body are touched."""

    locks = body.model_dump(exclude_none=True)
    try:
        shot = revisions_service.set_shot_locks(session, project_id, shot_id, locks)
    except ServiceError as exc:
        return error_response(exc)
    return _shot_out(shot)


@router.patch("/projects/{project_id}/shots/{shot_id}/caption", response_model=ShotOut)
def update_shot_caption(
    project_id: str, shot_id: str, body: ShotCaptionPatch, session: Session = Depends(get_session)
):
    """Spec §5.3 "altyazı düzeltme": manually correct a shot's burned-in
    caption text in place."""

    try:
        shot = revisions_service.set_shot_caption(session, project_id, shot_id, body.caption_text)
    except ServiceError as exc:
        return error_response(exc)
    return _shot_out(shot)


@router.put("/projects/{project_id}/revisions/{revision_id}/order", response_model=list[ShotOut])
def reorder_shots(
    project_id: str, revision_id: str, body: ReorderRequest, session: Session = Depends(get_session)
):
    """Spec §5.3 "klip taşıma": reorder a revision's shots in place."""

    try:
        shots = revisions_service.reorder_shots(session, project_id, revision_id, body.shot_order)
    except ServiceError as exc:
        return error_response(exc)
    return [_shot_out(s) for s in shots]
