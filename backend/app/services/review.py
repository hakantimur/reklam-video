"""Spec §10/§21: content/brand-safety review of a shot's take.

Separate from `app.services.qa` (which only checks mechanically-verifiable
facts: does a take exist, did technical QC pass). This is the piece that
was missing to judge *content* — forbidden claims, message accuracy,
whether the shot actually shows what it claims to. Persisted as a
`QAReport` row (spec §7.2, `scope="content"`) rather than returned
ad-hoc, so `run_revision_qa` can pick up the latest verdict without
re-running a paid vision call on every page load.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.reviewer import review_take
from app.media.technical_qc import sample_frames_png
from app.models.creative import Shot
from app.models.qa import QAReport as QAReportRow
from app.providers.base import TextVisionProvider
from app.services import assets as assets_service
from app.services import projects as projects_service
from app.services import timeline as timeline_service
from app.services.errors import ValidationAppError

DEFAULT_SAMPLE_COUNT = 4


def get_latest_content_review_for_asset(session: Session, asset_id: str) -> QAReportRow | None:
    """A content review is tied to the underlying Asset, not a Take row —
    a Take "carried forward" into a new revision (spec §10, locked/
    unmentioned shots) still points at the same asset_id, and its content
    genuinely hasn't changed, so a prior review of it is still valid."""

    return (
        session.execute(
            select(QAReportRow)
            .where(QAReportRow.asset_id == asset_id, QAReportRow.scope == "content")
            .order_by(QAReportRow.created_at.desc())
        )
        .scalars()
        .first()
    )


def review_shot_take(
    session: Session,
    project_id: str,
    shot_id: str,
    *,
    provider: TextVisionProvider,
    model: str,
    sample_count: int = DEFAULT_SAMPLE_COUNT,
) -> QAReportRow:
    from app.models.creative import Revision

    shot = session.get(Shot, shot_id)
    if shot is None:
        from app.services.errors import NotFoundError

        raise NotFoundError(f"Shot {shot_id} not found", details={"shot_id": shot_id})
    revision = session.get(Revision, shot.revision_id)
    if revision is None or revision.project_id != project_id:
        from app.services.errors import NotFoundError

        raise NotFoundError(f"Shot {shot_id} not found for this project", details={"shot_id": shot_id})

    take = timeline_service.selected_or_best_take(session, shot)
    if take is None:
        raise ValidationAppError(
            "Bu sahne için incelenecek kabul edilebilir bir çekim/üretim yok.", details={"shot_id": shot_id}
        )

    project = projects_service.get_project(session, project_id)
    brand = projects_service.get_brand_profile(session, project_id)

    _, path = assets_service.resolve_asset_path(session, take.asset_id)
    frames = sample_frames_png(path, sample_count)

    verdict = review_take(
        provider,
        model,
        shot_purpose=shot.purpose,
        desired_event=shot.desired_event,
        caption_text=shot.caption_text,
        voice_text=shot.voice_text,
        verified_claims=(brand.verified_claims_json or []) if brand else [],
        forbidden_claims=(brand.forbidden_claims_json or []) if brand else [],
        sample_frames_png=frames,
    )

    report = QAReportRow(
        revision_id=revision.id,
        asset_id=take.asset_id,
        scope="content",
        checks_json={"reasoning": verdict.reasoning, "defects": verdict.defects, "sampled_frames": len(frames)},
        reviewer_model=model,
        outcome=verdict.outcome,
        human_status="pending",
        created_at=datetime.now(timezone.utc),
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report
