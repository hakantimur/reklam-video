import json

import httpx
import pytest

_VALID_CONCEPTS_PAYLOAD = {
    "concepts": [
        {"angle": "Meydan okuma", "hook": "h1", "rationale": "r1", "claim_refs": []},
        {"angle": "Kisa mola", "hook": "h2", "rationale": "r2", "claim_refs": []},
        {"angle": "Gercek oynanis", "hook": "h3", "rationale": "r3", "claim_refs": []},
    ]
}


def _valid_shot_plan_payload(target_frames=600):
    return {
        "schema_version": 1,
        "fps": {"num": 30, "den": 1},
        "target_frames": target_frames,
        "shots": [
            {
                "id": "shot_1",
                "source_type": "gameplay",
                "purpose": "Ana mekanigi goster",
                "target_frames": 300,
                "handles_frames": {"before": 15, "after": 15},
                "start_state": {},
                "desired_event": None,
                "success_predicate": {"required_observations": ["ok"], "evidence_required": True},
                "action_constraints": {"max_attempts": 3, "max_seconds": 30},
                "caption": "Basla",
                "voice_text": None,
                "fallback": "Oyun kesfi gerekli",
                "locks": {"visual": False, "voice": False, "caption": False, "timing": False},
            },
            {
                "id": "shot_2",
                "source_type": "composed",
                "purpose": "Logo ve CTA",
                "target_frames": target_frames - 300,
                "handles_frames": {"before": 0, "after": 0},
                "start_state": {},
                "desired_event": None,
                "success_predicate": {"required_observations": [], "evidence_required": False},
                "action_constraints": {"max_attempts": 1, "max_seconds": 10},
                "caption": "Simdi indir",
                "voice_text": None,
                "fallback": None,
                "locks": {"visual": False, "voice": False, "caption": False, "timing": False},
            },
        ],
    }


def _create_project_with_brief_and_concept(api_client, name="Plan Testi"):
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

    import app.api.concepts as concepts_api

    def concepts_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(_VALID_CONCEPTS_PAYLOAD)}}]}
        )

    original_client_cls = concepts_api.OpenRouterClient

    def fake_concepts_client(*, api_key=None, **kwargs):
        return original_client_cls(
            api_key=api_key, http_client=httpx.Client(transport=httpx.MockTransport(concepts_handler))
        )

    real_get_value = concepts_api.credentials_service.get_credential_value
    concepts_api.credentials_service.get_credential_value = lambda p: "sk-test"
    concepts_api.OpenRouterClient = fake_concepts_client
    try:
        concepts = api_client.post(f"/api/v1/projects/{project['id']}/concepts", json={}).json()
    finally:
        concepts_api.OpenRouterClient = original_client_cls
        concepts_api.credentials_service.get_credential_value = real_get_value

    return project, concepts[0]["id"]


@pytest.fixture
def mock_plan_openrouter(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_valid_shot_plan_payload())}}]},
        )

    import app.api.plans as plans_api

    monkeypatch.setattr(plans_api.credentials_service, "get_credential_value", lambda p: "sk-test")

    original_client_cls = plans_api.OpenRouterClient

    def fake_client(*, api_key=None, **kwargs):
        return original_client_cls(
            api_key=api_key, http_client=httpx.Client(transport=httpx.MockTransport(handler))
        )

    monkeypatch.setattr(plans_api, "OpenRouterClient", fake_client)
    return handler


def test_create_plan_without_api_key_is_blocked(api_client, monkeypatch):
    import app.api.plans as plans_api

    monkeypatch.setattr(plans_api.credentials_service, "get_credential_value", lambda p: None)
    project, concept_id = _create_project_with_brief_and_concept(api_client, "Anahtarsiz Plan")

    response = api_client.post(
        f"/api/v1/projects/{project['id']}/plan", json={"concept_id": concept_id}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "blocked"


def test_create_plan_persists_revision_and_shots(api_client, mock_plan_openrouter):
    project, concept_id = _create_project_with_brief_and_concept(api_client)

    response = api_client.post(
        f"/api/v1/projects/{project['id']}/plan", json={"concept_id": concept_id}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["sequence_no"] == 1
    assert len(body["shots"]) == 2
    assert sum(s["target_frames"] for s in body["shots"]) == 600

    fetched = api_client.get(f"/api/v1/projects/{project['id']}/plan")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_create_plan_with_unknown_concept_returns_404(api_client, mock_plan_openrouter):
    project, _ = _create_project_with_brief_and_concept(api_client, "Bilinmeyen Concept")

    response = api_client.post(
        f"/api/v1/projects/{project['id']}/plan", json={"concept_id": "does-not-exist"}
    )
    assert response.status_code == 404
