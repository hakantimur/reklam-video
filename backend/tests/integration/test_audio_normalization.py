"""Integration: loudness normalization against real, previously-produced
media (not synthetic fixtures) — proves `normalize_loudness` actually
measures and corrects real audio via a real ffmpeg subprocess, not just a
mocked one.

Two real samples, both local dev artifacts under `backend/.tools/` (not
committed, same as `test_technical_qc.py`'s sample capture):

- `safha4_live_test.mp4`: a real scrcpy gameplay capture from this
  session's Safha 4 device testing. Found live to have effectively no
  measurable audio (`loudnorm` reports `input_i: -inf`) — a genuine,
  useful finding about that specific recording, not a normalize_loudness
  bug: it correctly declines to "normalize" silence instead of crashing
  on it or fabricating a result.
- `safha8_live_voice_sample.mp3`: a real ElevenLabs voice-over generated
  earlier this session (Safha 8), copied in from the real Synova
  project's own asset folder — has genuine measurable speech, so this is
  the sample that proves the actual measure-then-normalize path.

Both skipped if ffmpeg/ffprobe aren't resolvable or the sample files are
absent.
"""

from pathlib import Path

import pytest

from app.core.tool_paths import find_binary
from app.media.audio import TARGET_INTEGRATED_LUFS, normalize_loudness

SAMPLE_DIR = Path(__file__).resolve().parents[2] / ".tools" / "test_capture"
SILENT_GAMEPLAY_VIDEO = SAMPLE_DIR / "safha4_live_test.mp4"
VOICE_SAMPLE = SAMPLE_DIR / "safha8_live_voice_sample.mp3"


def _require_ffmpeg():
    if find_binary("ffprobe") is None or find_binary("ffmpeg") is None:
        pytest.skip("ffmpeg/ffprobe not available")


def test_real_voice_sample_gets_normalized_toward_the_target_loudness(tmp_path: Path):
    _require_ffmpeg()
    if not VOICE_SAMPLE.exists():
        pytest.skip("no locally captured voice sample present")

    output_path = tmp_path / "normalized.mp3"
    result = normalize_loudness(VOICE_SAMPLE, output_path)

    assert result is not None
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    # a real ElevenLabs TTS render is not pre-mixed to any target, so the
    # raw measurement should sit clearly off -16 LUFS...
    assert -60.0 < result.measured_integrated_lufs < 0.0

    # ...but re-measuring the OUTPUT itself proves the correction actually
    # landed near the target, not just that ffmpeg exited 0.
    reverify = normalize_loudness(output_path, tmp_path / "reverify.mp3")
    assert reverify is not None
    assert abs(reverify.measured_integrated_lufs - TARGET_INTEGRATED_LUFS) < 1.5


def test_real_near_silent_gameplay_capture_is_not_normalized(tmp_path: Path):
    """A real scrcpy capture with no measurable signal must be left alone
    (return `None`), not crash or produce a garbage "normalized" file."""

    _require_ffmpeg()
    if not SILENT_GAMEPLAY_VIDEO.exists():
        pytest.skip("no locally captured sample video present")

    output_path = tmp_path / "normalized.mp4"
    result = normalize_loudness(SILENT_GAMEPLAY_VIDEO, output_path)

    assert result is None
    assert not output_path.exists()
