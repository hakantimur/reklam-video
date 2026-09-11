import json

import httpx
import pytest

from app.agents.operator import OperatorDecisionError, decide_next_action
from app.providers.openrouter import OpenRouterClient, OpenRouterTextVisionProvider

_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)

_VALID_DECISION = {
    "screen_classification": "menu",
    "reasoning": "Main menu visible, tap play button",
    "memory_update": {"screen": "main_menu"},
    "action": {
        "type": "tap",
        "x": 0.5,
        "y": 0.8,
        "x2": None,
        "y2": None,
        "duration_ms": None,
        "note": None,
    },
}


def _provider(handler) -> OpenRouterTextVisionProvider:
    client = OpenRouterClient(
        api_key="sk-test", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    return OpenRouterTextVisionProvider(client)


def test_decide_next_action_sends_image_and_parses_decision():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(_VALID_DECISION)}}]}
        )

    provider = _provider(handler)
    decision = decide_next_action(
        provider,
        "test/model",
        screenshot_png=_TINY_PNG,
        package_id="com.example.synova.dev",
        working_memory={},
        actions_taken=0,
        max_actions=60,
        discovery_goal="Learn the mechanic",
    )

    assert decision.action.type == "tap"
    assert decision.action.x == 0.5

    user_content = captured["body"]["messages"][1]["content"]
    assert isinstance(user_content, list)
    types = {part["type"] for part in user_content}
    assert types == {"text", "image_url"}
    image_part = next(p for p in user_content if p["type"] == "image_url")
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")


def test_decide_next_action_rejects_malformed_decision():
    provider = _provider(
        lambda r: httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})
    )
    with pytest.raises(OperatorDecisionError):
        decide_next_action(
            provider,
            "test/model",
            screenshot_png=_TINY_PNG,
            package_id="com.example.synova.dev",
            working_memory={},
            actions_taken=0,
            max_actions=60,
            discovery_goal="Learn the mechanic",
        )
