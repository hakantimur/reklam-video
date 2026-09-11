"""Audio loudness normalization (spec §16.4: "Ses hedefi başlangıç
preset'i olarak yaklaşık -16 LUFS integrated ve true peak ≤ -1 dBTP; bu
değerler platform zorunluluğu değil ürün miks varsayılanı").

Two-pass EBU R128 loudness normalization via ffmpeg's built-in `loudnorm`
filter — no extra dependency beyond ffmpeg, already required by
`app.media.technical_qc`. Best-effort throughout: a render's own success
must never depend on this succeeding, so every failure mode here returns
`None` for the caller to fall back to the un-normalized file rather than
raising.
"""

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.tool_paths import find_binary
from app.media import technical_qc

TARGET_INTEGRATED_LUFS = -16.0
TARGET_TRUE_PEAK_DBTP = -1.0
TARGET_LOUDNESS_RANGE_LU = 11.0

# ffmpeg's own floor: below this the `loudnorm` measurement is dominated by
# noise floor / near-silence, not a meaningful signal to normalize.
_MIN_MEASURABLE_LUFS = -70.0

_MEASURE_TIMEOUT_S = 60.0
_APPLY_TIMEOUT_S = 120.0


@dataclass
class LoudnessResult:
    measured_integrated_lufs: float
    measured_true_peak_dbtp: float
    measured_lra_lu: float
    target_integrated_lufs: float = TARGET_INTEGRATED_LUFS
    target_true_peak_dbtp: float = TARGET_TRUE_PEAK_DBTP


def _measure(ffmpeg: str, path: Path) -> dict:
    result = subprocess.run(
        [
            ffmpeg, "-i", str(path),
            "-af", (
                f"loudnorm=I={TARGET_INTEGRATED_LUFS}:TP={TARGET_TRUE_PEAK_DBTP}:"
                f"LRA={TARGET_LOUDNESS_RANGE_LU}:print_format=json"
            ),
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        timeout=_MEASURE_TIMEOUT_S,
    )
    # loudnorm's analysis pass writes its JSON stats block to stderr,
    # interleaved with ffmpeg's own progress logging.
    match = re.search(r"\{[^{}]*\}", result.stderr, re.DOTALL)
    if match is None:
        raise RuntimeError(f"loudnorm measurement produced no stats block: {result.stderr[-500:]}")
    return json.loads(match.group(0))


def normalize_loudness(input_path: Path, output_path: Path) -> LoudnessResult | None:
    """Measure `input_path`'s integrated loudness/true peak/loudness range
    and, if there's a meaningful signal, write a loudness-normalized copy
    to `output_path` — the video stream is copied through untouched
    (`-c:v copy`), only audio is re-encoded. Returns `None` (and never
    writes `output_path`) when ffmpeg is unavailable, the file has no
    usable audio, or either ffmpeg pass fails — callers must keep using
    the original file in that case."""

    ffmpeg = find_binary("ffmpeg")
    if ffmpeg is None:
        return None

    try:
        stats = _measure(ffmpeg, input_path)
        measured_i = float(stats["input_i"])
        measured_tp = float(stats["input_tp"])
        measured_lra = float(stats["input_lra"])
        measured_thresh = float(stats["input_thresh"])
        target_offset = float(stats.get("target_offset", 0.0))
    except (subprocess.SubprocessError, RuntimeError, KeyError, ValueError):
        return None

    if measured_i <= _MIN_MEASURABLE_LUFS:
        return None

    # `-c:v copy` errors out ("Invalid argument", zero packets written) on
    # an audio-only input (e.g. a standalone ElevenLabs voice-over MP3) —
    # there is no video stream to copy. Only add it when one actually
    # exists; a render's real input (an MP4 Remotion produced) always has
    # both streams, but this function isn't hardcoded to that one caller.
    try:
        has_video = technical_qc.probe_media(input_path).has_video
    except technical_qc.ToolMissingError:
        return None

    audio_codec = "libmp3lame" if output_path.suffix.lower() == ".mp3" else "aac"
    apply_filter = (
        f"loudnorm=I={TARGET_INTEGRATED_LUFS}:TP={TARGET_TRUE_PEAK_DBTP}:"
        f"LRA={TARGET_LOUDNESS_RANGE_LU}:measured_I={measured_i}:measured_TP={measured_tp}:"
        f"measured_LRA={measured_lra}:measured_thresh={measured_thresh}:"
        f"offset={target_offset}:linear=true:print_format=summary"
    )
    cmd = [ffmpeg, "-y", "-i", str(input_path), "-af", apply_filter]
    if has_video:
        cmd += ["-c:v", "copy"]
    cmd += ["-c:a", audio_codec, "-b:a", "192k", "-ar", "48000", str(output_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_APPLY_TIMEOUT_S)
    except subprocess.SubprocessError:
        return None

    if result.returncode != 0 or not output_path.exists():
        return None

    return LoudnessResult(
        measured_integrated_lufs=measured_i,
        measured_true_peak_dbtp=measured_tp,
        measured_lra_lu=measured_lra,
    )
