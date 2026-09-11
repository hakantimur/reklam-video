"""Mock-only tests: fakes `technical_qc.sample_frames_png` (no real ffmpeg/
opencv dependency on a fake video file) and `agents.reviewer.review_take`
(no real LLM call), to prove the review service's own logic (take
resolution, QAReport persistence, asset-scoped review reuse across
revisions) independent of any real provider or media file."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.asset import Asset
from app.models.creative import Revision, Shot, Take
from app.schemas.review import TakeReview
from app.services import projects as projects_service
from app.services import review as review_service
from app.services.errors import NotFoundError, ValidationAppError


def _setup_shot_with_take(session, *, verified_claims=None, forbidden_claims=None):
    project = projects_service.create_project(session, name="Inceleme Testi")
    projects_service.put_brief(
        session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=90, fps_num=30, fps_den=1,
        placement_id="p", budget_microusd=1, product_name="Synova", description="d", cta="c",
    )
    brief = projects_service.get_latest_brief(session, project.id)
    if verified_claims is not None or forbidden_claims is not None:
        from app.models.project import BrandProfile

        brand = session.query(BrandProfile).filter_by(project_id=project.id).one()
        brand.verified_claims_json = verified_claims or []
        brand.forbidden_claims_json = forbidden_claims or []
        session.commit()

    revision = Revision(
        project_id=project.id, brief_id=brief.id, sequence_no=1, status="draft",
        timeline_json={}, content_hash="x", created_at=datetime.now(timezone.utc),
    )
    session.add(revision)
    session.flush()
    shot = Shot(revision_id=revision.id, order_index=0, source_type="gameplay", purpose="p", target_frames=90)
    session.add(shot)
    session.flush()

    asset = Asset(
        project_id=project.id, type="video", origin="emulator_capture", relative_path="x.mp4",
        sha256="h", byte_size=1,
    )
    session.add(asset)
    session.flush()
    take = Take(shot_id=shot.id, asset_id=asset.id, attempt=1, status="pending")
    session.add(take)
    session.commit()

    return project, shot, take, asset


@pytest.fixture(autouse=True)
def _fake_frame_sampling(monkeypatch):
    monkeypatch.setattr(review_service, "sample_frames_png", lambda path, count: [b"fake-png"] * count)


@pytest.fixture(autouse=True)
def _fake_asset_resolution(monkeypatch, tmp_path):
    fake_video = tmp_path / "fake.mp4"
    fake_video.write_bytes(b"x")
    monkeypatch.setattr(
        review_service.assets_service, "resolve_asset_path", lambda session, asset_id: (None, fake_video)
    )


def test_review_shot_take_persists_a_content_qa_report(monkeypatch, db_session):
    project, shot, take, asset = _setup_shot_with_take(db_session)
    verdict = TakeReview(outcome="pass", reasoning="Matches the shot objective", defects=[])
    monkeypatch.setattr(review_service, "review_take", lambda *a, **k: verdict)

    report = review_service.review_shot_take(
        db_session, project.id, shot.id, provider=MagicMock(), model="test/model"
    )

    assert report.scope == "content"
    assert report.outcome == "pass"
    assert report.asset_id == asset.id
    assert report.reviewer_model == "test/model"


def test_review_shot_take_forwards_forbidden_claims_to_the_agent(monkeypatch, db_session):
    project, shot, take, asset = _setup_shot_with_take(
        db_session, verified_claims=["Free trial"], forbidden_claims=["Guaranteed results"]
    )
    captured = {}

    def fake_review_take(*a, **kwargs):
        captured.update(kwargs)
        return TakeReview(outcome="fail", reasoning="Uses a forbidden claim", defects=["forbidden claim used"])

    monkeypatch.setattr(review_service, "review_take", fake_review_take)

    report = review_service.review_shot_take(
        db_session, project.id, shot.id, provider=MagicMock(), model="test/model"
    )

    assert captured["verified_claims"] == ["Free trial"]
    assert captured["forbidden_claims"] == ["Guaranteed results"]
    assert report.outcome == "fail"
    assert report.checks_json["defects"] == ["forbidden claim used"]


def test_review_shot_take_requires_an_existing_take(db_session):
    project = projects_service.create_project(db_session, name="Take'siz Proje")
    projects_service.put_brief(
        db_session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=90, fps_num=30, fps_den=1,
        placement_id="p", budget_microusd=1, product_name="X", description="d", cta="c",
    )
    brief = projects_service.get_latest_brief(db_session, project.id)
    revision = Revision(
        project_id=project.id, brief_id=brief.id, sequence_no=1, status="draft",
        timeline_json={}, content_hash="x", created_at=datetime.now(timezone.utc),
    )
    db_session.add(revision)
    db_session.flush()
    shot = Shot(revision_id=revision.id, order_index=0, source_type="gameplay", purpose="p", target_frames=90)
    db_session.add(shot)
    db_session.commit()

    with pytest.raises(ValidationAppError):
        review_service.review_shot_take(db_session, project.id, shot.id, provider=MagicMock(), model="m")


def test_review_shot_take_unknown_shot_is_404(db_session):
    project = projects_service.create_project(db_session, name="Bilinmeyen Sahne Projesi")

    with pytest.raises(NotFoundError):
        review_service.review_shot_take(db_session, project.id, "does-not-exist", provider=MagicMock(), model="m")


def test_get_latest_content_review_for_asset_returns_none_when_unreviewed(db_session):
    project, shot, take, asset = _setup_shot_with_take(db_session)

    assert review_service.get_latest_content_review_for_asset(db_session, asset.id) is None
