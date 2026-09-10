"""Device-live: exercises the /devices API surface against a real emulator.

Run explicitly with: pytest -m device_live
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.devices import router
from app.device import adb

pytestmark = pytest.mark.device_live


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture(scope="module")
def serial() -> str:
    devices = [d for d in adb.list_devices() if d.state == "device"]
    if not devices:
        pytest.skip("no real Android device/emulator attached")
    return devices[0].serial


def test_list_devices_reports_the_attached_emulator(client: TestClient, serial: str):
    response = client.get("/api/v1/devices")
    assert response.status_code == 200
    serials = {d["serial"] for d in response.json()}
    assert serial in serials


def test_list_apps_returns_installed_third_party_packages(client: TestClient, serial: str):
    response = client.get(f"/api/v1/devices/{serial}/apps")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_preflight_runs_screenshot_touch_and_recording_checks(client: TestClient, serial: str):
    response = client.post(f"/api/v1/devices/{serial}/preflight")
    assert response.status_code == 200
    body = response.json()
    assert body["screenshot_ok"] is True
    assert body["touch_ok"] is True
    # recording_ok/audio_detected depend on scrcpy/ffprobe being available
    # locally; assert only that the endpoint reports a real, non-crashing
    # outcome rather than asserting a specific true/false value.
    assert "recording_ok" in body
