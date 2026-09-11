"""Spec §21 Safha 11: QA gate a revision must pass before final export.

Deliberately narrow and honest about what it checks — spec's full reviewer
agent (brand-safety / content review, spec §10) is not implemented yet (see
docs/KNOWN_LIMITATIONS.md), so this only verifies what is mechanically
checkable from data already in the database: every shot has a take/asset
whose technical QC passed, none of it comes from a `synthetic_test` origin
(spec §7.2: that origin explicitly blocks final QA), and the frame budget
still adds up. A `passed: True` here means "technically exportable", not
"creatively approved".
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.services import plans as plans_service
from app.services import projects as projects_service
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

    brief = projects_service.get_latest_brief(session, project_id)
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

    return QAReport(revision_id=revision.id, passed=not issues, issues=issues)
