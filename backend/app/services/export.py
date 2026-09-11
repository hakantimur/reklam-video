"""Spec §21 Safha 11: final export — the same render pipeline Safha 9
built, but gated behind `app.services.qa.run_revision_qa` and writing into
`exports/v001/` (spec §7.3) with `Asset.type == "export"` instead of
`"proxy"`. A revision that fails QA never reaches `remotion render` at
all — no "export" asset is ever created for incomplete/unverified work.
"""

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.services import qa as qa_service
from app.services import render as render_service
from app.services.errors import BlockedError


def export_final(session: Session, project_id: str, revision_id: str) -> Asset:
    report = qa_service.run_revision_qa(session, project_id, revision_id)
    if not report.passed:
        raise BlockedError(
            "Bu revizyon QA'yı geçmedi, dışa aktarılamaz.",
            details={"revision_id": revision_id, "issues": report.issues},
        )

    return render_service.render_timeline_to_asset(
        session,
        project_id,
        output_dir_name="exports/v001",
        filename_prefix="export",
        asset_type="export",
        extra_metadata={"qa_report": {"passed": report.passed, "issues": report.issues}},
    )
