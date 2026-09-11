def test_list_jobs_returns_newest_first(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Isler Testi"}).json()

    api_client.post(
        f"/api/v1/projects/{project['id']}/discover",
        json={"serial": "emulator-5554", "package_id": "com.example.test"},
        headers={"Idempotency-Key": "job-1"},
    )
    api_client.post(
        f"/api/v1/projects/{project['id']}/discover",
        json={"serial": "emulator-5554", "package_id": "com.example.test"},
        headers={"Idempotency-Key": "job-2"},
    )

    response = api_client.get(f"/api/v1/projects/{project['id']}/jobs")
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 2
    assert jobs[0]["created_at"] >= jobs[1]["created_at"]
    assert all(j["kind"] == "discover" for j in jobs)


def test_list_jobs_filters_by_state(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Isler Filtre Testi"}).json()
    api_client.post(
        f"/api/v1/projects/{project['id']}/discover",
        json={"serial": "emulator-5554", "package_id": "com.example.test"},
    )

    response = api_client.get(f"/api/v1/projects/{project['id']}/jobs", params={"state": "succeeded"})
    assert response.status_code == 200
    assert response.json() == []


def test_list_jobs_scoped_to_project(api_client):
    project_a = api_client.post("/api/v1/projects", json={"name": "Proje A"}).json()
    project_b = api_client.post("/api/v1/projects", json={"name": "Proje B"}).json()
    api_client.post(
        f"/api/v1/projects/{project_a['id']}/discover",
        json={"serial": "emulator-5554", "package_id": "com.example.test"},
    )

    response = api_client.get(f"/api/v1/projects/{project_b['id']}/jobs")
    assert response.status_code == 200
    assert response.json() == []
