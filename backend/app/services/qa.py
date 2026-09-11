"""Spec §21 Safha 11: QA gate a revision must pass before final export.

Checks what is mechanically verifiable from data already in the database:
every shot has a take/asset whose technical QC passed, none of it comes
from a `synthetic_test` origin (spec §7.2: that origin explicitly blocks
final QA), the frame budget still adds up, and — if a content review
(`app.services.review`, spec §10) was ever run against a take's asset —
its latest verdict didn't fail. Content review is NOT mandatory: a take
that was never reviewed passes on technical grounds alone, so `passed:
True` here means "technically exportable, and content-clean where
reviewed", not "every frame was creatively approved by an LLM".
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.project import Brief
from app.services import plans as plans_service
from app.services import review as review_service
from app.services import timeline as timeline_service
from app.services.errors import NotFoundError, ValidationAppError


@dataclass
class QAReport:
    revision_id: str
    passed: bool
    issues: list[str] = field(default_factory=list)


def run_revision_qa(session: Session, project_id: str, revision_id: str) -> QAReport:
    from app.models.creative import Revision

    revision = session.get(Revision, revision_id)
    if revision is None or revision.project_id != project_id:
        raise NotFoundError(f"Revision {revision_id} not found", details={"revision_id": revision_id})

    shots = plans_service.get_shots_for_revision(session, revision.id)
    if not shots:
        raise ValidationAppError("Bu revizyonda hiç sahne yok.", details={"revision_id": revision_id})

    # The specific Brief this revision's plan was actually generated
    # against — not whatever the "latest" Brief happens to be now. A
    # revision's `brief_id` is set once (spec §7.2's `revisions.brief_id`
    # FK) and carried forward by every later variation (see
    # `app.services.revisions.create_revision_variation`); comparing
    # against "latest" instead would make QA permanently fail every
    # existing revision the moment a user edits the brief afterward, even
    # though nothing about the revision itself became invalid.
    brief = session.get(Brief, revision.brief_id)
    issues: list[str] = []

    total_frames = sum(s.target_frames for s in shots)
    if brief is not None and abs(total_frames - brief.target_frames) > 1:
        issues.append(
            f"Toplam sahne süresi ({total_frames} kare) brief hedefiyle ({brief.target_frames} kare) uyuşmuyor."
        )

    for shot in shots:
        take = timeline_service.selected_or_best_take(session, shot)
        if take is None:
            issues.append(f"Sahne '{shot.purpose}' için hiç kabul edilebilir çekim/üretim yok.")
            continue

        asset = session.get(Asset, take.asset_id)
        if asset is None:
            issues.append(f"Sahne '{shot.purpose}' → Take {take.id} bir Asset'e işaret etmiyor.")
            continue

        if asset.origin == "synthetic_test":
            issues.append(f"Sahne '{shot.purpose}' bir test/sentetik asset kullanıyor — final QA'yı bloklar.")

        qc_outcome = (asset.metadata_json or {}).get("technical_qc", {}).get("outcome")
        if qc_outcome == "fail":
            issues.append(f"Sahne '{shot.purpose}' → Take {take.id} teknik QC'yi geçemedi.")
        elif qc_outcome == "uncertain":
            issues.append(f"Sahne '{shot.purpose}' → Take {take.id} teknik QC sonucu belirsiz, elle onay gerekir.")
        elif qc_outcome is None:
            issues.append(f"Sahne '{shot.purpose}' → Take {take.id} için teknik QC hiç çalıştırılmamış.")

        content_review = review_service.get_latest_content_review_for_asset(session, take.asset_id)
        if content_review is not None and content_review.outcome == "fail":
            defects = ", ".join(content_review.checks_json.get("defects") or []) or content_review.checks_json.get(
                "reasoning", ""
            )
            issues.append(f"Sahne '{shot.purpose}' içerik incelemesini geçemedi: {defects}")

    return QAReport(revision_id=revision.id, passed=not issues, issues=issues)
