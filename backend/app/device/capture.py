"""scrcpy-based screen recording, running independently of game control.

Spec 11.5: CaptureManager starts scrcpy in its own process group; the async
controller keeps issuing tap/swipe/observe calls while recording runs. This
module must never expose a blocking `record(duration)` call that ties up the
control loop for the whole recording window.

Spec 11.6: host monotonic clock, action timestamps and media PTS are kept as
separate fields; a marker only gives a candidate region until QA confirms the
frame. `mark_event` therefore just appends to a JSONL sidecar — it never
touches the video container.
"""

import json
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.tool_paths import find_binary


class CaptureError(RuntimeError):
    pass


def scrcpy_path() -> str:
    found = find_binary("scrcpy")
    if found is None:
        raise CaptureError("scrcpy_not_found")
    return found


@dataclass
class RecordingHandle:
    serial: str
    video_path: Path
    events_path: Path
    process: subprocess.Popen
    started_monotonic: float


class CaptureManager:
    def __init__(self):
        self._active: dict[str, RecordingHandle] = {}

    def start_recording(self, serial: str, output_dir: Path, name: str) -> RecordingHandle:
        if serial in self._active:
            raise CaptureError(f"already_recording: {serial}")

        output_dir.mkdir(parents=True, exist_ok=True)
        video_path = output_dir / f"{name}.mp4"
        events_path = output_dir / f"{name}.events.jsonl"
        partial_path = video_path.with_suffix(video_path.suffix + ".partial")

        argv = [
            scrcpy_path(),
            "-s",
            serial,
            "--no-playback",
            "--record",
            str(partial_path),
            "--record-format=mp4",
        ]

        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        handle = RecordingHandle(
            serial=serial,
            video_path=video_path,
            events_path=events_path,
            process=process,
            started_monotonic=time.monotonic(),
        )
        self._active[serial] = handle
        events_path.write_text("", encoding="utf-8")
        return handle

    def mark_event(self, serial: str, label: str, payload: dict | None = None) -> None:
        handle = self._active.get(serial)
        if handle is None:
            raise CaptureError(f"not_recording: {serial}")
        entry = {
            "monotonic_ns": time.monotonic_ns(),
            "label": label,
            "payload": payload or {},
        }
        with handle.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def stop_recording(self, serial: str, graceful_timeout_s: float = 5.0) -> Path:
        handle = self._active.pop(serial, None)
        if handle is None:
            raise CaptureError(f"not_recording: {serial}")

        if sys.platform == "win32":
            try:
                handle.process.send_signal(signal.CTRL_BREAK_EVENT)
            except (OSError, ValueError):
                handle.process.terminate()
        else:
            handle.process.send_signal(signal.SIGINT)

        try:
            handle.process.wait(timeout=graceful_timeout_s)
        except subprocess.TimeoutExpired:
            # Last resort per spec 11.5: force kill, but the resulting file
            # must still pass container-close validation before use.
            handle.process.kill()
            handle.process.wait(timeout=5.0)

        partial_path = handle.video_path.with_suffix(handle.video_path.suffix + ".partial")
        if partial_path.exists():
            partial_path.rename(handle.video_path)
        return handle.video_path

    def is_recording(self, serial: str) -> bool:
        return serial in self._active
