"""Device-live: proves scrcpy recording runs concurrently with device
control (spec 11.5) and produces a decodable, event-annotated clip.

Run explicitly with: pytest -m device_live
Skipped when no device or no scrcpy binary is available.
"""

import json
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from app.core.tool_paths import find_binary
from app.device import adb
from app.device.actions import DeviceController
from app.device.capture import CaptureManager

pytestmark = pytest.mark.device_live


@pytest.fixture(scope="module")
def serial() -> str:
    devices = [d for d in adb.list_devices() if d.state == "device"]
    if not devices:
        pytest.skip("no real Android device/emulator attached")
    if find_binary("scrcpy") is None:
        pytest.skip("scrcpy binary not available")
    return devices[0].serial


def test_recording_survives_concurrent_taps_and_closes_cleanly(serial: str, tmp_path: Path):
    manager = CaptureManager()
    controller = DeviceController(serial)

    handle = manager.start_recording(serial, tmp_path, "capture_live_test")
    assert manager.is_recording(serial)

    for i in range(3):
        time.sleep(2)
        observation = controller.observe()
        controller.tap(observation, 0.5, 0.6)
        manager.mark_event(serial, f"tap_{i}")

    video_path = manager.stop_recording(serial)
    assert not manager.is_recording(serial)
    assert video_path.exists()
    assert video_path.stat().st_size > 0

    events = handle.events_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(events) == 3
    for line in events:
        entry = json.loads(line)
        assert "monotonic_ns" in entry

    ffprobe = find_binary("ffprobe")
    if ffprobe is None:
        pytest.skip("ffprobe not available to validate container")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video_path)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    duration_s = float(result.stdout.strip())
    assert duration_s >= 5.0
