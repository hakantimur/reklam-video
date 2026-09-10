"""Unit tests for validate_downloaded_media (spec §9.4: MIME + size + magic-byte)."""

from pathlib import Path

import pytest

from app.providers.network import MediaValidationError, validate_downloaded_media


def _write(tmp_path: Path, name: str, content: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


def test_accepts_valid_looking_mp4(tmp_path: Path):
    content = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2avc1mp41" + b"\x00" * 2000
    path = _write(tmp_path, "clip.mp4", content)
    validate_downloaded_media(path, content_type_header="video/mp4")  # must not raise


def test_rejects_html_error_page_saved_as_mp4(tmp_path: Path):
    content = b"<!DOCTYPE html><html><body>404 Not Found</body></html>" + b" " * 2000
    path = _write(tmp_path, "clip.mp4", content)
    # text/html is itself already a rejection (wrong content-type); the
    # HTML-body sniff is a second, independent line of defense for cases
    # where a provider mislabels the error page as e.g. video/mp4.
    with pytest.raises(MediaValidationError, match="content-type"):
        validate_downloaded_media(path, content_type_header="text/html")


def test_rejects_html_error_page_mislabeled_as_video(tmp_path: Path):
    content = b"<!DOCTYPE html><html><body>404 Not Found</body></html>" + b" " * 2000
    path = _write(tmp_path, "clip.mp4", content)
    with pytest.raises(MediaValidationError, match="HTML"):
        validate_downloaded_media(path, content_type_header="video/mp4")


def test_rejects_json_error_body(tmp_path: Path):
    content = b'{"error": {"code": 500, "message": "boom"}}' + b" " * 2000
    path = _write(tmp_path, "clip.mp4", content)
    with pytest.raises(MediaValidationError):
        validate_downloaded_media(path, content_type_header="application/json")


def test_rejects_too_small_file(tmp_path: Path):
    path = _write(tmp_path, "clip.mp4", b"\x00\x00\x00\x18ftyp")
    with pytest.raises(MediaValidationError, match="too small"):
        validate_downloaded_media(path, content_type_header="video/mp4", min_size_bytes=1024)


def test_rejects_missing_ftyp_magic_bytes(tmp_path: Path):
    content = b"not-a-real-video-container" + b"\x00" * 2000
    path = _write(tmp_path, "clip.mp4", content)
    with pytest.raises(MediaValidationError, match="ftyp"):
        validate_downloaded_media(path, content_type_header="video/mp4")


def test_rejects_unexpected_content_type(tmp_path: Path):
    content = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 2000
    path = _write(tmp_path, "clip.mp4", content)
    with pytest.raises(MediaValidationError, match="content-type"):
        validate_downloaded_media(path, content_type_header="text/plain")


def test_rejects_missing_file(tmp_path: Path):
    with pytest.raises(MediaValidationError, match="missing"):
        validate_downloaded_media(tmp_path / "does-not-exist.mp4", content_type_header="video/mp4")
