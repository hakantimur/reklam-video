import json

import httpx
import pytest

from app.agents.director import DirectorGenerationError, generate_concepts, generate_shot_plan
from app.models.creative import Concept
from app.models.project import BrandProfile, Brief
from app.providers.openrouter import OpenRouterClient, OpenRouterTextVisionProvider


def _brief() -> Brief:
    return Brief(
        id="brief-1",
        project_id="proj-1",
        revision=1,
        audience="18-34 mobil oyuncular",
        single_message="Sirayi hatirla, tekrar et",
        objective="install",
        style_id="natural_gameplay",
        language="tr",
        target_frames=600,
        fps_num=30,
        fps_den=1,
        placement_id="facebook_reels_9x16",
        budget_microusd=5_000_000,
    )


def _brand() -> BrandProfile:
    return BrandProfile(
        id="brand-1",
        project_id="proj-1",
        product_name="Synova",
        description="Hafiza oyunu",
        cta="Simdi indir",
        verified_claims_json=["Ucretsiz indirilebilir"],
        forbidden_claims_json=[],
        colors_json={},
    )


def _provider_with_response(payload: dict) -> OpenRouterTextVisionProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "gen-1",
                "choices": [{"message": {"content": json.dumps(payload)}}],
            },
        )

    client = OpenRouterClient(
        api_key="sk-test", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    return OpenRouterTextVisionProvider(client)


_VALID_PAYLOAD = {
    "concepts": [
        {"angle": "Meydan okuma", "hook": "Hatirlayabilir misin?", "rationale": "r1", "claim_refs": []},
        {"angle": "Kisa mola", "hook": "5 dakikan var mi?", "rationale": "r2", "claim_refs": []},
        {"angle": "Gercek oynanis", "hook": "Iste boyle oynanir", "rationale": "r3", "claim_refs": []},
    ]
}


def test_generate_concepts_returns_three_validated_candidates():
    provider = _provider_with_response(_VALID_PAYLOAD)
    result = generate_concepts(provider, "test/model", brief=_brief(), brand=_brand())
    assert len(result) == 3
    assert {c.angle for c in result} == {"Meydan okuma", "Kisa mola", "Gercek oynanis"}


def test_generate_concepts_rejects_duplicate_angles():
    payload = json.loads(json.dumps(_VALID_PAYLOAD))
    payload["concepts"][1]["angle"] = "meydan okuma"  # same as concepts[0], case-insensitive
    provider = _provider_with_response(payload)
    with pytest.raises(DirectorGenerationError):
        generate_concepts(provider, "test/model", brief=_brief(), brand=_brand())


def test_generate_concepts_rejects_malformed_schema():
    provider = _provider_with_response({"concepts": [{"angle": "only one"}]})
    with pytest.raises(DirectorGenerationError):
        generate_concepts(provider, "test/model", brief=_brief(), brand=_brand())


def test_missing_game_profile_is_marked_unavailable_not_omitted():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_VALID_PAYLOAD)}}]},
        )

    client = OpenRouterClient(
        api_key="sk-test", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    provider = OpenRouterTextVisionProvider(client)
    generate_concepts(provider, "test/model", brief=_brief(), brand=_brand())

    user_message = captured["body"]["messages"][1]["content"]
    assert "UNAVAILABLE" in user_message
    assert "Do not invent specific gameplay" in user_message


def _concept() -> Concept:
    return Concept(
        id="concept-1", brief_id="brief-1", angle="Meydan okuma", hook="h", rationale="r",
        claim_refs_json=[], selected=True,
    )


_VALID_SHOT_PLAN_PAYLOAD = {
    "schema_version": 1,
    "fps": {"num": 30, "den": 1},
    "target_frames": 600,
    "shots": [
        {
            "id": "shot_1",
            "source_type": "gameplay",
            "purpose": "Ana mekanigi goster",
            "target_frames": 600,
            "handles_frames": {"before": 15, "after": 15},
            "start_state": {},
            "desired_event": None,
            "success_predicate": {"required_observations": ["ok"], "evidence_required": True},
            "action_constraints": {"max_attempts": 3, "max_seconds": 30},
            "caption": "Basla",
            "voice_text": None,
            "fallback": "Oyun kesfi gerekli",
            "locks": {"visual": False, "voice": False, "caption": False, "timing": False},
        }
    ],
}


def test_generate_shot_plan_returns_validated_plan():
    provider = _provider_with_response(_VALID_SHOT_PLAN_PAYLOAD)
    plan = generate_shot_plan(provider, "test/model", brief=_brief(), brand=_brand(), concept=_concept())
    assert plan.target_frames == 600
    assert len(plan.shots) == 1
    assert plan.shots[0].fallback == "Oyun kesfi gerekli"


def test_generate_shot_plan_rejects_frame_mismatch():
    bad_payload = json.loads(json.dumps(_VALID_SHOT_PLAN_PAYLOAD))
    bad_payload["shots"][0]["target_frames"] = 100  # far off from target_frames=600
    provider = _provider_with_response(bad_payload)
    with pytest.raises(DirectorGenerationError):
        generate_shot_plan(provider, "test/model", brief=_brief(), brand=_brand(), concept=_concept())
