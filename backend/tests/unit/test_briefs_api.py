def _brief_payload(**overrides):
    payload = {
        "audience": "18-30 mobil oyuncular",
        "single_message": "Bu oyun bagimlilik yapiyor",
        "objective": "install",
        "style_id": "energetic-v1",
        "language": "tr",
        "target_frames": 900,
        "fps_num": 30,
        "fps_den": 1,
        "placement_id": "meta-feed-9x16",
        "budget_microusd": 50_000_000,
    }
    payload.update(overrides)
    return payload


def test_put_brief_creates_first_revision(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Brief Testi"}).json()

    response = api_client.put(f"/api/v1/projects/{project['id']}/brief", json=_brief_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["revision"] == 1
    assert body["project_id"] == project["id"]
    assert body["budget_microusd"] == 50_000_000


def test_put_brief_twice_creates_second_revision_not_overwrite(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Brief Revizyon Testi"}).json()

    first = api_client.put(
        f"/api/v1/projects/{project['id']}/brief", json=_brief_payload(single_message="ilk mesaj")
    ).json()
    second = api_client.put(
        f"/api/v1/projects/{project['id']}/brief", json=_brief_payload(single_message="ikinci mesaj")
    ).json()

    assert first["revision"] == 1
    assert second["revision"] == 2
    assert first["id"] != second["id"]
    assert second["single_message"] == "ikinci mesaj"


def test_put_brief_for_unknown_project_returns_404(api_client):
    response = api_client.put("/api/v1/projects/does-not-exist/brief", json=_brief_payload())
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
