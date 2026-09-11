"""Thin wrapper over the `adb` binary. Every call is argv-based with
shell=False (spec 20.1: commands run as argv lists, never through a shell)."""

import re
import shutil
import subprocess
from dataclasses import dataclass


class AdbError(RuntimeError):
    pass


@dataclass
class ConnectedDevice:
    serial: str
    state: str  # device | offline | unauthorized
    model: str | None = None


def _adb_path() -> str:
    path = shutil.which("adb")
    if path is None:
        raise AdbError("adb_not_found")
    return path


def _run(argv: list[str], timeout: float = 15.0) -> str:
    try:
        result = subprocess.run(
            [_adb_path(), *argv], capture_output=True, text=True, timeout=timeout, shell=False
        )
    except subprocess.TimeoutExpired as exc:
        raise AdbError(f"adb_timeout: {' '.join(argv)}") from exc
    if result.returncode != 0:
        raise AdbError(f"adb_failed: {' '.join(argv)}: {result.stderr.strip()}")
    return result.stdout


def list_devices() -> list[ConnectedDevice]:
    output = _run(["devices", "-l"])
    devices: list[ConnectedDevice] = []
    for line in output.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        serial, state = parts[0], parts[1]
        model = None
        for token in parts[2:]:
            if token.startswith("model:"):
                model = token.split(":", 1)[1]
        devices.append(ConnectedDevice(serial=serial, state=state, model=model))
    return devices


def screen_size(serial: str) -> tuple[int, int]:
    output = _run(["-s", serial, "shell", "wm", "size"])
    match = re.search(r"(\d+)x(\d+)", output)
    if not match:
        raise AdbError(f"cannot_parse_screen_size: {output!r}")
    return int(match.group(1)), int(match.group(2))


def orientation(serial: str) -> int:
    """Returns the Surface.ROTATION_* value (0, 1, 2 or 3).

    Filtering happens locally, not via a remote shell pipe: a piped remote
    grep with no match returns a non-zero exit code that adb propagates,
    which _run would otherwise (incorrectly) treat as a command failure.
    """
    output = _run(["-s", serial, "shell", "dumpsys", "input"], timeout=10.0)
    match = re.search(r"SurfaceOrientation:\s*(\d)", output)
    if match:
        return int(match.group(1))
    output = _run(["-s", serial, "shell", "settings", "get", "system", "user_rotation"])
    stripped = output.strip()
    return int(stripped) if stripped.isdigit() else 0


def list_third_party_packages(serial: str) -> list[str]:
    output = _run(["-s", serial, "shell", "pm", "list", "packages", "-3"])
    return sorted(
        line.strip().removeprefix("package:")
        for line in output.splitlines()
        if line.strip().startswith("package:")
    )


def package_version(serial: str, package_id: str) -> str | None:
    output = _run(["-s", serial, "shell", "dumpsys", "package", package_id])
    match = re.search(r"versionName=(\S+)", output)
    return match.group(1) if match else None


def launch_app(serial: str, package_id: str) -> None:
    _run(
        [
            "-s",
            serial,
            "shell",
            "monkey",
            "-p",
            package_id,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ]
    )


def foreground_package(serial: str) -> str | None:
    """Best-effort read of the package currently focused on screen, parsed
    from `dumpsys window`'s `mCurrentFocus` line. Returns None if it can't
    be determined (never raises -- this is a polling helper, not a hard
    requirement)."""
    try:
        output = _run(["-s", serial, "shell", "dumpsys", "window"])
    except AdbError:
        return None
    match = re.search(r"mCurrentFocus=Window\{[^ ]+ [^ ]+ ([^/}]+)", output)
    return match.group(1) if match else None


def wait_for_foreground(serial: str, package_id: str, *, timeout_s: float = 10.0, poll_interval_s: float = 0.5) -> bool:
    """Poll until `package_id` is the focused foreground app or `timeout_s`
    elapses. A cold start of a real, asset-heavy app can take well over the
    flat 2s sleep this used to be paired with -- found live (2026-09-11):
    the discovery/capture vision agent's first observation landed on the
    Android home screen mid-launch and it correctly (but wastefully, at
    real API cost) requested a human takeover instead of proceeding.
    Returns True once the app is confirmed foreground, False on timeout
    (callers should proceed anyway -- this is a best-effort wait, not a
    blocking guarantee, since `foreground_package` parsing can fail for
    reasons unrelated to the app actually being ready)."""
    import time

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if foreground_package(serial) == package_id:
            return True
        time.sleep(poll_interval_s)
    return False


def screenshot_png(serial: str) -> bytes:
    result = subprocess.run(
        [_adb_path(), "-s", serial, "exec-out", "screencap", "-p"],
        capture_output=True,
        timeout=15.0,
        shell=False,
    )
    if result.returncode != 0 or not result.stdout.startswith(b"\x89PNG"):
        raise AdbError("screenshot_failed")
    return result.stdout


def tap(serial: str, x_px: int, y_px: int) -> None:
    _run(["-s", serial, "shell", "input", "tap", str(x_px), str(y_px)])


def swipe(serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
    _run(
        ["-s", serial, "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)]
    )


def press_back(serial: str) -> None:
    _run(["-s", serial, "shell", "input", "keyevent", "KEYCODE_BACK"])


# --- Emulator snapshots (spec 11.7: checkpoints) ---
# Only meaningful for AVDs reached over the emulator console bridge
# (`adb emu`); a physical device has no snapshot concept and these calls
# will fail there, which callers must treat as "unsupported", not an error.


def save_snapshot(serial: str, name: str) -> None:
    output = _run(["-s", serial, "emu", "avd", "snapshot", "save", name], timeout=60.0)
    if "OK" not in output:
        raise AdbError(f"snapshot_save_failed: {output.strip()}")


def load_snapshot(serial: str, name: str) -> None:
    output = _run(["-s", serial, "emu", "avd", "snapshot", "load", name], timeout=60.0)
    if "OK" not in output:
        raise AdbError(f"snapshot_load_failed: {output.strip()}")


def list_snapshots(serial: str) -> list[str]:
    output = _run(["-s", serial, "emu", "avd", "snapshot", "list"], timeout=15.0)
    names = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line in ("OK",) or line.startswith("There is no snapshot"):
            continue
        if line.startswith("List of snapshots") or line.startswith("ID"):
            continue
        # Columns: ID  TAG  VM SIZE  DATE  VM CLOCK — the snapshot name we
        # pass to save/load is the TAG (2nd column), not the numeric ID.
        columns = line.split()
        if len(columns) >= 2:
            names.append(columns[1])
    return names


def delete_snapshot(serial: str, name: str) -> None:
    output = _run(["-s", serial, "emu", "avd", "snapshot", "delete", name], timeout=30.0)
    if "OK" not in output:
        raise AdbError(f"snapshot_delete_failed: {output.strip()}")
