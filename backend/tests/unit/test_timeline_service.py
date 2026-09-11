from datetime import datetime, timezone

from app.models.asset import Asset
from app.models.creative import Revision, Shot, Take
from app.services import projects as projects_service
from app.services import timeline as timeline_service
from app.services.errors import ValidationAppError

import pytest


def _setup_project(session):
    project = projects_service.create_project(session, name="Timeline Testi")
    projects_service.put_brief(
        session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=600, fps_num=30, fps_den=1,
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


def _add_asset(session, project_id, **kwargs):
    defaults = dict(type="video", origin="emulator_capture", relative_path="x.mp4", sha256="h", byte_size=1)
    defaults.update(kwargs)
    asset = Asset(project_id=project_id, **defaults)
    session.add(asset)
    session.flush()
    return asset


def test_build_timeline_positions_shots_sequentially(db_session):
    project, revision = _setup_project(db_session)
    shot1 = Shot(revision_id=revision.id, order_index=0, source_type="gameplay", purpose="p1", target_frames=90)
    shot2 = Shot(revision_id=revision.id, order_index=1, source_type="ai_generated", purpose="p2", target_frames=120, caption_text="Merhaba")
    db_session.add_all([shot1, shot2])
    db_session.flush()

    asset1 = _add_asset(db_session, project.id)
    take1 = Take(shot_id=shot1.id, asset_id=asset1.id, attempt=1, status="pending")
    db_session.add(take1)
    db_session.commit()

    timeline = timeline_service.build_timeline(db_session, project.id)

    assert timeline["duration_frames"] == 210
    video_items = timeline["tracks"][0]["items"]
    assert video_items[0]["start_frame"] == 0
    assert video_items[0]["asset_id"] == asset1.id
    assert video_items[1]["start_frame"] == 90
    assert video_items[1]["asset_id"] is None  # shot2 has no take yet

    subtitle_items = timeline["tracks"][2]["items"]
    assert len(subtitle_items) == 1
    assert subtitle_items[0]["shot_id"] == shot2.id
    assert subtitle_items[0]["transform"]["captionText"] == "Merhaba"


def test_build_timeline_prefers_selected_take_over_latest(db_session):
    project, revision = _setup_project(db_session)
    shot = Shot(revision_id=revision.id, order_index=0, source_type="gameplay", purpose="p", target_frames=60)
    db_session.add(shot)
    db_session.flush()

    asset1 = _add_asset(db_session, project.id, relative_path="a1.mp4")
    asset2 = _add_asset(db_session, project.id, relative_path="a2.mp4")
    take1 = Take(shot_id=shot.id, asset_id=asset1.id, attempt=1, status="pending")
    take2 = Take(shot_id=shot.id, asset_id=asset2.id, attempt=2, status="pending")
    db_session.add_all([take1, take2])
    db_session.flush()

    shot.selected_take_id = take1.id
    db_session.commit()

    timeline = timeline_service.build_timeline(db_session, project.id)
    assert timeline["tracks"][0]["items"][0]["asset_id"] == asset1.id


def test_build_timeline_includes_voice_asset_for_shot(db_session):
    project, revision = _setup_project(db_session)
    shot = Shot(revision_id=revision.id, order_index=0, source_type="composed", purpose="p", target_frames=60)
    db_session.add(shot)
    db_session.flush()

    voice_asset = _add_asset(
        db_session, project.id, type="audio", origin="provider_generation", relative_path="v.mp3",
        metadata_json={"shot_id": shot.id, "role": "voice_over"},
    )
    db_session.commit()

    timeline = timeline_service.build_timeline(db_session, project.id)
    voice_items = timeline["tracks"][1]["items"]
    assert len(voice_items) == 1
    assert voice_items[0]["asset_id"] == voice_asset.id


def test_build_timeline_without_plan_is_validation_error(db_session):
    project = projects_service.create_project(db_session, name="Plansiz Proje")

    with pytest.raises(ValidationAppError):
        timeline_service.build_timeline(db_session, project.id)
