"""Device-live tests: require a real connected Android device/emulator.

Run explicitly with: pytest -m device_live
Skipped automatically when no device is attached (CI / no-hardware runs).
"""

import pytest

from app.device import adb
from app.device.actions import DeviceController, StaleObservationError

pytestmark = pytest.mark.device_live


def _first_device_serial() -> str | None:
    try:
        devices = [d for d in adb.list_devices() if d.state == "device"]
    except adb.AdbError:
        return None
    return devices[0].serial if devices else None


@pytest.fixture(scope="module")
def serial() -> str:
    found = _first_device_serial()
    if not found:
        pytest.skip("no real Android device/emulator attached")
    return found


def test_screen_size_and_orientation_are_readable(serial: str):
    width, height = adb.screen_size(serial)
    assert width > 0 and height > 0
    assert adb.orientation(serial) in (0, 1, 2, 3)


def test_screenshot_returns_valid_png(serial: str):
    png = adb.screenshot_png(serial)
    assert png.startswith(b"\x89PNG")
    assert len(png) > 1000


def test_normalized_tap_succeeds_on_current_observation(serial: str):
    controller = DeviceController(serial)
    observation = controller.observe()
    controller.tap(observation, 0.5, 0.9)  # near-bottom, unlikely to leave the app


def test_stale_observation_is_rejected(serial: str):
    controller = DeviceController(serial)
    stale = controller.observe()
    controller.observe()  # produces a newer observation, invalidating `stale`
    with pytest.raises(StaleObservationError):
        controller.tap(stale, 0.5, 0.5)


def test_out_of_range_coordinates_are_rejected(serial: str):
    controller = DeviceController(serial)
    observation = controller.observe()
    with pytest.raises(ValueError):
        controller.tap(observation, 1.5, 0.5)
