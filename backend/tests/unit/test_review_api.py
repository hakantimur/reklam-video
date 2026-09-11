def test_start_review_enqueues_a_job(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Inceleme API Testi"}).json()

    response = api_client.post(
        f"/api/v1/projects/{project['id']}/shots/some-shot-id/review", json={}
    )
    assert response.status_code == 202
    body = response.json()
    assert body["job_id"]
    assert body["state"] == "queued"
