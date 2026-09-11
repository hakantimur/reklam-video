"""Technical QC pipeline for a captured/generated clip (spec 12.2, 18.1).

Step order mirrors the spec: ffprobe metadata -> full decode test -> scene
change detection (informational only, never treated as a gameplay success
event) -> blank/frozen frame detection. Each stage is independently callable
so a caller can short-circuit after a hard failure (e.g. skip scene
detection on a file that doesn't even decode).
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from scenedetect import ContentDetector, SceneManager, open_video

from app.core.tool_paths import find_binary


class ToolMissingError(RuntimeError):
    pass


@dataclass
class MediaProbe:
    duration_s: float
    width: int | None
    height: int | None
    has_video: bool
    has_audio: bool
    video_codec: str | None
    audio_codec: str | None


@dataclass
class TechnicalQCReport:
    probe: MediaProbe | None = None
    decodes_cleanly: bool = False
    scene_change_timestamps_s: list[float] = field(default_factory=list)
    blank_frame_ratio: float = 0.0
    frozen: bool = False
    checks: dict[str, str] = field(default_factory=dict)  # name -> pass|fail|uncertain
    errors: list[str] = field(default_factory=list)

    @property
    def outcome(self) -> str:
        """pass | fail | uncertain, per spec 18.1's technical QA row."""
        if any(v == "fail" for v in self.checks.values()):
            return "fail"
        if any(v == "uncertain" for v in self.checks.values()):
            return "uncertain"
        return "pass"


def _require(binary: str) -> str:
    path = find_binary(binary)
    if path is None:
        raise ToolMissingError(f"{binary}_not_found")
    return path


def probe_media(path: Path) -> MediaProbe:
    ffprobe = _require("ffprobe")
    result = subprocess.run(
        [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration:stream=codec_type,codec_name,width,height",
            "-of", "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise ToolMissingError(f"ffprobe_failed: {result.stderr.strip()}")

    duration_s = 0.0
    width = height = None
    has_video = has_audio = False
    video_codec = audio_codec = None

    # ffprobe's csv writer for `stream=...` rows does not preserve the field
    # order given to -show_entries; it always emits codec_name before
    # codec_type. Locate "video"/"audio" by content, not position.
    for line in result.stdout.splitlines():
        parts = line.strip().split(",")
        if not parts or not parts[0]:
            continue
        if "video" in parts:
            has_video = True
            idx = parts.index("video")
            video_codec = parts[0] if idx != 0 else (parts[1] if len(parts) > 1 else None)
            numeric = [p for p in parts if p not in ("video", video_codec)]
            if len(numeric) >= 2:
                width, height = int(numeric[0]), int(numeric[1])
        elif "audio" in parts:
            has_audio = True
            idx = parts.index("audio")
            audio_codec = parts[0] if idx != 0 else (parts[1] if len(parts) > 1 else None)
        elif len(parts) == 1:
            try:
                duration_s = float(parts[0])
            except ValueError:
                pass

    return MediaProbe(
        duration_s=duration_s,
        width=width,
        height=height,
        has_video=has_video,
        has_audio=has_audio,
        video_codec=video_codec,
        audio_codec=audio_codec,
    )


def decode_test(path: Path, timeout_s: float = 60.0) -> bool:
    """Full decode via ffmpeg -f null -: catches truncated/corrupt files
    that ffprobe's metadata-only read can miss (spec 12.2 step 2)."""
    ffmpeg = _require("ffmpeg")
    result = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    # -v error only prints ffmpeg-classified errors, but some encoders
    # (scrcpy included, on variable-framerate capture) emit benign
    # non-monotonic-DTS warnings at error level against the `null` muxer.
    # A non-zero exit code is the reliable corruption signal; a real decode
    # failure also raises "Invalid data found" / "moov atom not found" text.
    fatal_markers = ("invalid data found", "moov atom not found", "error while decoding")
    stderr_lower = result.stderr.lower()
    return result.returncode == 0 and not any(marker in stderr_lower for marker in fatal_markers)


def detect_scene_changes(path: Path) -> list[float]:
    """Informational cut detection only — spec 12.2 explicitly forbids
    treating a detected scene change as a gameplay success event."""
    video = open_video(str(path))
    manager = SceneManager()
    manager.add_detector(ContentDetector())
    manager.detect_scenes(video)
    scenes = manager.get_scene_list()
    return [start.get_seconds() for start, _end in scenes]


def detect_blank_or_frozen_frames(
    path: Path, sample_every_n_frames: int = 15, blank_luma_threshold: float = 8.0
) -> tuple[float, bool]:
    """Returns (blank_frame_ratio, frozen). `frozen` is True when every
    sampled frame is near-identical to the previous one across the whole
    clip (spec 12.2 "uzun donma")."""
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ToolMissingError("opencv_could_not_open_video")

    sampled = 0
    blank_count = 0
    prev_gray = None
    all_frozen_so_far = True
    frame_index = 0

    try:
        while True:
            ok = capture.grab()
            if not ok:
                break
            if frame_index % sample_every_n_frames == 0:
                ok, frame = capture.retrieve()
                if not ok:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                sampled += 1
                if float(np.mean(gray)) < blank_luma_threshold:
                    blank_count += 1
                if prev_gray is not None:
                    diff = cv2.absdiff(gray, prev_gray)
                    if float(np.mean(diff)) > 1.0:
                        all_frozen_so_far = False
                prev_gray = gray
            frame_index += 1
    finally:
        capture.release()

    if sampled == 0:
        return 0.0, False
    ratio = blank_count / sampled
    frozen = all_frozen_so_far and sampled > 1
    return ratio, frozen


def sample_frames_png(path: Path, count: int = 4) -> list[bytes]:
    """Grab `count` evenly-spaced frames (first to last, inclusive) as PNG
    bytes — spec §10's reviewer agent judges a take from real sampled
    frames, never from a text description of what the clip should show."""

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ToolMissingError("opencv_could_not_open_video")

    try:
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            raise ToolMissingError("opencv_could_not_read_frame_count")

        count = max(1, min(count, total_frames))
        indices = [round(i * (total_frames - 1) / max(count - 1, 1)) for i in range(count)]

        frames: list[bytes] = []
        for index in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok:
                continue
            ok, encoded = cv2.imencode(".png", frame)
            if ok:
                frames.append(encoded.tobytes())
        if not frames:
            raise ToolMissingError("opencv_could_not_decode_any_sampled_frame")
        return frames
    finally:
        capture.release()


def run_technical_qc(path: Path) -> TechnicalQCReport:
    report = TechnicalQCReport()

    try:
        report.probe = probe_media(path)
    except ToolMissingError as exc:
        report.errors.append(str(exc))
        report.checks["probe"] = "uncertain"
        return report

    report.checks["probe"] = "pass" if report.probe.has_video else "fail"

    try:
        report.decodes_cleanly = decode_test(path)
        report.checks["decode"] = "pass" if report.decodes_cleanly else "fail"
    except ToolMissingError as exc:
        report.errors.append(str(exc))
        report.checks["decode"] = "uncertain"

    if report.checks.get("decode") == "fail":
        return report  # spec 12.2: no point sampling frames of a broken file

    try:
        report.scene_change_timestamps_s = detect_scene_changes(path)
        report.checks["scene_detect"] = "pass"
    except Exception as exc:  # noqa: BLE001 - scene detection is best-effort/informational
        report.errors.append(f"scene_detect_failed: {exc}")
        report.checks["scene_detect"] = "uncertain"

    try:
        report.blank_frame_ratio, report.frozen = detect_blank_or_frozen_frames(path)
        if report.frozen:
            report.checks["blank_or_frozen"] = "fail"
        elif report.blank_frame_ratio > 0.5:
            report.checks["blank_or_frozen"] = "fail"
        else:
            report.checks["blank_or_frozen"] = "pass"
    except ToolMissingError as exc:
        report.errors.append(str(exc))
        report.checks["blank_or_frozen"] = "uncertain"

    return report
