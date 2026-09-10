from app.jobs.queue import JobQueue
from app.services.projects import create_project


def test_get_job_returns_current_state(api_client, db_session):
    project = create_project(db_session, name="Job API Testi")
    queue = JobQueue()
    job = queue.enqueue(db_session, project_id=project.id, kind="dummy_echo", idempotency_key="api-get-1")

    response = api_client.get(f"/api/v1/jobs/{job.id}")
    assert response.status_code == 200
    assert response.json()["state"] == "queued"
    assert response.json()["id"] == job.id


def test_get_unknown_job_returns_structured_404(api_client):
    response = api_client.get("/api/v1/jobs/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_pause_resume_cancel_via_api(api_client, db_session):
    project = create_project(db_session, name="Job API Pause Testi")
    queue = JobQueue()
    job = queue.enqueue(db_session, project_id=project.id, kind="dummy_echo", idempotency_key="api-pause-1")

    paused = api_client.post(f"/api/v1/jobs/{job.id}/pause")
    assert paused.status_code == 200
    assert paused.json()["state"] == "paused"

    resumed = api_client.post(f"/api/v1/jobs/{job.id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["state"] == "queued"

    cancelled = api_client.post(f"/api/v1/jobs/{job.id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "cancelled"


def test_resume_non_paused_job_returns_structured_409(api_client, db_session):
    project = create_project(db_session, name="Job API Conflict Testi")
    queue = JobQueue()
    job = queue.enqueue(db_session, project_id=project.id, kind="dummy_echo", idempotency_key="api-conflict-1")

    response = api_client.post(f"/api/v1/jobs/{job.id}/resume")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
