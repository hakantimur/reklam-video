"""HTTP contract tests for app.api.providers (spec §8.1).

`router` is intentionally not mounted in app.main (the coordinator will wire
it); these tests build a standalone FastAPI app around it so the endpoints
are still verified in isolation. Uses stub providers via monkeypatching the
default OpenRouterTextVisionProvider/OpenRouterVideoProvider construction
inside CatalogService -- no network call.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.providers import router
from app.schemas.provider import ProviderModel
from app.services import catalog as catalog_module


class _StubProvider:
    def __init__(self, models):
        self._models = models

    def list_models(self):
        return self._models


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(catalog_module.settings, "projects_root", str(tmp_path))
    monkeypatch.setattr(
        catalog_module,
        "OpenRouterTextVisionProvider",
        lambda: _StubProvider([ProviderModel(id="stub/text-model")]),
    )
    monkeypatch.setattr(
        catalog_module,
        "OpenRouterVideoProvider",
        lambda: _StubProvider([ProviderModel(id="stub/video-model", roles=["video"])]),
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def test_get_models_returns_normalized_catalog(client: TestClient):
    response = client.get("/api/v1/providers/models")
    assert response.status_code == 200
    body = response.json()
    ids = {m["id"] for m in body["models"]}
    assert ids == {"stub/text-model", "stub/video-model"}
    assert body["provider"] == "openrouter"
    assert body["stale"] is False
    assert all(m["capability_status"] == "unverified" for m in body["models"])


def test_refresh_endpoint_returns_catalog(client: TestClient):
    response = client.post("/api/v1/providers/models/refresh")
    assert response.status_code == 200
    body = response.json()
    assert {m["id"] for m in body["models"]} == {"stub/text-model", "stub/video-model"}
