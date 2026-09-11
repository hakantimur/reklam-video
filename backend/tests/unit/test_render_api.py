def test_get_timeline_is_null_before_any_plan(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Timeline API Testi"}).json()

    response = api_client.get(f"/api/v1/projects/{project['id']}/timeline")
    assert response.status_code == 200
    assert response.json() is None


def test_build_timeline_without_plan_is_422(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Timeline API Testi 2"}).json()

    response = api_client.post(f"/api/v1/projects/{project['id']}/timeline/build")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_start_render_preview_enqueues_a_job(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Render API Testi"}).json()

    response = api_client.post(f"/api/v1/projects/{project['id']}/render/preview")
    assert response.status_code == 202
    body = response.json()
    assert body["job_id"]
    assert body["state"] == "queued"
