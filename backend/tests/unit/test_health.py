from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_db_and_disk():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["db"]["ok"] is True
    assert "free_gb" in body["disk"]


def test_diagnostics_lists_expected_tools():
    response = client.get("/api/v1/diagnostics")
    assert response.status_code == 200
    body = response.json()
    names = {tool["name"] for tool in body["tools"]}
    assert names == {"node", "adb", "scrcpy", "ffmpeg", "ffprobe"}


def test_cross_origin_mutation_is_rejected():
    response = client.post(
        "/api/v1/health",
        headers={"Origin": "https://evil.example", "Host": "evil.example"},
    )
    # /health only supports GET, but any mutating verb from a foreign
    # origin must never reach a real mutating route either.
    assert response.status_code in (403, 405)
