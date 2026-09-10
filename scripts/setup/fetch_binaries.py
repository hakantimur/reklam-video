#!/usr/bin/env python3
"""Fetch pinned, checksum-verified ffmpeg + scrcpy Windows x64 binaries.

Spec reference: docs/IMPLEMENTATION_SPEC_TR.md §20.2 ("Eksik acik araclar
yalnizca resmi release kaynagindan, surum/checksum dogrulamasiyla indirilir")
and §20.3 (lisans/kaynak kaydi -> bkz. docs/DECISIONS.md, THIRD_PARTY_NOTICES.md).

Design notes (see docs/DECISIONS.md for the full rationale):

- ffmpeg: downloaded from the GyanD/codexffmpeg GitHub repository, which is
  the GitHub-hosted release mirror of the gyan.dev Windows builds -- gyan.dev
  is one of the two Windows build providers ffmpeg.org's own download page
  links to (the other is BtbN/FFmpeg-Builds). gyan.dev itself does not
  publish a signed checksum file next to the zip; instead we pin the
  SHA-256 "digest" GitHub's Releases API reports for that immutable release
  asset (GitHub computes this server-side at upload time; it is not an
  independently-signed vendor checksum, so this is called out explicitly
  here and in DECISIONS.md).
- scrcpy: downloaded from Genymobile/scrcpy (the official upstream project
  repository) which DOES publish a proper SHA256SUMS.txt (plus a detached
  .asc signature) alongside every release. We pin the SHA-256 straight out
  of that official checksum file.

Both binaries are pinned to an explicit version number (never "latest").
Re-running this script is idempotent: already-downloaded/extracted and
correctly-verified binaries are left alone.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import platform
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "backend" / ".tools"
DOWNLOAD_CACHE_DIR = TOOLS_DIR / "_downloads"

USER_AGENT = "local-ad-director-fetch-binaries/1 (+https://github.com/hakantimur/reklam-video)"


@dataclass(frozen=True)
class BinarySpec:
    name: str
    version: str
    url: str
    sha256: str
    size_bytes: int
    dest_dir: Path
    # If the zip wraps everything in a single top-level folder, strip it
    # while extracting so files land directly under dest_dir.
    strip_top_level: bool
    # Relative path(s) under dest_dir that must exist after extraction,
    # used both as a "already installed" check and a post-install sanity
    # check.
    expect_paths: tuple[str, ...]
    version_check_cmd: tuple[str, ...]


FFMPEG_VERSION = "9.0.1"
FFMPEG_ASSET = f"ffmpeg-{FFMPEG_VERSION}-essentials_build.zip"
FFMPEG_SPEC = BinarySpec(
    name="ffmpeg",
    version=FFMPEG_VERSION,
    url=(
        "https://github.com/GyanD/codexffmpeg/releases/download/"
        f"{FFMPEG_VERSION}/{FFMPEG_ASSET}"
    ),
    # SHA-256 as reported by GitHub Releases API `digest` field for this
    # exact asset on the 9.0.1 release (fetched 2026-09-11, see
    # docs/DECISIONS.md). NOT an independently vendor-signed checksum.
    sha256="fec81ae03971d9dd4be3ebe02e263bd2ec1d789483f931bdba5f5715e65da2e9",
    size_bytes=111_253_802,
    dest_dir=TOOLS_DIR / "ffmpeg",
    strip_top_level=True,
    expect_paths=("bin/ffmpeg.exe", "bin/ffprobe.exe"),
    version_check_cmd=("bin/ffmpeg.exe", "-version"),
)

SCRCPY_VERSION = "v4.1"
SCRCPY_ASSET = f"scrcpy-win64-{SCRCPY_VERSION}.zip"
SCRCPY_SPEC = BinarySpec(
    name="scrcpy",
    version=SCRCPY_VERSION,
    url=(
        "https://github.com/Genymobile/scrcpy/releases/download/"
        f"{SCRCPY_VERSION}/{SCRCPY_ASSET}"
    ),
    # SHA-256 copied verbatim from the official SHA256SUMS.txt published in
    # the same v4.1 GitHub release (fetched 2026-09-11, see
    # docs/DECISIONS.md).
    sha256="5b12172b3264b2889f4583ee64752ce832e29bc8b1089dca81093459697165db",
    size_bytes=11_305_298,
    dest_dir=TOOLS_DIR / "scrcpy",
    strip_top_level=True,
    expect_paths=("scrcpy.exe",),
    version_check_cmd=("scrcpy.exe", "--version"),
)


class FetchError(RuntimeError):
    pass


def _check_platform() -> None:
    if platform.system() != "Windows":
        raise FetchError(
            "Bu betik yalnizca Windows x64 icin ikili dosya indirir; "
            f"algilanan isletim sistemi: {platform.system()}"
        )
    machine = platform.machine().lower()
    if machine not in ("amd64", "x86_64"):
        raise FetchError(
            "Bu betik yalnizca x64 mimarisi icin ikili dosya indirir; "
            f"algilanan mimari: {platform.machine()}"
        )


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(spec: BinarySpec) -> Path:
    DOWNLOAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest = DOWNLOAD_CACHE_DIR / f"{spec.name}-{spec.version}.zip"

    if dest.exists():
        actual_size = dest.stat().st_size
        if actual_size == spec.size_bytes and _sha256_of(dest) == spec.sha256:
            print(f"[{spec.name}] Onbellekte dogrulanmis indirme bulundu: {dest}")
            return dest
        print(f"[{spec.name}] Onbellekteki dosya beklenenle uyusmuyor, yeniden indiriliyor.")
        dest.unlink()

    print(f"[{spec.name}] Indiriliyor: {spec.url}")
    request = urllib.request.Request(spec.url, headers={"User-Agent": USER_AGENT})
    tmp_dest = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(request, timeout=120) as response, tmp_dest.open("wb") as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user as FetchError
        tmp_dest.unlink(missing_ok=True)
        raise FetchError(f"[{spec.name}] Indirme basarisiz: {exc}") from exc

    actual_size = tmp_dest.stat().st_size
    if actual_size != spec.size_bytes:
        tmp_dest.unlink(missing_ok=True)
        raise FetchError(
            f"[{spec.name}] Dosya boyutu uyusmuyor. Beklenen={spec.size_bytes} "
            f"Alinan={actual_size}. Kaynak degismis olabilir; surumu/checksum'i "
            "yeniden dogrulayip bu betikteki sabit degerleri guncelleyin."
        )

    actual_sha256 = _sha256_of(tmp_dest)
    if actual_sha256 != spec.sha256:
        tmp_dest.unlink(missing_ok=True)
        raise FetchError(
            f"[{spec.name}] SHA-256 uyusmuyor. Beklenen={spec.sha256} "
            f"Alinan={actual_sha256}. Dosya bozuk veya kaynak degismis olabilir; "
            "guvenlik nedeniyle devam edilmiyor."
        )

    tmp_dest.rename(dest)
    print(f"[{spec.name}] Indirme dogrulandi (boyut+SHA-256): {dest}")
    return dest


def _extract(spec: BinarySpec, archive_path: Path) -> None:
    if spec.dest_dir.exists():
        shutil.rmtree(spec.dest_dir)
    spec.dest_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path) as zf:
        names = zf.namelist()
        top_level_dirs = {n.split("/", 1)[0] for n in names if "/" in n}
        strip_prefix = ""
        if spec.strip_top_level and len(top_level_dirs) == 1:
            strip_prefix = next(iter(top_level_dirs)) + "/"

        for name in names:
            if name.endswith("/"):
                continue
            rel = name[len(strip_prefix):] if strip_prefix and name.startswith(strip_prefix) else name
            if not rel:
                continue
            target = spec.dest_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, target.open("wb") as out:
                shutil.copyfileobj(src, out)

    print(f"[{spec.name}] Cikartildi: {spec.dest_dir}")


def _already_installed(spec: BinarySpec) -> bool:
    return all((spec.dest_dir / p).is_file() for p in spec.expect_paths)


def _verify_runs(spec: BinarySpec) -> str:
    exe = spec.dest_dir / spec.version_check_cmd[0]
    if not exe.is_file():
        raise FetchError(f"[{spec.name}] Beklenen calistirilabilir dosya yok: {exe}")
    try:
        result = subprocess.run(
            [str(exe), *spec.version_check_cmd[1:]],
            cwd=spec.dest_dir,
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,
        )
    except Exception as exc:  # noqa: BLE001
        raise FetchError(f"[{spec.name}] Calistirma denemesi basarisiz: {exc}") from exc

    output = (result.stdout or "") + (result.stderr or "")
    first_line = output.strip().splitlines()[0] if output.strip() else "(cikti yok)"
    if result.returncode not in (0,):
        # scrcpy --version exits 0 normally; ffmpeg -version exits 0 too.
        raise FetchError(
            f"[{spec.name}] Beklenmeyen cikis kodu {result.returncode}. Cikti: {first_line}"
        )
    return first_line


def ensure_binary(spec: BinarySpec, force: bool) -> str:
    if not force and _already_installed(spec):
        print(f"[{spec.name}] Zaten kurulu: {spec.dest_dir}")
    else:
        archive = _download(spec)
        _extract(spec, archive)
    return _verify_runs(spec)


def _write_gitignore_entry() -> None:
    gitignore = REPO_ROOT / ".gitignore"
    marker = "backend/.tools/"
    text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if marker in text.splitlines():
        return
    if not text.endswith("\n") and text:
        text += "\n"
    text += (
        "\n# Downloaded third-party binaries (fetched by "
        "scripts/setup/fetch_binaries.py, never committed)\n"
        f"{marker}\n"
    )
    gitignore.write_text(text, encoding="utf-8")
    print(f".gitignore guncellendi: {marker} eklendi")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="Zaten kurulu olsa bile yeniden indir/cikart."
    )
    parser.add_argument(
        "--only",
        choices=["ffmpeg", "scrcpy"],
        help="Sadece tek bir aracı indir (varsayilan: ikisi de).",
    )
    args = parser.parse_args(argv)

    try:
        _check_platform()
        _write_gitignore_entry()

        specs = [FFMPEG_SPEC, SCRCPY_SPEC]
        if args.only:
            specs = [s for s in specs if s.name == args.only]

        results = {}
        for spec in specs:
            results[spec.name] = ensure_binary(spec, force=args.force)

        print("\n=== Ozet ===")
        for spec in specs:
            print(f"{spec.name} {spec.version}: {results[spec.name]}")
            print(f"  konum: {spec.dest_dir}")
        return 0
    except FetchError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
