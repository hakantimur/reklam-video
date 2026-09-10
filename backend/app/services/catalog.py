"""OpenRouter catalog cache service (spec IMPLEMENTATION_SPEC_TR.md §9.1, §7.3, §3.2).

Caches the combined text/vision + video model catalog as one JSON file at
`<projects_root>/cache/catalog_openrouter.json`, honoring
`settings.catalog_cache_hours` (default 24h per spec §3.2). Manual refresh
(`refresh()` / `force_refresh=True`) always re-fetches live regardless of
cache age. If a live fetch fails, a stale cache is served (flagged
`stale=True`) rather than hard-failing -- spec §9.1: "Listeyi API'den
çekemediğinde önbellek sunulabilir; '24 saattir doğrulanmadı' gibi durum
görünür." No Alembic migration is used for this cache; it is a plain file
under the project root's `cache/` directory (spec §7.3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import settings
from app.providers.openrouter import OpenRouterTextVisionProvider, OpenRouterVideoProvider
from app.schemas.provider import ProviderCatalog, ProviderModel

CACHE_FILENAME = "catalog_openrouter.json"


def cache_path(projects_root: str | None = None) -> Path:
    root = Path(projects_root or settings.projects_root)
    cache_dir = root / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / CACHE_FILENAME


@dataclass
class CatalogResult:
    catalog: ProviderCatalog
    cache_age_seconds: float | None
    is_stale: bool


class CatalogService:
    def __init__(
        self,
        *,
        text_provider: OpenRouterTextVisionProvider | None = None,
        video_provider: OpenRouterVideoProvider | None = None,
        projects_root: str | None = None,
        ttl_hours: float | None = None,
    ) -> None:
        self._text_provider = text_provider or OpenRouterTextVisionProvider()
        self._video_provider = video_provider or OpenRouterVideoProvider()
        self._projects_root = projects_root
        self._ttl_hours = ttl_hours if ttl_hours is not None else settings.catalog_cache_hours

    def _path(self) -> Path:
        return cache_path(self._projects_root)

    @staticmethod
    def _age_of(catalog: ProviderCatalog) -> timedelta:
        fetched_at = datetime.fromisoformat(catalog.fetched_at)
        return datetime.now(timezone.utc) - fetched_at

    def _read_cache(self) -> ProviderCatalog | None:
        path = self._path()
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return ProviderCatalog.model_validate(raw)
        except (ValueError, TypeError):
            return None

    def _write_cache(self, catalog: ProviderCatalog) -> None:
        path = self._path()
        # Spec §7.4: write to .partial then atomic rename; never leave a
        # half-written cache file in place of a good one.
        partial = path.with_suffix(path.suffix + ".partial")
        partial.write_text(catalog.model_dump_json(indent=2), encoding="utf-8")
        partial.replace(path)

    def _fetch_live(self) -> ProviderCatalog:
        models: list[ProviderModel] = []
        models.extend(self._text_provider.list_models())
        models.extend(self._video_provider.list_models())
        return ProviderCatalog(provider="openrouter", models=models, source="live", stale=False)

    def get_catalog(self, *, force_refresh: bool = False) -> CatalogResult:
        existing = self._read_cache()

        if not force_refresh and existing is not None:
            age = self._age_of(existing)
            if age <= timedelta(hours=self._ttl_hours):
                return CatalogResult(catalog=existing, cache_age_seconds=age.total_seconds(), is_stale=False)

        try:
            fresh = self._fetch_live()
        except Exception:
            if existing is not None:
                age = self._age_of(existing)
                stale = existing.model_copy(update={"stale": True})
                return CatalogResult(catalog=stale, cache_age_seconds=age.total_seconds(), is_stale=True)
            raise

        self._write_cache(fresh)
        return CatalogResult(catalog=fresh, cache_age_seconds=0.0, is_stale=False)

    def refresh(self) -> CatalogResult:
        return self.get_catalog(force_refresh=True)
