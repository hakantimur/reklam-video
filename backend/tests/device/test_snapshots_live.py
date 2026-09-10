"""Device-live: emulator snapshot save/list/load/delete (spec 11.7).

Only meaningful for an AVD reached via the emulator console bridge; skipped
when unsupported (e.g. a physical device) rather than failing.
"""

import pytest

from app.device import adb

pytestmark = pytest.mark.device_live

SNAPSHOT_NAME = "lad_pytest_checkpoint"


@pytest.fixture(scope="module")
def serial() -> str:
    devices = [d for d in adb.list_devices() if d.state == "device"]
    if not devices:
        pytest.skip("no real Android device/emulator attached")
    return devices[0].serial


def test_snapshot_save_list_load_delete_roundtrip(serial: str):
    try:
        adb.save_snapshot(serial, SNAPSHOT_NAME)
    except adb.AdbError:
        pytest.skip("snapshot save not supported on this device (not an AVD console target)")

    try:
        assert SNAPSHOT_NAME in adb.list_snapshots(serial)
        adb.load_snapshot(serial, SNAPSHOT_NAME)
    finally:
        adb.delete_snapshot(serial, SNAPSHOT_NAME)

    assert SNAPSHOT_NAME not in adb.list_snapshots(serial)
