"""`GET /projects/{id}/budget` — the read side of `app.services.budget`,
which real job handlers (`_settle_llm_cost`/`_settle_generation_cost`)
have been writing real `BudgetEntry` rows into all session with nothing
to read them back."""

from app.jobs.queue import JobQueue
from app.services import budget as budget_service
from app.services import projects as projects_service


def _project_with_budget(db_session, budget_microusd=100_000_000, name="Butce API Testi"):
    project = projects_service.create_project(db_session, name=name)
    projects_service.put_brief(
        db_session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=300, fps_num=30, fps_den=1,
        placement_id="p", budget_microusd=budget_microusd, product_name="X", description="d", cta="c",
    )
    return project


def test_get_budget_with_no_activity_returns_full_cap_available(api_client, db_session):
    project = _project_with_budget(db_session, budget_microusd=100_000_000)

    response = api_client.get(f"/api/v1/projects/{project.id}/budget")
    assert response.status_code == 200
    body = response.json()
    assert body["user_cap_microusd"] == 100_000_000
    assert body["settled_cost_microusd"] == 0
    assert body["active_reservations_microusd"] == 0
    assert body["available_microusd"] == 100_000_000


def test_get_budget_reflects_a_real_settlement(api_client, db_session):
    project = _project_with_budget(db_session, budget_microusd=100_000_000)
    queue = JobQueue(worker_id="budget-api-test-worker")
    job = queue.enqueue(db_session, project_id=project.id, kind="dummy_echo", idempotency_key="budget-api-1")
    budget_service.settle(db_session, project.id, job_id=job.id, actual_amount_microusd=5_957)

    response = api_client.get(f"/api/v1/projects/{project.id}/budget")
    assert response.status_code == 200
    body = response.json()
    assert body["settled_cost_microusd"] == 5_957
    assert body["available_microusd"] == 100_000_000 - 5_957


def test_get_budget_without_a_brief_has_no_cap(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Briefsiz Proje"}).json()

    response = api_client.get(f"/api/v1/projects/{project['id']}/budget")
    assert response.status_code == 200
    body = response.json()
    assert body["user_cap_microusd"] is None
    assert body["available_microusd"] is None
