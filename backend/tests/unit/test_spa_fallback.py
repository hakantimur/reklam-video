"""A plain StaticFiles(html=True) mount only serves index.html for '/' —
a bookmark or refresh on a client-side route like /studyo/senaryo 404s
unless there's an explicit SPA fallback (spec 20.2: the built UI is served
by FastAPI). Skipped when apps/web hasn't been built locally.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import _WEB_DIST, app

pytestmark = pytest.mark.skipif(
    not (_WEB_DIST / "index.html").exists(), reason="apps/web/dist not built locally"
)

client = TestClient(app)


def test_root_serves_index_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "<div id=\"root\"" in response.text or "<!doctype html>" in response.text.lower()


def test_client_side_route_falls_back_to_index_html_not_404():
    response = client.get("/studyo/senaryo")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_hashed_asset_is_served_directly_not_as_index_html():
    asset_dir = _WEB_DIST / "assets"
    js_files = list(asset_dir.glob("*.js"))
    assert js_files, "expected a built JS bundle under dist/assets"

    response = client.get(f"/assets/{js_files[0].name}")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_api_routes_are_not_shadowed_by_the_spa_fallback():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
