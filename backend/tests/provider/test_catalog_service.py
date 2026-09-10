"""Unit tests for CatalogService's 24h TTL file cache (spec §9.1, §7.3, §3.2).

Uses fake in-memory providers instead of real OpenRouter calls -- these are
mock/contract tests for the caching behavior, not live network tests.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.schemas.provider import ProviderModel
from app.services.catalog import CACHE_FILENAME, CatalogService, cache_path


class _StubProvider:
    def __init__(self, models: list[ProviderModel]) -> None:
        self._models = models
        self.calls = 0

    def list_models(self) -> list[ProviderModel]:
        self.calls += 1
        return self._models


class _FailingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def list_models(self):
        self.calls += 1
        raise RuntimeError("network unreachable")


def _model(model_id: str) -> ProviderModel:
    return ProviderModel(id=model_id, capability_status="unverified")


def test_get_catalog_fetches_live_and_writes_cache_when_no_cache_exists(tmp_path: Path):
    text_provider = _StubProvider([_model("a/model")])
    video_provider = _StubProvider([_model("b/video-model")])
    service = CatalogService(
        text_provider=text_provider, video_provider=video_provider, projects_root=str(tmp_path)
    )

    result = service.get_catalog()

    assert result.is_stale is False
    assert {m.id for m in result.catalog.models} == {"a/model", "b/video-model"}
    assert text_provider.calls == 1
    assert video_provider.calls == 1
    assert cache_path(str(tmp_path)).exists()


def test_get_catalog_uses_fresh_cache_without_refetching(tmp_path: Path):
    text_provider = _StubProvider([_model("a/model")])
    video_provider = _StubProvider([_model("b/video-model")])
    service = CatalogService(
        text_provider=text_provider, video_provider=video_provider, projects_root=str(tmp_path)
    )
    service.get_catalog()
    assert text_provider.calls == 1

    result = service.get_catalog()

    assert result.is_stale is False
    assert text_provider.calls == 1, "must not re-fetch while cache is within TTL"
    assert video_provider.calls == 1


def test_get_catalog_refetches_when_cache_older_than_ttl(tmp_path: Path):
    text_provider = _StubProvider([_model("a/model")])
    video_provider = _StubProvider([_model("b/video-model")])
    service = CatalogService(
        text_provider=text_provider,
        video_provider=video_provider,
        projects_root=str(tmp_path),
        ttl_hours=24,
    )
    service.get_catalog()

    # Rewrite the cache file with a fetched_at far in the past.
    path = cache_path(str(tmp_path))
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["fetched_at"] = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    path.write_text(json.dumps(raw), encoding="utf-8")

    result = service.get_catalog()

    assert result.is_stale is False
    assert text_provider.calls == 2, "must re-fetch once the cache exceeds the TTL"


def test_refresh_always_refetches_even_within_ttl(tmp_path: Path):
    text_provider = _StubProvider([_model("a/model")])
    video_provider = _StubProvider([_model("b/video-model")])
    service = CatalogService(
        text_provider=text_provider, video_provider=video_provider, projects_root=str(tmp_path)
    )
    service.get_catalog()
    assert text_provider.calls == 1

    service.refresh()

    assert text_provider.calls == 2, "manual refresh must bypass the TTL"


def test_live_failure_falls_back_to_stale_cache_when_available(tmp_path: Path):
    good_text = _StubProvider([_model("a/model")])
    good_video = _StubProvider([_model("b/video-model")])
    warm_service = CatalogService(
        text_provider=good_text, video_provider=good_video, projects_root=str(tmp_path)
    )
    warm_service.get_catalog()

    failing_service = CatalogService(
        text_provider=_FailingProvider(), video_provider=good_video, projects_root=str(tmp_path)
    )
    result = failing_service.refresh()

    assert result.is_stale is True
    assert {m.id for m in result.catalog.models} == {"a/model", "b/video-model"}
    assert result.cache_age_seconds is not None


def test_live_failure_with_no_cache_raises(tmp_path: Path):
    service = CatalogService(
        text_provider=_FailingProvider(), video_provider=_StubProvider([]), projects_root=str(tmp_path)
    )
    with pytest.raises(RuntimeError):
        service.get_catalog()


def test_cache_file_lives_under_projects_root_cache_dir(tmp_path: Path):
    path = cache_path(str(tmp_path))
    assert path.name == CACHE_FILENAME
    assert path.parent.name == "cache"
    assert path.parent.parent == tmp_path
