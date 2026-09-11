"""Mock-only tests for `app.media.audio.normalize_loudness`'s edge-case
handling — every failure mode must return `None`, never raise, since the
caller (`app.services.render`) treats this as a best-effort enhancement
that must not fail an otherwise-successful render. The real, end-to-end
ffmpeg behavior is covered separately by
`tests/integration/test_audio_normalization.py` against a real capture.
"""

import json
import subprocess
from unittest.mock import MagicMock

from app.media import audio, technical_qc


def _measure_stderr(**overrides) -> str:
    stats = {
        "input_i": "-23.10", "input_tp": "-3.20", "input_lra": "6.00", "input_thresh": "-33.50",
        "target_offset": "0.50",
    }
    stats.update(overrides)
    return "ffmpeg progress noise\n" + json.dumps(stats) + "\nmore noise"


def test_normalize_loudness_returns_none_when_ffmpeg_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(audio, "find_binary", lambda name: None)

    result = audio.normalize_loudness(tmp_path / "in.mp4", tmp_path / "out.mp4")

    assert result is None


def test_normalize_loudness_measures_then_applies_with_the_measured_values(monkeypatch, tmp_path):
    monkeypatch.setattr(audio, "find_binary", lambda name: "C:/fake/ffmpeg.exe")
    fake_probe = MagicMock(has_video=True)
    monkeypatch.setattr(audio.technical_qc, "probe_media", lambda path: fake_probe)
    captured_apply_cmd = {}

    def fake_run(cmd, **kwargs):
        if "-f" in cmd and "null" in cmd:  # measurement pass
            return MagicMock(returncode=0, stdout="", stderr=_measure_stderr())
        captured_apply_cmd["cmd"] = cmd
        out_path = cmd[-1]
        from pathlib import Path

        Path(out_path).write_bytes(b"fake-normalized")
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(audio.subprocess, "run", fake_run)

    output_path = tmp_path / "out.mp4"
    result = audio.normalize_loudness(tmp_path / "in.mp4", output_path)

    assert result is not None
    assert result.measured_integrated_lufs == -23.10
    assert result.measured_true_peak_dbtp == -3.20
    assert result.measured_lra_lu == 6.00
    assert output_path.exists()
    apply_filter = captured_apply_cmd["cmd"][captured_apply_cmd["cmd"].index("-af") + 1]
    assert "measured_I=-23.1" in apply_filter
    assert "-c:v" in captured_apply_cmd["cmd"] and "copy" in captured_apply_cmd["cmd"]


def test_normalize_loudness_skips_near_silent_input(monkeypatch, tmp_path):
    monkeypatch.setattr(audio, "find_binary", lambda name: "C:/fake/ffmpeg.exe")
    monkeypatch.setattr(
        audio.subprocess, "run",
        lambda cmd, **k: MagicMock(returncode=0, stdout="", stderr=_measure_stderr(input_i="-90.00")),
    )

    result = audio.normalize_loudness(tmp_path / "in.mp4", tmp_path / "out.mp4")

    assert result is None


def test_normalize_loudness_returns_none_when_measurement_has_no_stats_block(monkeypatch, tmp_path):
    monkeypatch.setattr(audio, "find_binary", lambda name: "C:/fake/ffmpeg.exe")
    monkeypatch.setattr(
        audio.subprocess, "run", lambda cmd, **k: MagicMock(returncode=1, stdout="", stderr="no such file")
    )

    result = audio.normalize_loudness(tmp_path / "in.mp4", tmp_path / "out.mp4")

    assert result is None


def test_normalize_loudness_omits_c_v_copy_for_an_audio_only_input(monkeypatch, tmp_path):
    """`-c:v copy` on an audio-only input (no video stream) makes ffmpeg
    fail outright — found live against a real ElevenLabs voice MP3
    (see the integration test). Regression coverage for that fix."""

    monkeypatch.setattr(audio, "find_binary", lambda name: "C:/fake/ffmpeg.exe")
    monkeypatch.setattr(audio.technical_qc, "probe_media", lambda path: MagicMock(has_video=False))
    captured_apply_cmd = {}

    def fake_run(cmd, **kwargs):
        if "-f" in cmd and "null" in cmd:
            return MagicMock(returncode=0, stdout="", stderr=_measure_stderr())
        captured_apply_cmd["cmd"] = cmd
        from pathlib import Path

        Path(cmd[-1]).write_bytes(b"fake-normalized-audio")
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(audio.subprocess, "run", fake_run)

    output_path = tmp_path / "out.mp3"
    result = audio.normalize_loudness(tmp_path / "in.mp3", output_path)

    assert result is not None
    assert "-c:v" not in captured_apply_cmd["cmd"]
    assert "libmp3lame" in captured_apply_cmd["cmd"]  # mp3 output uses an mp3 encoder, not aac


def test_normalize_loudness_returns_none_when_video_probe_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(audio, "find_binary", lambda name: "C:/fake/ffmpeg.exe")
    monkeypatch.setattr(audio.subprocess, "run", lambda cmd, **k: MagicMock(returncode=0, stdout="", stderr=_measure_stderr()))

    def raise_tool_missing(path):
        raise technical_qc.ToolMissingError("ffprobe_failed: boom")

    monkeypatch.setattr(audio.technical_qc, "probe_media", raise_tool_missing)

    result = audio.normalize_loudness(tmp_path / "in.mp4", tmp_path / "out.mp4")

    assert result is None


def test_normalize_loudness_returns_none_when_apply_pass_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(audio, "find_binary", lambda name: "C:/fake/ffmpeg.exe")
    monkeypatch.setattr(audio.technical_qc, "probe_media", lambda path: MagicMock(has_video=True))

    def fake_run(cmd, **kwargs):
        if "-f" in cmd and "null" in cmd:
            return MagicMock(returncode=0, stdout="", stderr=_measure_stderr())
        return MagicMock(returncode=1, stdout="", stderr="encode failed")

    monkeypatch.setattr(audio.subprocess, "run", fake_run)

    result = audio.normalize_loudness(tmp_path / "in.mp4", tmp_path / "out.mp4")

    assert result is None


def test_normalize_loudness_returns_none_on_subprocess_timeout(monkeypatch, tmp_path):
    monkeypatch.setattr(audio, "find_binary", lambda name: "C:/fake/ffmpeg.exe")

    def raises_timeout(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=1)

    monkeypatch.setattr(audio.subprocess, "run", raises_timeout)

    result = audio.normalize_loudness(tmp_path / "in.mp4", tmp_path / "out.mp4")

    assert result is None
