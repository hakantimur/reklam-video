from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.asset import Asset
from app.models.creative import Revision, Shot, Take
from app.services import export as export_service
from app.services import projects as projects_service
from app.services.errors import BlockedError


def _setup_incomplete_project(session):
    project = projects_service.create_project(session, name="Export Testi")
    projects_service.put_brief(
        session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=90, fps_num=30, fps_den=1,
        placement_id="p", budget_microusd=1, product_name="Synova", description="d", cta="c",
    )
    brief = projects_service.get_latest_brief(session, project.id)
    revision = Revision(
        project_id=project.id, brief_id=brief.id, sequence_no=1, status="draft",
        timeline_json={}, content_hash="x", created_at=datetime.now(timezone.utc),
    )
    session.add(revision)
    session.flush()
    shot = Shot(revision_id=revision.id, order_index=0, source_type="gameplay", purpose="no take yet", target_frames=90)
    session.add(shot)
    session.commit()
    return project, revision


def test_export_final_blocked_when_qa_fails(db_session):
    project, revision = _setup_incomplete_project(db_session)

    with pytest.raises(BlockedError) as exc_info:
        export_service.export_final(db_session, project.id, revision.id)

    assert "issues" in exc_info.value.details
    assert len(exc_info.value.details["issues"]) > 0


def test_export_final_renders_when_qa_passes(monkeypatch, db_session):
    project = projects_service.create_project(db_session, name="Export Basarili Testi")
    projects_service.put_brief(
        db_session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=90, fps_num=30, fps_den=1,
        placement_id="p", budget_microusd=1, product_name="Synova", description="d", cta="c",
    )
    brief = projects_service.get_latest_brief(db_session, project.id)
    revision = Revision(
        project_id=project.id, brief_id=brief.id, sequence_no=1, status="draft",
        timeline_json={}, content_hash="x", created_at=datetime.now(timezone.utc),
    )
    db_session.add(revision)
    db_session.flush()
    shot = Shot(revision_id=revision.id, order_index=0, source_type="gameplay", purpose="ok", target_frames=90)
    db_session.add(shot)
    db_session.flush()
    asset = Asset(
        project_id=project.id, type="video", origin="emulator_capture", relative_path="x.mp4",
        sha256="h", byte_size=1, metadata_json={"technical_qc": {"outcome": "pass"}},
    )
    db_session.add(asset)
    db_session.flush()
    take = Take(shot_id=shot.id, asset_id=asset.id, attempt=1, status="pending")
    db_session.add(take)
    db_session.flush()
    shot.selected_take_id = take.id
    db_session.commit()

    fake_export_asset = MagicMock(id="export-asset-1")
    fake_render = MagicMock(return_value=fake_export_asset)
    monkeypatch.setattr(export_service.render_service, "render_timeline_to_asset", fake_render)

    result = export_service.export_final(db_session, project.id, revision.id)

    assert result is fake_export_asset
    _, kwargs = fake_render.call_args
    assert kwargs["output_dir_name"] == "exports/v001"
    assert kwargs["asset_type"] == "export"
