import hashlib
from pathlib import Path


def _create_project(api_client, name="Asset Testi"):
    return api_client.post("/api/v1/projects", json={"name": name}).json()


def test_upload_asset_computes_sha256_and_leaves_no_partial_file(api_client):
    project = _create_project(api_client)
    content = b"hello world" * 1000
    expected_sha = hashlib.sha256(content).hexdigest()

    response = api_client.post(
        f"/api/v1/projects/{project['id']}/assets",
        files={"file": ("clip.mp4", content, "video/mp4")},
        data={"type": "video", "origin": "user_upload"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["sha256"] == expected_sha
    assert body["byte_size"] == len(content)

    final_path = Path(project["root_path"]) / body["relative_path"]
    assert final_path.exists()
    assert final_path.read_bytes() == content
    assert not final_path.with_name(final_path.name + ".partial").exists()


def test_upload_rejects_path_traversal_filename(api_client):
    project = _create_project(api_client)
    response = api_client.post(
        f"/api/v1/projects/{project['id']}/assets",
        files={"file": ("../../evil.txt", b"payload", "text/plain")},
        data={"type": "video", "origin": "user_upload"},
    )
    assert response.status_code == 201
    body = response.json()
    final_path = Path(project["root_path"]) / body["relative_path"]
    # Must land inside the project's own asset subdirectory, never escape it.
    assert final_path.is_relative_to(Path(project["root_path"]))
    assert ".." not in body["relative_path"]


def test_upload_unicode_filename_with_spaces(api_client):
    project = _create_project(api_client)
    content = b"unicode test"
    response = api_client.post(
        f"/api/v1/projects/{project['id']}/assets",
        files={"file": ("oyun ekran görüntüsü çğşü.png", content, "image/png")},
        data={"type": "image", "origin": "user_upload"},
    )
    assert response.status_code == 201
    body = response.json()
    final_path = Path(project["root_path"]) / body["relative_path"]
    assert final_path.exists()
    assert final_path.read_bytes() == content


def test_upload_empty_file_is_rejected(api_client):
    project = _create_project(api_client)
    response = api_client.post(
        f"/api/v1/projects/{project['id']}/assets",
        files={"file": ("empty.bin", b"", "application/octet-stream")},
        data={"type": "video", "origin": "user_upload"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_upload_unknown_type_is_rejected(api_client):
    project = _create_project(api_client)
    response = api_client.post(
        f"/api/v1/projects/{project['id']}/assets",
        files={"file": ("x.bin", b"data", "application/octet-stream")},
        data={"type": "not-a-real-type", "origin": "user_upload"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_upload_for_unknown_project_returns_404(api_client):
    response = api_client.post(
        "/api/v1/projects/does-not-exist/assets",
        files={"file": ("x.bin", b"data", "application/octet-stream")},
        data={"type": "video", "origin": "user_upload"},
    )
    assert response.status_code == 404


def test_list_assets_and_get_content_with_range(api_client):
    project = _create_project(api_client)
    content = b"content for range test" * 10
    uploaded = api_client.post(
        f"/api/v1/projects/{project['id']}/assets",
        files={"file": ("clip.mp4", content, "video/mp4")},
        data={"type": "video", "origin": "user_upload"},
    ).json()

    listed = api_client.get(f"/api/v1/projects/{project['id']}/assets")
    assert listed.status_code == 200
    assert any(a["id"] == uploaded["id"] for a in listed.json()["items"])

    filtered = api_client.get(f"/api/v1/projects/{project['id']}/assets", params={"type": "audio"})
    assert filtered.json()["items"] == []

    full = api_client.get(f"/api/v1/assets/{uploaded['id']}/content")
    assert full.status_code == 200
    assert full.content == content

    ranged = api_client.get(f"/api/v1/assets/{uploaded['id']}/content", headers={"Range": "bytes=0-9"})
    assert ranged.status_code == 206
    assert ranged.content == content[:10]


def test_get_content_for_unknown_asset_returns_404(api_client):
    response = api_client.get("/api/v1/assets/does-not-exist/content")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
