def test_capture_enqueues_a_job(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Cekim API Testi"}).json()

    response = api_client.post(
        f"/api/v1/projects/{project['id']}/shots/some-shot-id/capture",
        json={"serial": "emulator-5554"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["job_id"]
    assert body["state"] == "queued"


def test_capture_is_idempotent_per_key(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Cekim Idempotency Testi"}).json()
    payload = {"serial": "emulator-5554"}

    first = api_client.post(
        f"/api/v1/projects/{project['id']}/shots/some-shot-id/capture",
        json=payload,
        headers={"Idempotency-Key": "same-key-capture-1"},
    )
    second = api_client.post(
        f"/api/v1/projects/{project['id']}/shots/some-shot-id/capture",
        json=payload,
        headers={"Idempotency-Key": "same-key-capture-1"},
    )
    assert first.json()["job_id"] == second.json()["job_id"]
