from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.director import generate_concepts
from app.models.creative import Concept
from app.providers.base import TextVisionProvider
from app.services import projects as projects_service
from app.services.errors import NotFoundError, ValidationAppError


def create_concepts_for_project(
    session: Session,
    project_id: str,
    *,
    provider: TextVisionProvider,
    model: str,
) -> list[Concept]:
    projects_service.get_project(session, project_id)  # 404 if unknown

    brief = projects_service.get_latest_brief(session, project_id)
    if brief is None:
        raise ValidationAppError("Concept üretmeden önce brief kaydedilmelidir.")

    brand = projects_service.get_brand_profile(session, project_id)
    if brand is None:
        raise ValidationAppError(
            "Concept üretmeden önce marka bilgisi (ürün adı/açıklama/CTA) kaydedilmelidir."
        )

    candidates = generate_concepts(provider, model, brief=brief, brand=brand)

    rows = [
        Concept(
            brief_id=brief.id,
            angle=c.angle,
            hook=c.hook,
            rationale=c.rationale,
            claim_refs_json=c.claim_refs,
            selected=False,
        )
        for c in candidates
    ]
    session.add_all(rows)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows


def list_concepts_for_project(session: Session, project_id: str) -> list[Concept]:
    brief = projects_service.get_latest_brief(session, project_id)
    if brief is None:
        return []
    return list(
        session.execute(select(Concept).where(Concept.brief_id == brief.id)).scalars().all()
    )


def select_concept(session: Session, project_id: str, concept_id: str) -> Concept:
    brief = projects_service.get_latest_brief(session, project_id)
    if brief is None:
        raise NotFoundError(f"Concept {concept_id} not found", details={"concept_id": concept_id})

    concept = session.get(Concept, concept_id)
    if concept is None or concept.brief_id != brief.id:
        raise NotFoundError(f"Concept {concept_id} not found", details={"concept_id": concept_id})

    others = session.execute(select(Concept).where(Concept.brief_id == brief.id)).scalars().all()
    for other in others:
        other.selected = other.id == concept_id
    session.commit()
    session.refresh(concept)
    return concept
