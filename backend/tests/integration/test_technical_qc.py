"""Integration: technical QC pipeline against a real, previously-captured
device recording (not a synthetic fixture) — proves the checks work on an
actual scrcpy MP4, not just a hand-crafted test file.

Skipped if ffmpeg/ffprobe aren't resolvable or the sample file is absent
(it's a local dev artifact under backend/.tools/, not committed).
"""

from pathlib import Path

import pytest

from app.core.tool_paths import find_binary
from app.media.technical_qc import run_technical_qc

SAMPLE_VIDEO = Path(__file__).resolve().parents[2] / ".tools" / "test_capture" / "safha4_live_test.mp4"


@pytest.fixture(scope="module")
def sample_video() -> Path:
    if find_binary("ffprobe") is None or find_binary("ffmpeg") is None:
        pytest.skip("ffmpeg/ffprobe not available")
    if not SAMPLE_VIDEO.exists():
        pytest.skip("no locally captured sample video present")
    return SAMPLE_VIDEO


def test_real_capture_passes_technical_qc(sample_video: Path):
    report = run_technical_qc(sample_video)

    assert report.probe is not None
    assert report.probe.has_video is True
    assert report.probe.has_audio is True
    assert report.probe.duration_s > 15.0
    assert report.decodes_cleanly is True
    assert report.frozen is False
    assert report.blank_frame_ratio < 0.5
    assert report.outcome == "pass"
