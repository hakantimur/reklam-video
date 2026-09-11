"""`GET /projects/{id}/revisions` — spec §5.3 "önceki sürümle
karşılaştırma" read side: the full revision history, newest first."""

from datetime import datetime, timezone

from app.models.creative import Revision, Shot
from app.services import projects as projects_service


def _setup_project_with_revisions(session, *, count: int):
    project = projects_service.create_project(session, name="Revizyon Gecmisi Testi")
    projects_service.put_brief(
        session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=90, fps_num=30, fps_den=1,
        placement_id="p", budget_microusd=1, product_name="X", description="d", cta="c",
    )
    brief = projects_service.get_latest_brief(session, project.id)

    parent_id = None
    revisions = []
    for seq in range(1, count + 1):
        revision = Revision(
            project_id=project.id, brief_id=brief.id, sequence_no=seq, status="draft",
            parent_id=parent_id, timeline_json={}, content_hash=f"h{seq}",
            change_summary=f"Değişiklik #{seq}" if seq > 1 else None,
            created_at=datetime.now(timezone.utc),
        )
        session.add(revision)
        session.flush()
        shot = Shot(revision_id=revision.id, order_index=0, source_type="composed", purpose="p", target_frames=90)
        session.add(shot)
        session.flush()
        revisions.append(revision)
        parent_id = revision.id
    session.commit()
    return project, revisions


def test_list_revisions_returns_newest_first_with_shot_counts(api_client, db_session):
    project, revisions = _setup_project_with_revisions(db_session, count=3)

    response = api_client.get(f"/api/v1/projects/{project.id}/revisions")
    assert response.status_code == 200
    body = response.json()

    assert [r["sequence_no"] for r in body] == [3, 2, 1]
    assert body[0]["change_summary"] == "Değişiklik #3"
    assert body[0]["parent_id"] == revisions[1].id
    assert body[-1]["parent_id"] is None
    assert all(r["shot_count"] == 1 for r in body)


def test_list_revisions_is_empty_for_a_project_with_no_plan(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Plansiz Proje"}).json()

    response = api_client.get(f"/api/v1/projects/{project['id']}/revisions")
    assert response.status_code == 200
    assert response.json() == []


def test_list_revisions_does_not_leak_across_projects(api_client, db_session):
    project_a, _ = _setup_project_with_revisions(db_session, count=1)
    project_b = api_client.post("/api/v1/projects", json={"name": "Baska Proje"}).json()

    response = api_client.get(f"/api/v1/projects/{project_b['id']}/revisions")
    assert response.status_code == 200
    assert response.json() == []
