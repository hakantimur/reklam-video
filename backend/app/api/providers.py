"""Provider catalog HTTP routes (spec IMPLEMENTATION_SPEC_TR.md §8.1).

Exports a standalone `router` (GET /providers/models, POST
/providers/models/refresh). Intentionally NOT wired into `app.main` --
mounting it under `/api/v1` is the coordinator's job, per this task's
boundary (do not touch app/main.py).

Both routes currently run the catalog fetch/refresh synchronously in the
request handler rather than through the job queue; the spec's API table
describes the refresh as "katalog yenileme isi" (a job), so if the
coordinator wants job/event-log integration, wrap `CatalogService.refresh()`
in a job of kind e.g. "catalog_refresh" at the mounting layer.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.services.catalog import CatalogResult, CatalogService

router = APIRouter(prefix="/providers", tags=["providers"])


def _serialize(result: CatalogResult) -> dict:
    return {
        "provider": result.catalog.provider,
        "models": [m.model_dump() for m in result.catalog.models],
        "fetched_at": result.catalog.fetched_at,
        "cache_age_seconds": result.cache_age_seconds,
        "stale": result.is_stale,
    }


@router.get("/models")
def get_models() -> dict:
    """Spec §9.1: cache-first with visible age/staleness, never a silent 24h cache."""
    return _serialize(CatalogService().get_catalog())


@router.post("/models/refresh")
def refresh_models() -> dict:
    """Spec §3.2: manual catalog refresh, bypassing the TTL."""
    return _serialize(CatalogService().refresh())
