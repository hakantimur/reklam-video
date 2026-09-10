"""Mock contract tests for ElevenLabsProvider. No ElevenLabs key on this
machine (spec §2.2) -- fully mocked via httpx.MockTransport, not live."""

import httpx
import pytest

from app.providers.base import UnsupportedOperationError
from app.providers.elevenlabs import ElevenLabsProvider


def _provider(handler, api_key: str | None = "el-test-key") -> ElevenLabsProvider:
    return ElevenLabsProvider(
        base_url="https://api.elevenlabs.io/v1",
        api_key=api_key,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_list_voices_without_api_key_is_unsupported():
    provider = _provider(lambda request: httpx.Response(200), api_key=None)
    with pytest.raises(UnsupportedOperationError):
        provider.list_voices()


def test_list_voices_sends_xi_api_key_header_and_parses_voices():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["xi_key"] = request.headers.get("xi-api-key")
        return httpx.Response(
            200,
            json={"voices": [{"voice_id": "abc123", "name": "Rachel", "category": "premade"}]},
        )

    provider = _provider(handler)
    voices = provider.list_voices()

    assert captured["path"] == "/v1/voices"
    assert captured["xi_key"] == "el-test-key"
    assert voices == [{"voice_id": "abc123", "name": "Rachel", "category": "premade"}]


def test_synthesize_without_api_key_is_unsupported():
    provider = _provider(lambda request: httpx.Response(200), api_key=None)
    with pytest.raises(UnsupportedOperationError):
        provider.synthesize("hello", "abc123", "tr")


def test_synthesize_posts_text_and_returns_audio_bytes():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["xi_key"] = request.headers.get("xi-api-key")
        import json as _json

        captured["body"] = _json.loads(request.content)
        return httpx.Response(200, content=b"FAKE_MP3_BYTES", headers={"Content-Type": "audio/mpeg"})

    provider = _provider(handler)
    audio = provider.synthesize("Merhaba dunya", "abc123", "tr", style="energetic")

    assert captured["path"] == "/v1/text-to-speech/abc123"
    assert captured["xi_key"] == "el-test-key"
    assert captured["body"]["text"] == "Merhaba dunya"
    assert captured["body"]["language_code"] == "tr"
    assert captured["body"]["voice_settings"] == {"style": "energetic"}
    assert audio == b"FAKE_MP3_BYTES"


def test_synthesize_raises_on_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "invalid voice_id"})

    provider = _provider(handler)
    with pytest.raises(RuntimeError, match="422"):
        provider.synthesize("hi", "bad-voice", "en")
