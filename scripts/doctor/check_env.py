#!/usr/bin/env python3
"""Standalone environment diagnostic CLI.

Spec reference: docs/IMPLEMENTATION_SPEC_TR.md §20.2 ("SETUP.bat Python/
Node/ADB/scrcpy/FFmpeg uygunlugunu kontrol eder" and "Donanim tani ekrani
... emulator test sonucunu gosterir"). This script is the independent,
scriptable core of that check -- it has no dependency on the rest of the
backend/frontend code so it can run before anything else is installed.

For each required tool it looks in two places, in order:
  1. The system PATH (a normal install the user already has).
  2. The project-local `backend/.tools/<tool>/...` copy produced by
     `scripts/setup/fetch_binaries.py`.

Exit code is 0 if every required tool was found and ran successfully,
1 otherwise. Use --json for machine-readable output.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "backend" / ".tools"


@dataclass
class CheckResult:
    tool: str
    found: bool
    path: Optional[str] = None
    version: Optional[str] = None
    source: Optional[str] = None  # "PATH" or "backend/.tools"
    error: Optional[str] = None
    required: bool = True


def _run_version(exe: Path | str, args: list[str]) -> str:
    result = subprocess.run(
        [str(exe), *args],
        capture_output=True,
        text=True,
        timeout=20,
        shell=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    first_line = output.strip().splitlines()[0] if output.strip() else ""
    if result.returncode != 0 and not first_line:
        raise RuntimeError(f"cikis kodu {result.returncode}, cikti yok")
    return first_line


def _check(tool: str, path_names: list[str], version_args: list[str],
           local_candidates: list[Path], required: bool = True) -> CheckResult:
    # 1) System PATH
    for name in path_names:
        found = shutil.which(name)
        if found:
            try:
                version = _run_version(found, version_args)
                return CheckResult(tool, True, found, version, "PATH", required=required)
            except Exception as exc:  # noqa: BLE001
                return CheckResult(tool, True, found, None, "PATH", error=str(exc), required=required)

    # 2) Project-local backend/.tools copy
    for candidate in local_candidates:
        if candidate.is_file():
            try:
                version = _run_version(candidate, version_args)
                return CheckResult(
                    tool, True, str(candidate), version, "backend/.tools", required=required
                )
            except Exception as exc:  # noqa: BLE001
                return CheckResult(
                    tool, True, str(candidate), None, "backend/.tools", error=str(exc), required=required
                )

    return CheckResult(tool, False, required=required)


def run_all() -> list[CheckResult]:
    checks: list[CheckResult] = []

    checks.append(_check("node", ["node"], ["--version"], []))
    checks.append(_check("npm", ["npm"], ["--version"], []))
    checks.append(
        _check(
            "python",
            ["python", "python3"],
            ["--version"],
            [],
        )
    )
    checks.append(
        _check(
            "adb",
            ["adb"],
            ["version"],
            [TOOLS_DIR / "scrcpy" / "adb.exe"],
        )
    )
    checks.append(
        _check(
            "ffmpeg",
            ["ffmpeg"],
            ["-version"],
            [TOOLS_DIR / "ffmpeg" / "bin" / "ffmpeg.exe"],
        )
    )
    checks.append(
        _check(
            "ffprobe",
            ["ffprobe"],
            ["-version"],
            [TOOLS_DIR / "ffmpeg" / "bin" / "ffprobe.exe"],
        )
    )
    checks.append(
        _check(
            "scrcpy",
            ["scrcpy"],
            ["--version"],
            [TOOLS_DIR / "scrcpy" / "scrcpy.exe"],
        )
    )
    return checks


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Sonucu JSON olarak yazdir.")
    args = parser.parse_args(argv)

    results = run_all()

    if args.json:
        print(json.dumps([r.__dict__ for r in results], indent=2, ensure_ascii=False))
    else:
        print("Ortam tanisi\n" + "=" * 60)
        for r in results:
            if not r.found:
                status = "BULUNAMADI"
            elif r.error:
                status = f"BULUNDU ama CALISTIRILAMADI ({r.error})"
            else:
                status = "OK"
            print(f"- {r.tool:8s} [{status}]")
            if r.found:
                print(f"    yol   : {r.path}  (kaynak: {r.source})")
                if r.version:
                    print(f"    surum : {r.version}")
        print("=" * 60)

    missing_or_broken = [r for r in results if r.required and (not r.found or r.error)]
    if missing_or_broken:
        names = ", ".join(r.tool for r in missing_or_broken)
        print(f"\nEksik/bozuk araclar: {names}", file=sys.stderr)
        print(
            "ffmpeg/scrcpy icin: python scripts/setup/fetch_binaries.py calistirin.",
            file=sys.stderr,
        )
        return 1

    print("\nTum zorunlu araclar bulundu ve calisiyor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
