def test_start_review_enqueues_a_job(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Inceleme API Testi"}).json()

    response = api_client.post(
        f"/api/v1/projects/{project['id']}/shots/some-shot-id/review", json={}
    )
    assert response.status_code == 202
    body = response.json()
    assert body["job_id"]
    assert body["state"] == "queued"


def _setup_shot_with_take(db_session, project_id):
    from datetime import datetime, timezone

    from app.models.asset import Asset
    from app.models.creative import Revision, Shot, Take
    from app.services import projects as projects_service

    projects_service.put_brief(
        db_session, project_id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=90, fps_num=30, fps_den=1,
        placement_id="p", budget_microusd=1, product_name="Synova", description="d", cta="c",
    )
    brief = projects_service.get_latest_brief(db_session, project_id)
    revision = Revision(
        project_id=project_id, brief_id=brief.id, sequence_no=1, status="draft",
        timeline_json={}, content_hash="x", created_at=datetime.now(timezone.utc),
    )
    db_session.add(revision)
    db_session.flush()
    shot = Shot(revision_id=revision.id, order_index=0, source_type="gameplay", purpose="p", target_frames=90)
    db_session.add(shot)
    db_session.flush()
    asset = Asset(
        project_id=project_id, type="video", origin="emulator_capture", relative_path="x.mp4",
        sha256="h", byte_size=1,
    )
    db_session.add(asset)
    db_session.flush()
    take = Take(shot_id=shot.id, asset_id=asset.id, attempt=1, status="pending")
    db_session.add(take)
    db_session.commit()
    return revision, shot, take, asset


def test_get_shot_review_is_null_when_never_reviewed(api_client, db_session):
    project = api_client.post("/api/v1/projects", json={"name": "Hic Incelenmemis Proje"}).json()
    _, shot, _, _ = _setup_shot_with_take(db_session, project["id"])

    response = api_client.get(f"/api/v1/projects/{project['id']}/shots/{shot.id}/review")
    assert response.status_code == 200
    assert response.json() is None


def test_get_shot_review_returns_the_latest_content_report(api_client, db_session):
    from datetime import datetime, timezone

    from app.models.qa import QAReport

    project = api_client.post("/api/v1/projects", json={"name": "Incelenmis Proje"}).json()
    revision, shot, _, asset = _setup_shot_with_take(db_session, project["id"])

    report = QAReport(
        revision_id=revision.id,
        asset_id=asset.id,
        scope="content",
        checks_json={"reasoning": "Marka mesajiyla uyumlu", "defects": []},
        reviewer_model="test/model",
        outcome="pass",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(report)
    db_session.commit()

    response = api_client.get(f"/api/v1/projects/{project['id']}/shots/{shot.id}/review")
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "pass"
    assert body["reasoning"] == "Marka mesajiyla uyumlu"
    assert body["defects"] == []
    assert body["reviewer_model"] == "test/model"
