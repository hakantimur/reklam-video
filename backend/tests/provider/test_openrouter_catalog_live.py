"""Real, live calls against OpenRouter's public catalog endpoints.

`/models` and `/videos/models` are documented as requiring no API key, and
this machine was confirmed (2026-09-11) to get real HTTP 200 responses from
both without any credentials. These tests are NOT mocked and are NOT gated
behind the `provider_live` marker (that marker is reserved for tests that
need a real, user-authorized API key per spec §2.2) -- they exercise an
actually-reachable anonymous endpoint.

If the network is genuinely unavailable in a given environment, the test
skips rather than failing the whole suite, but on this development machine
it has been confirmed to pass with real data.
"""

import httpx
import pytest

from app.providers.openrouter import OpenRouterTextVisionProvider, OpenRouterVideoProvider


def _skip_if_unreachable(exc: Exception) -> None:
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout)):
        pytest.skip(f"OpenRouter unreachable from this environment: {exc}")
    raise exc


def test_list_models_returns_real_live_catalog():
    provider = OpenRouterTextVisionProvider()
    try:
        models = provider.list_models()
    except httpx.HTTPError as exc:
        _skip_if_unreachable(exc)
        return

    assert len(models) > 50, "expected OpenRouter's real catalog to list many models"
    ids = {m.id for m in models}
    # Sanity: real catalog ids look like "vendor/model-name", not fixtures.
    assert any("/" in model_id for model_id in ids)
    # Every entry must start unverified -- catalog richness never implies
    # our own compatibility verification (spec §9.1).
    assert all(m.capability_status == "unverified" for m in models)
    print(f"[LIVE] OpenRouter /models returned {len(models)} models; sample id={next(iter(ids))!r}")


def test_list_video_models_returns_real_live_catalog():
    provider = OpenRouterVideoProvider()
    try:
        models = provider.list_models()
    except httpx.HTTPError as exc:
        _skip_if_unreachable(exc)
        return

    assert len(models) > 0, "expected OpenRouter's real video catalog to list at least one model"
    assert all(m.roles == ["video"] for m in models)
    assert all(m.capability_status == "unverified" for m in models)
    sample = models[0]
    print(f"[LIVE] OpenRouter /videos/models returned {len(models)} models; sample id={sample.id!r}")
