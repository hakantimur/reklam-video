def test_get_qa_for_unknown_revision_is_404(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "QA API Testi"}).json()

    response = api_client.get(f"/api/v1/projects/{project['id']}/revisions/does-not-exist/qa")
    assert response.status_code == 404


def test_start_export_enqueues_a_job(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Export API Testi"}).json()

    response = api_client.post(f"/api/v1/projects/{project['id']}/revisions/some-revision-id/export")
    assert response.status_code == 202
    body = response.json()
    assert body["job_id"]
    assert body["state"] == "queued"
