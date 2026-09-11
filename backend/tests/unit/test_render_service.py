"""Mock-only tests: fakes `subprocess.run` (never spawns real npx/remotion)
and `technical_qc.run_technical_qc`, to prove the render service's own
logic (asset staging into apps/render/public/, props file handling, Asset
persistence) independent of a real Remotion render."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.media import technical_qc
from app.models.asset import Asset
from app.models.creative import Revision, Shot, Take
from app.services import assets as assets_service
from app.services import projects as projects_service
from app.services import render as render_service
from app.services.errors import ValidationAppError


def _setup_project_with_gameplay_take(session, tmp_path):
    project = projects_service.create_project(session, name="Render Testi")
    projects_service.put_brief(
        session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=90, fps_num=30, fps_den=1,
        placement_id="p", budget_microusd=1, product_name="Synova", description="d", cta="c",
    )
    brief = projects_service.get_latest_brief(session, project.id)
    revision = Revision(
        project_id=project.id, brief_id=brief.id, sequence_no=1, status="draft",
        timeline_json={}, content_hash="x", created_at=datetime.now(timezone.utc),
    )
    session.add(revision)
    session.flush()

    shot = Shot(revision_id=revision.id, order_index=0, source_type="gameplay", purpose="p", target_frames=90)
    session.add(shot)
    session.flush()

    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake-source-mp4")
    # relative_path must resolve under the real project root for
    # assets_service.resolve_asset_path to find it.
    import shutil
    from pathlib import Path

    dest_dir = Path(project.root_path) / "captures" / "raw"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "take1.mp4"
    shutil.copyfile(source_video, dest)

    asset = Asset(
        project_id=project.id, type="video", origin="emulator_capture",
        relative_path=str(dest.relative_to(Path(project.root_path))), sha256="h", byte_size=dest.stat().st_size,
    )
    session.add(asset)
    session.flush()
    take = Take(shot_id=shot.id, asset_id=asset.id, attempt=1, status="pending")
    session.add(take)
    session.commit()

    return project, shot


@pytest.fixture(autouse=True)
def _fake_technical_qc(monkeypatch):
    report = technical_qc.TechnicalQCReport(
        probe=technical_qc.MediaProbe(
            duration_s=3.0, width=1080, height=1920, has_video=True, has_audio=False,
            video_codec="h264", audio_codec=None,
        ),
        decodes_cleanly=True,
        checks={"probe": "pass", "decode": "pass", "scene_detect": "pass", "blank_or_frozen": "pass"},
    )
    monkeypatch.setattr(render_service.technical_qc, "run_technical_qc", lambda path: report)
    return report


@pytest.fixture(autouse=True)
def _fake_no_loudness_normalization(monkeypatch):
    """Default every test to "normalization unavailable" (mirrors a real
    environment with no usable audio track / no ffmpeg) so most tests
    don't pay for a real ffmpeg subprocess call on a fake, non-MP4 byte
    string. Tests that care about the loudness path override this."""

    monkeypatch.setattr(render_service.audio_media, "normalize_loudness", lambda *a, **k: None)


def test_render_preview_job_stages_assets_and_persists_output(monkeypatch, db_session, tmp_path):
    project, shot = _setup_project_with_gameplay_take(db_session, tmp_path)

    monkeypatch.setattr(render_service.shutil, "which", lambda name: "C:/fake/npx.cmd")

    def fake_run(argv, **kwargs):
        # argv: [npx, "remotion", "render", "src/index.ts", "AdComposition", <output>, "--props=..."]
        output_path = argv[5]
        from pathlib import Path

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"fake-rendered-mp4")
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(render_service.subprocess, "run", fake_run)

    asset = render_service.render_preview_job(db_session, project.id)

    assert asset.type == "proxy"
    assert asset.origin == "derived"
    assert (render_service.PUBLIC_DIR / f"video-{shot.id}.mp4").exists()

    from pathlib import Path

    assert (Path(project.root_path) / asset.relative_path).exists()


def test_render_preview_job_raises_on_nonzero_exit(monkeypatch, db_session, tmp_path):
    project, shot = _setup_project_with_gameplay_take(db_session, tmp_path)

    monkeypatch.setattr(render_service.shutil, "which", lambda name: "C:/fake/npx.cmd")
    monkeypatch.setattr(
        render_service.subprocess, "run", lambda *a, **k: MagicMock(returncode=1, stdout="", stderr="boom")
    )

    with pytest.raises(render_service.RenderError):
        render_service.render_preview_job(db_session, project.id)


def test_render_preview_job_requires_a_plan(db_session):
    project = projects_service.create_project(db_session, name="Plansiz Render Testi")

    with pytest.raises(ValidationAppError):
        render_service.render_preview_job(db_session, project.id)


def test_render_preview_job_records_loudness_when_normalization_succeeds(monkeypatch, db_session, tmp_path):
    from app.media import audio as audio_media

    project, shot = _setup_project_with_gameplay_take(db_session, tmp_path)
    monkeypatch.setattr(render_service.shutil, "which", lambda name: "C:/fake/npx.cmd")

    def fake_run(argv, **kwargs):
        from pathlib import Path

        output_path = argv[5]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"fake-rendered-mp4")
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(render_service.subprocess, "run", fake_run)

    fake_result = audio_media.LoudnessResult(
        measured_integrated_lufs=-23.1, measured_true_peak_dbtp=-3.2, measured_lra_lu=6.0,
    )

    def fake_normalize(input_path, output_path):
        # a real normalize would write a (different) file; the fake mimics
        # that so render.py's replace()/unlink() logic exercises for real.
        output_path.write_bytes(b"fake-normalized-mp4")
        return fake_result

    monkeypatch.setattr(render_service.audio_media, "normalize_loudness", fake_normalize)

    asset = render_service.render_preview_job(db_session, project.id)

    assert asset.audio_info_json["loudness_normalized"] is True
    assert asset.audio_info_json["measured_integrated_lufs"] == -23.1
    assert asset.audio_info_json["target_integrated_lufs"] == audio_media.TARGET_INTEGRATED_LUFS

    from pathlib import Path

    # the final persisted file is the normalized one, not the raw Remotion output
    assert (Path(project.root_path) / asset.relative_path).read_bytes() == b"fake-normalized-mp4"


def test_render_preview_job_keeps_original_file_when_normalization_is_unavailable(monkeypatch, db_session, tmp_path):
    project, shot = _setup_project_with_gameplay_take(db_session, tmp_path)
    monkeypatch.setattr(render_service.shutil, "which", lambda name: "C:/fake/npx.cmd")

    def fake_run(argv, **kwargs):
        from pathlib import Path

        output_path = argv[5]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"fake-rendered-mp4")
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(render_service.subprocess, "run", fake_run)
    # e.g. no usable audio track, ffmpeg missing, or either pass failed
    monkeypatch.setattr(render_service.audio_media, "normalize_loudness", lambda *a, **k: None)

    asset = render_service.render_preview_job(db_session, project.id)

    assert asset.audio_info_json == {"loudness_normalized": False}

    from pathlib import Path

    assert (Path(project.root_path) / asset.relative_path).read_bytes() == b"fake-rendered-mp4"
