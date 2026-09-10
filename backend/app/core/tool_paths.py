"""Resolves external tool binaries (ffmpeg, ffprobe, scrcpy) that may live on
the system PATH or in the locally-fetched `backend/.tools/` directory
(populated by scripts/setup/fetch_binaries.py, spec 20.2)."""

import shutil
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parents[2] / ".tools"


def find_binary(name: str) -> str | None:
    on_path = shutil.which(name)
    if on_path:
        return on_path

    exe_name = f"{name}.exe"
    tool_root = _TOOLS_DIR / name
    if tool_root.is_dir():
        matches = list(tool_root.rglob(exe_name))
        if matches:
            return str(matches[0])

    # ffprobe ships inside the ffmpeg release bundle, not its own directory —
    # fall back to a full search of the fetched tools tree by exe name.
    if _TOOLS_DIR.is_dir():
        matches = list(_TOOLS_DIR.rglob(exe_name))
        if matches:
            return str(matches[0])
    return None
