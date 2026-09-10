"""Mock contract tests for OpenRouterTextVisionProvider.generate_structured.

`/chat/completions` requires a real API key (spec §2.2), which this machine
does not have -- these tests use httpx.MockTransport as a local fixture
server and are explicitly mock, not live.
"""

import json

import httpx
import pytest

from app.providers.base import ChatMessage, UnsupportedOperationError
from app.providers.openrouter import OpenRouterClient, OpenRouterTextVisionProvider


def _provider(handler, api_key: str | None = "sk-test-key") -> OpenRouterTextVisionProvider:
    client = OpenRouterClient(
        api_key=api_key, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    return OpenRouterTextVisionProvider(client)


def test_generate_structured_without_api_key_is_unsupported():
    provider = _provider(lambda request: httpx.Response(200), api_key=None)
    with pytest.raises(UnsupportedOperationError):
        provider.generate_structured("some/model", [ChatMessage("user", "hi")], {"type": "object"})


def test_generate_structured_sends_json_schema_response_format_and_parses_content():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization")
        body = json.loads(request.content)
        captured["body"] = body
        return httpx.Response(
            200,
            json={
                "id": "gen-1",
                "choices": [
                    {"message": {"role": "assistant", "content": json.dumps({"answer": 42})}}
                ],
            },
        )

    provider = _provider(handler)
    schema = {"title": "math_response", "type": "object", "properties": {"answer": {"type": "number"}}}
    result = provider.generate_structured(
        "anthropic/claude-fable-5.1",
        [ChatMessage("system", "sys"), ChatMessage("user", "2+2?")],
        schema,
    )

    assert result == {"answer": 42}
    assert captured["auth"] == "Bearer sk-test-key"
    assert captured["body"]["response_format"]["type"] == "json_schema"
    assert captured["body"]["response_format"]["json_schema"]["name"] == "math_response"
    assert captured["body"]["response_format"]["json_schema"]["schema"] == schema
    assert captured["body"]["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "2+2?"},
    ]


def test_generate_structured_raises_on_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"code": 401, "message": "Missing Authentication header"}})

    provider = _provider(handler)
    with pytest.raises(RuntimeError, match="401"):
        provider.generate_structured("some/model", [ChatMessage("user", "hi")], {"type": "object"})
