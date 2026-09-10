def test_create_and_get_project(api_client):
    response = api_client.post("/api/v1/projects", json={"name": "Kahve Reklamı", "locale": "tr-TR"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Kahve Reklamı"
    assert body["slug"]
    assert body["version"] == 1
    assert body["root_path"]

    fetched = api_client.get(f"/api/v1/projects/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_list_projects_contains_created_project(api_client):
    created = api_client.post("/api/v1/projects", json={"name": "Liste Testi"}).json()
    listed = api_client.get("/api/v1/projects")
    assert listed.status_code == 200
    ids = {p["id"] for p in listed.json()["items"]}
    assert created["id"] in ids


def test_get_unknown_project_returns_structured_404(api_client):
    response = api_client.get("/api/v1/projects/does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["retryable"] is False
    assert "job_id" in error


def test_patch_updates_and_bumps_version(api_client):
    created = api_client.post("/api/v1/projects", json={"name": "Guncelleme Testi"}).json()

    patched = api_client.patch(
        f"/api/v1/projects/{created['id']}",
        json={"version": created["version"], "name": "Guncellenmis Isim"},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["name"] == "Guncellenmis Isim"
    assert body["version"] == created["version"] + 1


def test_patch_with_stale_version_returns_409(api_client):
    created = api_client.post("/api/v1/projects", json={"name": "Cakisma Testi"}).json()

    first = api_client.patch(
        f"/api/v1/projects/{created['id']}",
        json={"version": created["version"], "name": "Ilk Guncelleme"},
    )
    assert first.status_code == 200

    # Retrying with the now-stale version the client originally read must 409,
    # never silently apply on top of the newer state (spec 7.1).
    stale = api_client.patch(
        f"/api/v1/projects/{created['id']}",
        json={"version": created["version"], "name": "Ikinci Guncelleme"},
    )
    assert stale.status_code == 409
    error = stale.json()["error"]
    assert error["code"] == "version_conflict"
    assert error["retryable"] is False
