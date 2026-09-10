import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.core.tool_paths import find_binary


@dataclass
class ToolCheck:
    name: str
    available: bool
    version: str | None
    path: str | None
    error: str | None = None


def _run_version(argv: list[str]) -> tuple[bool, str | None, str | None]:
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=10, shell=False
        )
        output = (result.stdout or result.stderr or "").strip().splitlines()
        return True, (output[0] if output else ""), None
    except FileNotFoundError:
        return False, None, "not_found"
    except subprocess.TimeoutExpired:
        return False, None, "timeout"
    except OSError as exc:
        return False, None, str(exc)


def check_tool(name: str, binary: str, version_args: list[str]) -> ToolCheck:
    resolved = find_binary(binary)
    if resolved is None:
        return ToolCheck(name=name, available=False, version=None, path=None, error="not_found")
    ok, version, error = _run_version([resolved, *version_args])
    return ToolCheck(name=name, available=ok, version=version, path=resolved, error=error)


def check_disk_space() -> dict:
    root = Path(settings.projects_root)
    root.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(root)
    return {
        "path": str(root),
        "free_bytes": usage.free,
        "total_bytes": usage.total,
        "free_gb": round(usage.free / (1024**3), 1),
    }


def run_diagnostics() -> dict:
    tools = [
        check_tool("node", "node", ["--version"]),
        check_tool("adb", "adb", ["version"]),
        check_tool("scrcpy", "scrcpy", ["--version"]),
        check_tool("ffmpeg", "ffmpeg", ["-version"]),
        check_tool("ffprobe", "ffprobe", ["-version"]),
    ]
    return {
        "tools": [t.__dict__ for t in tools],
        "disk": check_disk_space(),
        "all_required_present": all(t.available for t in tools),
    }
