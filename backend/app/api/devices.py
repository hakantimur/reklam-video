import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.core.tool_paths import find_binary
from app.device import adb
from app.device.actions import DeviceController
from app.device.capture import CaptureError, CaptureManager
from app.schemas.device import DeviceSummary, PreflightResult

router = APIRouter(prefix="/devices", tags=["devices"])

_capture_manager = CaptureManager()


def _error(code: str, message: str, status_code: int = 400, retryable: bool = False):
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
                "details": {},
                "job_id": None,
            }
        },
    )


@router.get("", response_model=list[DeviceSummary])
def list_devices() -> list[DeviceSummary]:
    try:
        devices = adb.list_devices()
    except adb.AdbError as exc:
        raise _error("adb_unavailable", str(exc), status_code=503, retryable=True) from exc

    summaries: list[DeviceSummary] = []
    for device in devices:
        width = height = orientation = None
        if device.state == "device":
            try:
                width, height = adb.screen_size(device.serial)
                orientation = adb.orientation(device.serial)
            except adb.AdbError:
                pass  # device just came online / going offline; report what we have
        summaries.append(
            DeviceSummary(
                serial=device.serial,
                state=device.state,
                model=device.model,
                width=width,
                height=height,
                orientation=orientation,
            )
        )
    return summaries


@router.get("/{serial}/apps", response_model=list[str])
def list_apps(serial: str) -> list[str]:
    try:
        return adb.list_third_party_packages(serial)
    except adb.AdbError as exc:
        raise _error("device_unreachable", str(exc), status_code=503, retryable=True) from exc


@router.post("/{serial}/preflight", response_model=PreflightResult)
def preflight(serial: str) -> PreflightResult:
    """Spec 11.1: screenshot, touch and short recording/audio checks before
    a device is offered for shot capture."""
    errors: list[str] = []
    screenshot_ok = touch_ok = recording_ok = False
    audio_detected: bool | None = None

    try:
        controller = DeviceController(serial)
        observation = controller.observe()
        screenshot_ok = observation.png_bytes.startswith(b"\x89PNG")
    except Exception as exc:  # noqa: BLE001 - report as a failed check, not a 500
        errors.append(f"screenshot_failed: {exc}")

    if screenshot_ok:
        try:
            controller.tap(observation, 0.5, 0.5)
            touch_ok = True
        except Exception as exc:  # noqa: BLE001
            errors.append(f"touch_failed: {exc}")

    if find_binary("scrcpy") is None:
        errors.append("scrcpy_not_found")
    else:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                _capture_manager.start_recording(serial, tmp_path, "preflight")
                time.sleep(5)
                video_path = _capture_manager.stop_recording(serial)
                recording_ok = video_path.exists() and video_path.stat().st_size > 0
                audio_detected = _probe_has_audio(video_path)
        except CaptureError as exc:
            errors.append(f"recording_failed: {exc}")

    return PreflightResult(
        serial=serial,
        screenshot_ok=screenshot_ok,
        touch_ok=touch_ok,
        recording_ok=recording_ok,
        audio_detected=audio_detected,
        errors=errors,
    )


def _probe_has_audio(video_path: Path) -> bool | None:
    import subprocess

    ffprobe = find_binary("ffprobe")
    if ffprobe is None:
        return None
    result = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(video_path)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return bool(result.stdout.strip())
