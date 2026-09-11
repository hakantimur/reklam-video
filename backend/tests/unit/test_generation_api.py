def test_generate_scene_enqueues_a_job(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Sahne API Testi"}).json()

    response = api_client.post(
        f"/api/v1/projects/{project['id']}/shots/some-shot-id/generate-scene",
        json={"video_model": "some/video-model"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["job_id"]
    assert body["state"] == "queued"


def test_generate_voice_enqueues_a_job(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Ses API Testi"}).json()

    response = api_client.post(
        f"/api/v1/projects/{project['id']}/shots/some-shot-id/generate-voice",
        json={"voice_id": "voice-1"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["job_id"]
    assert body["state"] == "queued"


def test_generate_scene_is_idempotent_per_key(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Sahne Idempotency Testi"}).json()
    payload = {"video_model": "some/video-model"}

    first = api_client.post(
        f"/api/v1/projects/{project['id']}/shots/some-shot-id/generate-scene",
        json=payload,
        headers={"Idempotency-Key": "same-key-scene-1"},
    )
    second = api_client.post(
        f"/api/v1/projects/{project['id']}/shots/some-shot-id/generate-scene",
        json=payload,
        headers={"Idempotency-Key": "same-key-scene-1"},
    )
    assert first.json()["job_id"] == second.json()["job_id"]
