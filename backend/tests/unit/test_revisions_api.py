def test_create_variation_without_api_key_is_blocked(api_client, monkeypatch):
    import app.api.revisions as revisions_api

    monkeypatch.setattr(revisions_api.credentials_service, "get_credential_value", lambda p: None)
    project = api_client.post("/api/v1/projects", json={"name": "Varyasyon Anahtarsiz"}).json()

    response = api_client.post(
        f"/api/v1/projects/{project['id']}/revisions/does-not-exist/variation",
        json={"shot_instructions": {"shot-1": "x"}},
    )
    # No OpenRouter key configured in the test environment -> blocked before
    # the (nonexistent) revision is even looked up.
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "blocked"


def _setup_shot(db_session, project_id):
    from datetime import datetime, timezone

    from app.models.creative import Revision, Shot
    from app.services import projects as projects_service

    projects_service.put_brief(
        db_session, project_id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=90, fps_num=30, fps_den=1,
        placement_id="p", budget_microusd=1, product_name="X", description="d", cta="c",
    )
    brief = projects_service.get_latest_brief(db_session, project_id)
    revision = Revision(
        project_id=project_id, brief_id=brief.id, sequence_no=1, status="draft",
        timeline_json={}, content_hash="x", created_at=datetime.now(timezone.utc),
    )
    db_session.add(revision)
    db_session.flush()
    shot = Shot(
        revision_id=revision.id, order_index=0, source_type="ai_generated", purpose="p", target_frames=90,
        locks_json={"visual": False, "voice": False, "caption": False, "timing": False},
    )
    db_session.add(shot)
    db_session.commit()
    return shot


def test_update_shot_locks_merges_a_partial_update(api_client, db_session):
    project = api_client.post("/api/v1/projects", json={"name": "Kilit API Testi"}).json()
    shot = _setup_shot(db_session, project["id"])

    response = api_client.patch(f"/api/v1/projects/{project['id']}/shots/{shot.id}/locks", json={"voice": True})
    assert response.status_code == 200
    body = response.json()
    assert body["locks"] == {"visual": False, "voice": True, "caption": False, "timing": False}

    response2 = api_client.patch(f"/api/v1/projects/{project['id']}/shots/{shot.id}/locks", json={"visual": True})
    assert response2.json()["locks"] == {"visual": True, "voice": True, "caption": False, "timing": False}


def test_update_shot_locks_unknown_shot_is_404(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Kilit 404 Testi"}).json()

    response = api_client.patch(
        f"/api/v1/projects/{project['id']}/shots/does-not-exist/locks", json={"visual": True}
    )
    assert response.status_code == 404
