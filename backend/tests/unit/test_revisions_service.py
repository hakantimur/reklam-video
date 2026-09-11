from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.asset import Asset
from app.models.creative import Revision, Shot, Take
from app.schemas.shot_plan import ActionConstraints, HandlesFrames, Shot as ShotPlanShot, ShotLocks, SuccessPredicate
from app.services import projects as projects_service
from app.services import revisions as revisions_service
from app.services.errors import NotFoundError, ValidationAppError


def _revised_shot(**overrides) -> ShotPlanShot:
    defaults = dict(
        id="shot-will-be-overridden",
        source_type="ai_generated",
        purpose="Revised purpose",
        target_frames=90,
        handles_frames=HandlesFrames(),
        start_state={},
        desired_event=None,
        success_predicate=SuccessPredicate(required_observations=[], evidence_required=False),
        action_constraints=ActionConstraints(),
        caption="Yeni yazi",
        voice_text=None,
        fallback=None,
        locks=ShotLocks(),
    )
    defaults.update(overrides)
    return ShotPlanShot(**defaults)


def _setup_base_revision(session, *, shot_kwargs_list):
    project = projects_service.create_project(session, name="Varyasyon Testi")
    projects_service.put_brief(
        session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=sum(k.get("target_frames", 90) for k in shot_kwargs_list),
        fps_num=30, fps_den=1, placement_id="p", budget_microusd=1,
        product_name="Synova", description="d", cta="c",
    )
    brief = projects_service.get_latest_brief(session, project.id)
    revision = Revision(
        project_id=project.id, brief_id=brief.id, sequence_no=1, status="draft",
        timeline_json={}, content_hash="x", created_at=datetime.now(timezone.utc),
    )
    session.add(revision)
    session.flush()

    shots = []
    for index, kwargs in enumerate(shot_kwargs_list):
        kwargs = dict(kwargs)
        target_frames = kwargs.pop("target_frames", 90)
        locks = kwargs.pop("locks", None)
        shot = Shot(
            revision_id=revision.id, order_index=index, target_frames=target_frames,
            locks_json=locks or {"visual": False, "voice": False, "caption": False, "timing": False},
            **kwargs,
        )
        session.add(shot)
        shots.append(shot)
    session.commit()
    for s in shots:
        session.refresh(s)
    return project, revision, shots


def _fake_provider(revised_shot: ShotPlanShot):
    provider = MagicMock()
    provider.generate_structured.return_value = revised_shot.model_dump()
    return provider


def test_variation_regenerates_only_instructed_unlocked_shots(monkeypatch, db_session):
    project, revision, shots = _setup_base_revision(
        db_session,
        shot_kwargs_list=[
            {"source_type": "ai_generated", "purpose": "Hook", "target_frames": 90},
            {"source_type": "composed", "purpose": "CTA", "target_frames": 90},
        ],
    )
    target_shot = shots[0]
    revised = _revised_shot(id=target_shot.id, target_frames=target_shot.target_frames, purpose="New hook")

    from app.services import revisions as revisions_mod

    monkeypatch.setattr(revisions_mod, "regenerate_shot", lambda *a, **k: revised)

    new_revision = revisions_service.create_revision_variation(
        db_session, project.id, revision.id,
        shot_instructions={target_shot.id: "Make it punchier"},
        provider=MagicMock(), model="test/model",
    )

    assert new_revision.parent_id == revision.id
    assert new_revision.sequence_no == 2

    from app.services import plans as plans_service

    new_shots = plans_service.get_shots_for_revision(db_session, new_revision.id)
    assert len(new_shots) == 2
    assert new_shots[0].purpose == "New hook"
    assert new_shots[1].purpose == "CTA"  # untouched, carried forward


def test_variation_rejects_instruction_on_visually_locked_shot(db_session):
    project, revision, shots = _setup_base_revision(
        db_session,
        shot_kwargs_list=[
            {"source_type": "ai_generated", "purpose": "Hook", "target_frames": 90,
             "locks": {"visual": True, "voice": False, "caption": False, "timing": False}},
        ],
    )

    with pytest.raises(ValidationAppError):
        revisions_service.create_revision_variation(
            db_session, project.id, revision.id,
            shot_instructions={shots[0].id: "Change it anyway"},
            provider=MagicMock(), model="test/model",
        )


def test_variation_carries_forward_selected_take_under_new_shot_id(monkeypatch, db_session):
    project, revision, shots = _setup_base_revision(
        db_session,
        shot_kwargs_list=[
            {"source_type": "gameplay", "purpose": "Play", "target_frames": 90},
            {"source_type": "composed", "purpose": "CTA", "target_frames": 90},
        ],
    )
    gameplay_shot = shots[0]
    asset = Asset(
        project_id=project.id, type="video", origin="emulator_capture",
        relative_path="captures/raw/x.mp4", sha256="h", byte_size=1,
    )
    db_session.add(asset)
    db_session.flush()
    take = Take(shot_id=gameplay_shot.id, asset_id=asset.id, attempt=1, status="pending")
    db_session.add(take)
    db_session.flush()
    gameplay_shot.selected_take_id = take.id
    db_session.commit()

    cta_shot = shots[1]
    revised = _revised_shot(id=cta_shot.id, target_frames=cta_shot.target_frames, source_type="composed", purpose="New CTA")
    from app.services import revisions as revisions_mod

    monkeypatch.setattr(revisions_mod, "regenerate_shot", lambda *a, **k: revised)

    new_revision = revisions_service.create_revision_variation(
        db_session, project.id, revision.id,
        shot_instructions={cta_shot.id: "Change CTA"},
        provider=MagicMock(), model="m",
    )

    from app.services import plans as plans_service

    new_shots = plans_service.get_shots_for_revision(db_session, new_revision.id)
    new_gameplay_shot = new_shots[0]
    assert new_gameplay_shot.selected_take_id is not None
    assert new_gameplay_shot.selected_take_id != take.id  # a new Take row, not the same FK

    new_take = db_session.get(Take, new_gameplay_shot.selected_take_id)
    assert new_take.asset_id == asset.id  # same underlying video, different Take row
    assert new_take.shot_id == new_gameplay_shot.id


def test_variation_carries_forward_a_take_even_without_explicit_selection(monkeypatch, db_session):
    """An AI-generated/gameplay shot whose take was never explicitly
    "selected" (no select-take UI action happened) must still survive a
    variation of an unrelated shot — losing it silently would be a real
    regression a user would only discover once it's too late."""

    project, revision, shots = _setup_base_revision(
        db_session,
        shot_kwargs_list=[
            {"source_type": "ai_generated", "purpose": "Hook", "target_frames": 90},
            {"source_type": "composed", "purpose": "CTA", "target_frames": 90},
        ],
    )
    hook_shot = shots[0]
    asset = Asset(
        project_id=project.id, type="video", origin="provider_generation",
        relative_path="generated/video/x.mp4", sha256="h", byte_size=1,
    )
    db_session.add(asset)
    db_session.flush()
    take = Take(shot_id=hook_shot.id, asset_id=asset.id, attempt=1, status="pending")
    db_session.add(take)
    db_session.commit()  # note: hook_shot.selected_take_id is never set

    cta_shot = shots[1]
    revised = _revised_shot(id=cta_shot.id, target_frames=cta_shot.target_frames, source_type="composed", purpose="New CTA")
    from app.services import revisions as revisions_mod

    monkeypatch.setattr(revisions_mod, "regenerate_shot", lambda *a, **k: revised)

    new_revision = revisions_service.create_revision_variation(
        db_session, project.id, revision.id,
        shot_instructions={cta_shot.id: "Change CTA"},
        provider=MagicMock(), model="m",
    )

    from app.services import plans as plans_service

    new_hook_shot = plans_service.get_shots_for_revision(db_session, new_revision.id)[0]
    assert new_hook_shot.selected_take_id is not None
    new_take = db_session.get(Take, new_hook_shot.selected_take_id)
    assert new_take.asset_id == asset.id


def test_variation_carries_forward_a_voice_over_asset_to_the_new_shot_id(monkeypatch, db_session):
    """A voice-over Asset points at its shot via inline
    `metadata_json.shot_id` (no dedicated join table the way Takes have
    one) — a carried-forward shot gets a brand new Shot row/id, so without
    repointing that metadata, an already-generated, already-paid-for
    voice-over would silently vanish from the Taslak screen and the
    timeline the same way an unselected take used to."""

    project, revision, shots = _setup_base_revision(
        db_session,
        shot_kwargs_list=[
            {"source_type": "ai_generated", "purpose": "Hook", "target_frames": 90, "voice_text": "Merhaba"},
            {"source_type": "composed", "purpose": "CTA", "target_frames": 90},
        ],
    )
    hook_shot = shots[0]
    voice_asset = Asset(
        project_id=project.id, type="audio", origin="provider_generation",
        relative_path="generated/audio/x.mp3", sha256="h", byte_size=1,
        metadata_json={"shot_id": hook_shot.id, "role": "voice_over", "voice_id": "v1"},
    )
    db_session.add(voice_asset)
    db_session.commit()

    cta_shot = shots[1]
    revised = _revised_shot(id=cta_shot.id, target_frames=cta_shot.target_frames, source_type="composed", purpose="New CTA")
    from app.services import revisions as revisions_mod

    monkeypatch.setattr(revisions_mod, "regenerate_shot", lambda *a, **k: revised)

    new_revision = revisions_service.create_revision_variation(
        db_session, project.id, revision.id,
        shot_instructions={cta_shot.id: "Change CTA"},
        provider=MagicMock(), model="m",
    )

    from app.services import plans as plans_service

    new_hook_shot = plans_service.get_shots_for_revision(db_session, new_revision.id)[0]
    assert new_hook_shot.id != hook_shot.id  # carry-forward always mints a new Shot row

    db_session.refresh(voice_asset)
    assert voice_asset.metadata_json["shot_id"] == hook_shot.id  # original untouched, not mutated

    cloned = (
        db_session.query(Asset)
        .filter(Asset.project_id == project.id, Asset.id != voice_asset.id, Asset.type == "audio")
        .one()
    )
    assert cloned.metadata_json["shot_id"] == new_hook_shot.id
    assert cloned.metadata_json["role"] == "voice_over"  # untouched fields survive
    assert cloned.relative_path == voice_asset.relative_path  # same underlying file, no re-upload
    assert cloned.sha256 == voice_asset.sha256


def test_variation_does_not_steal_a_voice_over_from_a_sibling_variation(monkeypatch, db_session):
    """Two variations can share the same parent revision (a branching
    tree, not a line) — found live: mutating the voice Asset's shot_id in
    place meant whichever sibling ran first "stole" the voice-over from
    every other sibling still carrying forward the same base shot. Each
    variation must get its own reference to the same underlying file."""

    project, revision, shots = _setup_base_revision(
        db_session,
        shot_kwargs_list=[
            {"source_type": "ai_generated", "purpose": "Hook", "target_frames": 90, "voice_text": "Merhaba"},
            {"source_type": "composed", "purpose": "CTA", "target_frames": 90},
        ],
    )
    hook_shot = shots[0]
    voice_asset = Asset(
        project_id=project.id, type="audio", origin="provider_generation",
        relative_path="generated/audio/x.mp3", sha256="h", byte_size=1,
        metadata_json={"shot_id": hook_shot.id, "role": "voice_over"},
    )
    db_session.add(voice_asset)
    db_session.commit()

    cta_shot = shots[1]
    revised = _revised_shot(id=cta_shot.id, target_frames=cta_shot.target_frames, source_type="composed", purpose="New CTA")
    from app.services import revisions as revisions_mod

    monkeypatch.setattr(revisions_mod, "regenerate_shot", lambda *a, **k: revised)

    from app.services import plans as plans_service

    sibling_a = revisions_service.create_revision_variation(
        db_session, project.id, revision.id, shot_instructions={cta_shot.id: "Variant A"},
        provider=MagicMock(), model="m",
    )
    sibling_b = revisions_service.create_revision_variation(
        db_session, project.id, revision.id, shot_instructions={cta_shot.id: "Variant B"},
        provider=MagicMock(), model="m",
    )

    hook_a = plans_service.get_shots_for_revision(db_session, sibling_a.id)[0]
    hook_b = plans_service.get_shots_for_revision(db_session, sibling_b.id)[0]

    voice_assets = db_session.query(Asset).filter(Asset.project_id == project.id, Asset.type == "audio").all()
    shot_ids_with_voice = {a.metadata_json.get("shot_id") for a in voice_assets}
    assert hook_a.id in shot_ids_with_voice
    assert hook_b.id in shot_ids_with_voice  # not silently lost because sibling_a ran first


def test_variation_carries_forward_voice_asset_when_voice_locked_on_an_instructed_shot(monkeypatch, db_session):
    """A shot can be instructed to change (e.g. its visuals) while its
    voice stays locked — `voice_text` is then kept byte-identical to the
    base shot, so a previously generated voice-over still matches and
    must not be silently dropped just because this shot went through the
    `if instruction:` branch instead of the untouched carry-forward one."""

    project, revision, shots = _setup_base_revision(
        db_session,
        shot_kwargs_list=[
            {
                "source_type": "ai_generated", "purpose": "Hook", "target_frames": 90,
                "voice_text": "Sabit seslendirme metni",
                "locks": {"visual": False, "voice": True, "caption": False, "timing": False},
            },
        ],
    )
    hook_shot = shots[0]
    voice_asset = Asset(
        project_id=project.id, type="audio", origin="provider_generation",
        relative_path="generated/audio/x.mp3", sha256="h", byte_size=1,
        metadata_json={"shot_id": hook_shot.id, "role": "voice_over", "voice_id": "v1"},
    )
    db_session.add(voice_asset)
    db_session.commit()

    revised = _revised_shot(
        id=hook_shot.id, target_frames=hook_shot.target_frames, purpose="Punchier hook",
        voice_text="Bu talimat tarafindan degistirilmis olurdu ama kilit korumali",
    )
    from app.services import revisions as revisions_mod

    monkeypatch.setattr(revisions_mod, "regenerate_shot", lambda *a, **k: revised)

    new_revision = revisions_service.create_revision_variation(
        db_session, project.id, revision.id,
        shot_instructions={hook_shot.id: "Make the visuals punchier, keep the voice"},
        provider=MagicMock(), model="m",
    )

    from app.services import plans as plans_service

    new_hook_shot = plans_service.get_shots_for_revision(db_session, new_revision.id)[0]
    assert new_hook_shot.id != hook_shot.id
    assert new_hook_shot.voice_text == "Sabit seslendirme metni"  # lock preserved base text
    assert new_hook_shot.purpose == "Punchier hook"  # unlocked field still changed

    db_session.refresh(voice_asset)
    assert voice_asset.metadata_json["shot_id"] == hook_shot.id  # original untouched

    cloned = (
        db_session.query(Asset)
        .filter(Asset.project_id == project.id, Asset.id != voice_asset.id, Asset.type == "audio")
        .one()
    )
    assert cloned.metadata_json["shot_id"] == new_hook_shot.id


def test_variation_rejects_unknown_shot_id(db_session):
    project, revision, shots = _setup_base_revision(
        db_session, shot_kwargs_list=[{"source_type": "composed", "purpose": "CTA", "target_frames": 90}]
    )

    with pytest.raises(ValidationAppError):
        revisions_service.create_revision_variation(
            db_session, project.id, revision.id,
            shot_instructions={"does-not-exist": "x"},
            provider=MagicMock(), model="m",
        )


def test_variation_unknown_revision_is_404(db_session):
    project = projects_service.create_project(db_session, name="Revizyonsuz Proje")

    with pytest.raises(NotFoundError):
        revisions_service.create_revision_variation(
            db_session, project.id, "does-not-exist",
            shot_instructions={"x": "y"},
            provider=MagicMock(), model="m",
        )


def test_set_shot_locks_merges_a_partial_update(db_session):
    project, revision, shots = _setup_base_revision(
        db_session,
        shot_kwargs_list=[
            {
                "source_type": "ai_generated", "purpose": "Hook", "target_frames": 90,
                "locks": {"visual": False, "voice": False, "caption": False, "timing": False},
            },
        ],
    )
    shot = shots[0]

    updated = revisions_service.set_shot_locks(db_session, project.id, shot.id, {"voice": True})

    assert updated.locks_json == {"visual": False, "voice": True, "caption": False, "timing": False}

    updated_again = revisions_service.set_shot_locks(db_session, project.id, shot.id, {"visual": True})
    # a second, disjoint update must not clobber the first one
    assert updated_again.locks_json == {"visual": True, "voice": True, "caption": False, "timing": False}


def test_set_shot_locks_unknown_shot_is_404(db_session):
    project = projects_service.create_project(db_session, name="Kilit Testi Projesi")

    with pytest.raises(NotFoundError):
        revisions_service.set_shot_locks(db_session, project.id, "does-not-exist", {"visual": True})


def test_set_shot_locks_rejects_a_shot_from_another_project(db_session):
    project_a, revision_a, shots_a = _setup_base_revision(
        db_session, shot_kwargs_list=[{"source_type": "composed", "purpose": "CTA", "target_frames": 90}]
    )
    project_b = projects_service.create_project(db_session, name="Baska Proje")

    with pytest.raises(NotFoundError):
        revisions_service.set_shot_locks(db_session, project_b.id, shots_a[0].id, {"visual": True})
