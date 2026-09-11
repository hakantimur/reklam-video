from datetime import datetime, timezone

from app.models.asset import Asset
from app.models.creative import Revision, Shot, Take
from app.services import projects as projects_service


def _setup_shot_with_takes(db_session, n_takes=2):
    project = projects_service.create_project(db_session, name="Take Testi")
    projects_service.put_brief(
        db_session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=600, fps_num=30, fps_den=1,
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
    db_session.flush()

    takes = []
    for i in range(1, n_takes + 1):
        asset = Asset(
            project_id=project.id, type="video", origin="emulator_capture",
            relative_path=f"captures/raw/take{i}.mp4", sha256=f"hash{i}", byte_size=100,
        )
        db_session.add(asset)
        db_session.flush()
        take = Take(shot_id=shot.id, asset_id=asset.id, attempt=i, status="pending")
        db_session.add(take)
        takes.append(take)
    db_session.commit()
    for t in takes:
        db_session.refresh(t)

    return project.id, shot.id, takes


def test_list_takes_returns_all_attempts_in_order(db_session, api_client):
    project_id, shot_id, takes = _setup_shot_with_takes(db_session, n_takes=2)

    response = api_client.get(f"/api/v1/projects/{project_id}/shots/{shot_id}/takes")
    assert response.status_code == 200
    body = response.json()
    assert [t["attempt"] for t in body] == [1, 2]
    assert body[0]["id"] == takes[0].id


def test_list_takes_for_unknown_shot_is_404(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Take 404 Testi"}).json()
    response = api_client.get(f"/api/v1/projects/{project['id']}/shots/does-not-exist/takes")
    assert response.status_code == 404


def test_select_take_sets_shot_selected_take_id(db_session, api_client):
    project_id, shot_id, takes = _setup_shot_with_takes(db_session, n_takes=2)

    response = api_client.post(
        f"/api/v1/projects/{project_id}/shots/{shot_id}/takes/{takes[1].id}/select"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["selected_take_id"] == takes[1].id

    db_session.expire_all()
    fetched = db_session.get(Shot, shot_id)
    assert fetched.selected_take_id == takes[1].id


def test_select_take_from_other_shot_is_404(db_session, api_client):
    project_id, shot_id, takes = _setup_shot_with_takes(db_session, n_takes=1)
    _, other_shot_id, other_takes = _setup_shot_with_takes(db_session, n_takes=1)

    response = api_client.post(
        f"/api/v1/projects/{project_id}/shots/{shot_id}/takes/{other_takes[0].id}/select"
    )
    assert response.status_code == 404
