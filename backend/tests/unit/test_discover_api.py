def test_discover_enqueues_a_job(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Discover API Testi"}).json()

    response = api_client.post(
        f"/api/v1/projects/{project['id']}/discover",
        json={"serial": "emulator-5554", "package_id": "com.example.synova.dev"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["job_id"]
    assert body["state"] == "queued"


def test_discover_is_idempotent_per_key(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Discover Idempotency Testi"}).json()
    payload = {"serial": "emulator-5554", "package_id": "com.example.synova.dev"}

    first = api_client.post(
        f"/api/v1/projects/{project['id']}/discover",
        json=payload,
        headers={"Idempotency-Key": "same-key-1"},
    )
    second = api_client.post(
        f"/api/v1/projects/{project['id']}/discover",
        json=payload,
        headers={"Idempotency-Key": "same-key-1"},
    )
    assert first.json()["job_id"] == second.json()["job_id"]
