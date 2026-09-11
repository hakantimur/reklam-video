import hashlib
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.director import generate_shot_plan
from app.models.creative import Concept, Revision, Shot
from app.providers.base import TextVisionProvider
from app.services import projects as projects_service
from app.services.errors import NotFoundError, ValidationAppError


def create_plan_for_project(
    session: Session,
    project_id: str,
    concept_id: str,
    *,
    provider: TextVisionProvider,
    model: str,
) -> Revision:
    projects_service.get_project(session, project_id)  # 404 if unknown

    brief = projects_service.get_latest_brief(session, project_id)
    if brief is None:
        raise ValidationAppError("Plan üretmeden önce brief kaydedilmelidir.")

    brand = projects_service.get_brand_profile(session, project_id)
    if brand is None:
        raise ValidationAppError("Plan üretmeden önce marka bilgisi kaydedilmelidir.")

    concept = session.get(Concept, concept_id)
    if concept is None or concept.brief_id != brief.id:
        raise NotFoundError(
            f"Concept {concept_id} not found for this brief", details={"concept_id": concept_id}
        )

    shot_plan = generate_shot_plan(provider, model, brief=brief, brand=brand, concept=concept)

    plan_json = shot_plan.model_dump_json()
    content_hash = hashlib.sha256(plan_json.encode("utf-8")).hexdigest()

    next_sequence = (
        session.execute(
            select(func.coalesce(func.max(Revision.sequence_no), 0)).where(
                Revision.project_id == project_id
            )
        ).scalar_one()
        + 1
    )

    revision = Revision(
        project_id=project_id,
        parent_id=None,
        brief_id=brief.id,
        sequence_no=next_sequence,
        status="draft",
        timeline_json={},
        content_hash=content_hash,
        created_at=datetime.now(timezone.utc),
        change_summary=f"'{concept.angle}' fikrinden otomatik üretilen ilk çekim planı",
    )
    session.add(revision)
    session.flush()  # need revision.id for the Shot rows below

    for index, shot in enumerate(shot_plan.shots):
        session.add(
            Shot(
                revision_id=revision.id,
                order_index=index,
                source_type=shot.source_type,
                purpose=shot.purpose,
                desired_event=shot.desired_event,
                start_state_json=shot.start_state,
                success_predicate_json=shot.success_predicate.model_dump(),
                action_constraints_json=shot.action_constraints.model_dump(),
                target_frames=shot.target_frames,
                handles_frames=shot.handles_frames.model_dump(),
                caption_text=shot.caption,
                voice_text=shot.voice_text,
                locks_json=shot.locks.model_dump(),
            )
        )

    session.commit()
    session.refresh(revision)
    return revision


def get_latest_revision(session: Session, project_id: str) -> Revision | None:
    return (
        session.execute(
            select(Revision)
            .where(Revision.project_id == project_id)
            .order_by(Revision.sequence_no.desc())
        )
        .scalars()
        .first()
    )


def get_shots_for_revision(session: Session, revision_id: str) -> list[Shot]:
    return list(
        session.execute(
            select(Shot).where(Shot.revision_id == revision_id).order_by(Shot.order_index)
        )
        .scalars()
        .all()
    )
