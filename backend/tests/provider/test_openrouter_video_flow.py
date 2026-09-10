"""Mock contract tests for the OpenRouter async video submit->poll->download
flow (spec §9.3/§9.4). Requires a real API key on the live API, which this
machine does not have (spec §2.2) -- fully mocked via httpx.MockTransport,
routed by real documented paths/shapes from openrouter.ai/openapi.json
(fetched live 2026-09-11): POST /videos, GET /videos/{jobId},
GET /videos/{jobId}/content.
"""

from pathlib import Path

import httpx
import pytest

from app.providers.base import (
    SubmissionUnknownError,
    UnsupportedOperationError,
    VideoGenerationRequest,
)
from app.providers.network import MediaValidationError
from app.providers.openrouter import OpenRouterClient, OpenRouterVideoProvider

_VIDEO_MODELS = {
    "data": [
        {
            "id": "google/veo-3.1",
            "supported_durations": [4, 6, 8],
            "supported_aspect_ratios": ["16:9", "9:16"],
            "supported_resolutions": ["720p", "1080p"],
            "supported_frame_images": None,
            "generate_audio": True,
            "pricing_skus": {"cents_per_second_output": "10"},
        }
    ]
}

_VALID_MP4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2avc1mp41" + b"\x00" * 2000


def _router(routes: dict[str, httpx.Response]):
    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.method} {request.url.path}"
        if key in routes:
            return routes[key]
        raise AssertionError(f"unexpected request: {key}")

    return handler


def _provider(handler, api_key: str | None = "sk-test") -> OpenRouterVideoProvider:
    client = OpenRouterClient(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return OpenRouterVideoProvider(client)


def test_validate_request_rejects_unsupported_duration():
    handler = _router({"GET /api/v1/videos/models": httpx.Response(200, json=_VIDEO_MODELS)})
    provider = _provider(handler)
    request = VideoGenerationRequest(
        model_id="google/veo-3.1", prompt="p", duration_s=5, ratio="16:9"
    )
    result = provider.validate_request(request)
    assert result.ok is False
    assert any("duration" in e for e in result.errors)


def test_validate_request_ok_for_supported_params():
    handler = _router({"GET /api/v1/videos/models": httpx.Response(200, json=_VIDEO_MODELS)})
    provider = _provider(handler)
    request = VideoGenerationRequest(model_id="google/veo-3.1", prompt="p", duration_s=8, ratio="16:9")
    result = provider.validate_request(request)
    assert result.ok is True
    assert result.errors == []


def test_estimate_cost_uses_pricing_skus():
    handler = _router({"GET /api/v1/videos/models": httpx.Response(200, json=_VIDEO_MODELS)})
    provider = _provider(handler)
    request = VideoGenerationRequest(model_id="google/veo-3.1", prompt="p", duration_s=8, ratio="16:9")
    estimate = provider.estimate_cost(request)
    assert estimate.confidence == "estimated"
    assert estimate.amount_microusd == 10 * 8 * 10_000


def test_estimate_cost_unknown_when_pricing_missing():
    models = {"data": [{**_VIDEO_MODELS["data"][0], "pricing_skus": {}}]}
    handler = _router({"GET /api/v1/videos/models": httpx.Response(200, json=models)})
    provider = _provider(handler)
    request = VideoGenerationRequest(model_id="google/veo-3.1", prompt="p", duration_s=8, ratio="16:9")
    estimate = provider.estimate_cost(request)
    assert estimate.confidence == "unknown"
    assert estimate.amount_microusd is None


def test_submit_without_api_key_is_unsupported():
    provider = _provider(_router({}), api_key=None)
    request = VideoGenerationRequest(model_id="google/veo-3.1", prompt="p", duration_s=8, ratio="16:9")
    with pytest.raises(UnsupportedOperationError):
        provider.submit(request, idempotency_key="k1")


def test_submit_returns_remote_job_id_on_202():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/videos"
        return httpx.Response(
            202,
            json={"id": "job-abc123", "polling_url": "/api/v1/videos/job-abc123", "status": "pending"},
        )

    provider = _provider(handler)
    request = VideoGenerationRequest(model_id="google/veo-3.1", prompt="p", duration_s=8, ratio="16:9")
    remote_id = provider.submit(request, idempotency_key="k1")
    assert remote_id == "job-abc123"


def test_submit_5xx_raises_submission_unknown_not_a_retry():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"code": 500, "message": "boom"}})

    provider = _provider(handler)
    request = VideoGenerationRequest(model_id="google/veo-3.1", prompt="p", duration_s=8, ratio="16:9")
    with pytest.raises(SubmissionUnknownError):
        provider.submit(request, idempotency_key="k1")


def test_submit_transport_error_raises_submission_unknown():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    provider = _provider(handler)
    request = VideoGenerationRequest(model_id="google/veo-3.1", prompt="p", duration_s=8, ratio="16:9")
    with pytest.raises(SubmissionUnknownError):
        provider.submit(request, idempotency_key="k1")


def test_poll_maps_status_to_job_state():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/videos/job-abc123"
        return httpx.Response(
            200,
            json={
                "id": "job-abc123",
                "polling_url": "/api/v1/videos/job-abc123",
                "status": "completed",
                "unsigned_urls": ["https://storage.example.com/video.mp4"],
                "usage": {"cost": 0.5},
            },
        )

    provider = _provider(handler)
    result = provider.poll("job-abc123")
    assert result.state == "completed"
    assert result.download_url == "https://storage.example.com/video.mp4"


def test_download_validates_and_saves_content(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/videos/job-abc123/content"
        return httpx.Response(200, content=_VALID_MP4, headers={"Content-Type": "video/mp4"})

    provider = _provider(handler)
    destination = tmp_path / "clip.mp4"
    result = provider.download("job-abc123", destination)
    assert result == destination
    assert destination.read_bytes() == _VALID_MP4


def test_download_rejects_html_error_page(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>error</html>" + b" " * 2000, headers={"Content-Type": "text/html"})

    provider = _provider(handler)
    destination = tmp_path / "clip.mp4"
    with pytest.raises(MediaValidationError):
        provider.download("job-abc123", destination)
    assert not destination.exists()


def test_cancel_is_unsupported():
    provider = _provider(_router({}))
    with pytest.raises(UnsupportedOperationError):
        provider.cancel("job-abc123")
