from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.errors import error_response
from app.core.db import get_session
from app.providers.openrouter import OpenRouterClient, OpenRouterTextVisionProvider
from app.schemas.concept import ConceptOut
from app.services import concepts as concepts_service
from app.services import credentials as credentials_service
from app.services.errors import BlockedError, ServiceError

router = APIRouter(tags=["concepts"])

# Spec §3.2 doesn't pin a specific director model; this is a low-risk default
# (cheap, capable, present in the live OpenRouter catalog) rather than a
# spec requirement — the user can override per-request until Settings grows
# a real "director model" picker.
_DEFAULT_DIRECTOR_MODEL = "anthropic/claude-haiku-4.5"


class ConceptGenerateRequest(BaseModel):
    model: str = _DEFAULT_DIRECTOR_MODEL


def _concept_out(concept) -> ConceptOut:
    return ConceptOut(
        id=concept.id,
        angle=concept.angle,
        hook=concept.hook,
        rationale=concept.rationale,
        claim_refs=concept.claim_refs_json or [],
        selected=concept.selected,
    )


@router.post("/projects/{project_id}/concepts", response_model=list[ConceptOut], status_code=201)
def create_concepts(
    project_id: str, body: ConceptGenerateRequest, session: Session = Depends(get_session)
):
    api_key = credentials_service.get_credential_value("openrouter")
    if not api_key:
        return error_response(
            BlockedError(
                "OpenRouter API anahtarı girilmeden concept üretilemez.",
                details={"missing": "openrouter_api_key"},
            )
        )

    client = OpenRouterClient(api_key=api_key)
    try:
        provider = OpenRouterTextVisionProvider(client)
        try:
            rows = concepts_service.create_concepts_for_project(
                session, project_id, provider=provider, model=body.model
            )
        except ServiceError as exc:
            return error_response(exc)
        except Exception as exc:  # noqa: BLE001 - surface a real provider/model failure, don't crash
            return error_response(ServiceError(f"Concept üretimi başarısız: {exc}"))
    finally:
        client.close()

    return [_concept_out(c) for c in rows]


@router.get("/projects/{project_id}/concepts", response_model=list[ConceptOut])
def list_concepts(project_id: str, session: Session = Depends(get_session)):
    rows = concepts_service.list_concepts_for_project(session, project_id)
    return [_concept_out(c) for c in rows]


@router.post("/projects/{project_id}/concepts/{concept_id}/select", response_model=ConceptOut)
def select_concept(project_id: str, concept_id: str, session: Session = Depends(get_session)):
    try:
        concept = concepts_service.select_concept(session, project_id, concept_id)
    except ServiceError as exc:
        return error_response(exc)
    return _concept_out(concept)
