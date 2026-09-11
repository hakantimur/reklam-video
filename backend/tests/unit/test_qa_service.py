from datetime import datetime, timezone

import pytest

from app.models.asset import Asset
from app.models.creative import Revision, Shot, Take
from app.models.qa import QAReport as QAReportRow
from app.services import projects as projects_service
from app.services import qa as qa_service
from app.services.errors import NotFoundError, ValidationAppError


def _setup_project(session, target_frames=90):
    project = projects_service.create_project(session, name="QA Testi")
    projects_service.put_brief(
        session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=target_frames, fps_num=30, fps_den=1,
        placement_id="p", budget_microusd=1, product_name="Synova", description="d", cta="c",
    )
    brief = projects_service.get_latest_brief(session, project.id)
    revision = Revision(
        project_id=project.id, brief_id=brief.id, sequence_no=1, status="draft",
        timeline_json={}, content_hash="x", created_at=datetime.now(timezone.utc),
    )
    session.add(revision)
    session.flush()
    return project, revision


def _add_shot_with_take(session, project_id, revision_id, order_index, *, qc_outcome="pass", origin="emulator_capture"):
    shot = Shot(revision_id=revision_id, order_index=order_index, source_type="gameplay", purpose=f"shot-{order_index}", target_frames=90)
    session.add(shot)
    session.flush()
    asset = Asset(
        project_id=project_id, type="video", origin=origin, relative_path=f"x{order_index}.mp4",
        sha256="h", byte_size=1, metadata_json={"technical_qc": {"outcome": qc_outcome}} if qc_outcome else {},
    )
    session.add(asset)
    session.flush()
    take = Take(shot_id=shot.id, asset_id=asset.id, attempt=1, status="pending")
    session.add(take)
    session.flush()
    shot.selected_take_id = take.id
    session.commit()
    return shot, take, asset


def test_qa_passes_when_every_shot_has_a_clean_take(db_session):
    project, revision = _setup_project(db_session, target_frames=90)
    _add_shot_with_take(db_session, project.id, revision.id, 0, qc_outcome="pass")

    report = qa_service.run_revision_qa(db_session, project.id, revision.id)
    assert report.passed
    assert report.issues == []


def test_qa_fails_when_a_shot_has_no_take(db_session):
    project, revision = _setup_project(db_session, target_frames=90)
    shot = Shot(revision_id=revision.id, order_index=0, source_type="gameplay", purpose="no take", target_frames=90)
    db_session.add(shot)
    db_session.commit()

    report = qa_service.run_revision_qa(db_session, project.id, revision.id)
    assert not report.passed
    assert any("hiç kabul edilebilir" in issue for issue in report.issues)


def test_qa_fails_on_failed_technical_qc(db_session):
    project, revision = _setup_project(db_session, target_frames=90)
    _add_shot_with_take(db_session, project.id, revision.id, 0, qc_outcome="fail")

    report = qa_service.run_revision_qa(db_session, project.id, revision.id)
    assert not report.passed
    assert any("teknik QC'yi geçemedi" in issue for issue in report.issues)


def test_qa_fails_on_synthetic_test_origin(db_session):
    project, revision = _setup_project(db_session, target_frames=90)
    _add_shot_with_take(db_session, project.id, revision.id, 0, qc_outcome="pass", origin="synthetic_test")

    report = qa_service.run_revision_qa(db_session, project.id, revision.id)
    assert not report.passed
    assert any("test/sentetik asset" in issue for issue in report.issues)


def test_qa_fails_when_frame_total_mismatches_brief(db_session):
    project, revision = _setup_project(db_session, target_frames=200)
    _add_shot_with_take(db_session, project.id, revision.id, 0, qc_outcome="pass")

    report = qa_service.run_revision_qa(db_session, project.id, revision.id)
    assert not report.passed
    assert any("Toplam sahne süresi" in issue for issue in report.issues)


def test_qa_fails_when_content_review_failed(db_session):
    project, revision = _setup_project(db_session, target_frames=90)
    shot, take, asset = _add_shot_with_take(db_session, project.id, revision.id, 0, qc_outcome="pass")
    db_session.add(
        QAReportRow(
            revision_id=revision.id, asset_id=asset.id, scope="content",
            checks_json={"reasoning": "Uses a forbidden claim", "defects": ["forbidden claim used"]},
            reviewer_model="test/model", outcome="fail", human_status="pending",
            created_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    report = qa_service.run_revision_qa(db_session, project.id, revision.id)
    assert not report.passed
    assert any("içerik incelemesini geçemedi" in issue for issue in report.issues)


def test_qa_passes_when_content_review_is_absent(db_session):
    """Content review is optional — a never-reviewed take must not block
    an otherwise technically-clean QA pass."""
    project, revision = _setup_project(db_session, target_frames=90)
    _add_shot_with_take(db_session, project.id, revision.id, 0, qc_outcome="pass")

    report = qa_service.run_revision_qa(db_session, project.id, revision.id)
    assert report.passed


def test_qa_unknown_revision_is_404(db_session):
    project = projects_service.create_project(db_session, name="QA 404 Testi")

    with pytest.raises(NotFoundError):
        qa_service.run_revision_qa(db_session, project.id, "does-not-exist")


def test_qa_frame_budget_check_uses_the_revision_own_brief_not_the_latest_one(db_session):
    """A revision's `brief_id` (spec §7.2) is the specific Brief version
    its plan was actually generated against, carried forward unchanged by
    every later variation (`app.services.revisions.create_revision_variation`
    propagates `brief_id=base_revision.brief_id`). QA must check the
    frame budget against THAT brief, not whatever the project's current
    "latest" brief happens to be — otherwise editing the brief after a
    plan already exists (a normal, legitimate action) would make QA fail
    forever on every existing revision, even though nothing about the
    revision itself changed. Found live: exactly this happened on a real
    project whose brief had been edited (750-frame target) after its
    plan (600 frames) was already generated and fully produced."""

    project, revision = _setup_project(db_session, target_frames=90)
    _add_shot_with_take(db_session, project.id, revision.id, 0, qc_outcome="pass")

    # editing the brief afterward must not retroactively break this
    # already-existing, already-correct revision's QA
    projects_service.put_brief(
        db_session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=180, fps_num=30, fps_den=1,
        placement_id="p", budget_microusd=1, product_name="Synova", description="d", cta="c",
    )

    report = qa_service.run_revision_qa(db_session, project.id, revision.id)

    assert report.passed
    assert report.issues == []
