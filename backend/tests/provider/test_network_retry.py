"""Mock-transport contract tests for GET retry/backoff (spec §9.4).

Uses httpx.MockTransport (built into httpx, no extra dependency) instead of
a real network call -- these are explicitly mock/contract tests, not live.
"""

from pathlib import Path

import httpx
import pytest

from app.providers.network import download_with_retry, get_with_retry


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_retries_on_429_then_succeeds():
    calls = {"n": 0}
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0.01"})
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    response = get_with_retry(client, "https://example.test/models", sleep=sleeps.append)

    assert response.status_code == 200
    assert calls["n"] == 2
    assert sleeps == [0.01], "must honor the Retry-After header exactly, not random backoff"


def test_retries_on_5xx_with_exponential_jittered_backoff():
    calls = {"n": 0}
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    response = get_with_retry(
        client, "https://example.test/models", base_delay_s=0.01, max_delay_s=1.0, sleep=sleeps.append
    )

    assert response.status_code == 200
    assert calls["n"] == 3
    assert len(sleeps) == 2
    assert all(delay >= 0 for delay in sleeps)


def test_gives_up_after_max_retries_without_raising():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503)

    client = _client(handler)
    response = get_with_retry(
        client, "https://example.test/models", max_retries=2, base_delay_s=0.001, sleep=lambda _: None
    )

    assert response.status_code == 503
    assert calls["n"] == 3  # first attempt + 2 retries


def test_transport_error_retries_then_raises():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("boom", request=request)

    client = _client(handler)
    with pytest.raises(httpx.ConnectError):
        get_with_retry(
            client, "https://example.test/models", max_retries=2, base_delay_s=0.001, sleep=lambda _: None
        )

    assert calls["n"] == 3


def test_non_retryable_status_returns_immediately():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404)

    client = _client(handler)
    response = get_with_retry(client, "https://example.test/models", sleep=lambda _: None)

    assert response.status_code == 404
    assert calls["n"] == 1


def test_download_with_retry_writes_file_atomically(tmp_path: Path):
    body = b"\x00\x00\x00\x18ftypisommp42binary-video-bytes-padding-to-be-realistic"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"Content-Type": "video/mp4"})

    client = _client(handler)
    destination = tmp_path / "clip.mp4"
    content_type = download_with_retry(client, "https://example.test/videos/x/content", destination)

    assert content_type == "video/mp4"
    assert destination.read_bytes() == body
    assert not destination.with_suffix(destination.suffix + ".partial").exists()


def test_download_with_retry_recovers_from_one_transport_error(tmp_path: Path):
    calls = {"n": 0}
    body = b"\x00\x00\x00\x18ftypisommp42real-bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, content=body, headers={"Content-Type": "video/mp4"})

    client = _client(handler)
    destination = tmp_path / "clip.mp4"
    content_type = download_with_retry(
        client, "https://example.test/videos/x/content", destination, sleep=lambda _: None
    )

    assert content_type == "video/mp4"
    assert destination.read_bytes() == body
    assert calls["n"] == 2
