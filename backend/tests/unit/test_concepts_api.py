import json

import httpx
import pytest

_VALID_PAYLOAD = {
    "concepts": [
        {"angle": "Meydan okuma", "hook": "h1", "rationale": "r1", "claim_refs": []},
        {"angle": "Kisa mola", "hook": "h2", "rationale": "r2", "claim_refs": []},
        {"angle": "Gercek oynanis", "hook": "h3", "rationale": "r3", "claim_refs": []},
    ]
}


def _create_project_with_brief(api_client, name="Concept Testi"):
    project = api_client.post("/api/v1/projects", json={"name": name}).json()
    api_client.put(
        f"/api/v1/projects/{project['id']}/brief",
        json={
            "audience": "test",
            "single_message": "test",
            "objective": "install",
            "style_id": "style-1",
            "language": "tr",
            "target_frames": 600,
            "fps_num": 30,
            "fps_den": 1,
            "placement_id": "placement-1",
            "budget_microusd": 5_000_000,
            "product_name": "Synova",
            "description": "Hafiza oyunu",
            "cta": "Simdi indir",
        },
    )
    return project


@pytest.fixture
def mock_openrouter(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_VALID_PAYLOAD)}}]},
        )

    import app.api.concepts as concepts_api

    monkeypatch.setattr(concepts_api.credentials_service, "get_credential_value", lambda p: "sk-test")

    original_client_cls = concepts_api.OpenRouterClient

    def fake_client(*, api_key=None, **kwargs):
        return original_client_cls(
            api_key=api_key, http_client=httpx.Client(transport=httpx.MockTransport(handler))
        )

    monkeypatch.setattr(concepts_api, "OpenRouterClient", fake_client)
    return handler


def test_create_concepts_without_api_key_is_blocked(api_client, monkeypatch):
    import app.api.concepts as concepts_api

    monkeypatch.setattr(concepts_api.credentials_service, "get_credential_value", lambda p: None)
    project = _create_project_with_brief(api_client, "Anahtarsiz Testi")

    response = api_client.post(f"/api/v1/projects/{project['id']}/concepts", json={})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "blocked"


def test_create_concepts_without_brief_returns_422(api_client, mock_openrouter):
    project = api_client.post("/api/v1/projects", json={"name": "Briefsiz Testi"}).json()
    response = api_client.post(f"/api/v1/projects/{project['id']}/concepts", json={})
    assert response.status_code == 422


def test_create_and_list_concepts(api_client, mock_openrouter):
    project = _create_project_with_brief(api_client)

    created = api_client.post(f"/api/v1/projects/{project['id']}/concepts", json={})
    assert created.status_code == 201
    body = created.json()
    assert len(body) == 3
    assert {c["angle"] for c in body} == {"Meydan okuma", "Kisa mola", "Gercek oynanis"}
    assert all(c["selected"] is False for c in body)

    listed = api_client.get(f"/api/v1/projects/{project['id']}/concepts")
    assert listed.status_code == 200
    assert {c["id"] for c in listed.json()} == {c["id"] for c in body}


def test_select_concept_marks_exactly_one_selected(api_client, mock_openrouter):
    project = _create_project_with_brief(api_client)
    concepts = api_client.post(f"/api/v1/projects/{project['id']}/concepts", json={}).json()

    target = concepts[1]["id"]
    response = api_client.post(f"/api/v1/projects/{project['id']}/concepts/{target}/select")
    assert response.status_code == 200
    assert response.json()["selected"] is True

    listed = api_client.get(f"/api/v1/projects/{project['id']}/concepts").json()
    selected_ids = [c["id"] for c in listed if c["selected"]]
    assert selected_ids == [target]
