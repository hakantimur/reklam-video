"""Mock-only tests: fakes `app.device.adb`, a fake in-memory `CaptureManager`
(writes a small dummy file instead of running real scrcpy) and a canned
`technical_qc.run_technical_qc` result, to prove the capture loop's own logic
(shot lookup, budget, takeover handling, Asset/Take persistence) independent
of any real hardware, LLM call, or ffmpeg binary. Real-device/real-ffmpeg
evidence lives in `tests/device/` under the `device_live` marker.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.device import adb
from app.media import technical_qc
from app.models.creative import Revision, Shot, Take
from app.models.device import DeviceProfile, GameProfile
from app.schemas.operator import OperatorAction, OperatorDecision
from app.services import capture as capture_service
from app.services import projects as projects_service
from app.services.capture import CaptureTakeoverRequested
from app.services.errors import BlockedError, ValidationAppError

_TINY_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


def _fake_adb(monkeypatch, *, serial="emulator-5554", connected=True):
    monkeypatch.setattr(
        adb,
        "list_devices",
        lambda: [adb.ConnectedDevice(serial=serial, state="device" if connected else "offline")],
    )
    monkeypatch.setattr(adb, "screen_size", lambda serial: (1080, 2400))
    monkeypatch.setattr(adb, "orientation", lambda serial: 0)
    monkeypatch.setattr(adb, "screenshot_png", lambda serial: _TINY_PNG)
    monkeypatch.setattr(adb, "launch_app", lambda serial, package: None)
    monkeypatch.setattr(adb, "wait_for_foreground", lambda *a, **k: True)
    monkeypatch.setattr(adb, "tap", lambda serial, x, y: None)
    monkeypatch.setattr(adb, "swipe", lambda *a, **k: None)
    monkeypatch.setattr(adb, "press_back", lambda serial: None)


class _FakeCaptureManager:
    def __init__(self, tmp_path: Path):
        self._tmp_path = tmp_path
        self.events: list[tuple[str, dict]] = []
        self._video_path: Path | None = None

    def start_recording(self, serial, output_dir, name):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self._video_path = output_dir / f"{name}.mp4"
        self._video_path.write_bytes(b"fake-mp4-bytes")

    def mark_event(self, serial, label, payload=None):
        self.events.append((label, payload or {}))

    def stop_recording(self, serial):
        return self._video_path


@pytest.fixture(autouse=True)
def _fake_technical_qc(monkeypatch):
    report = technical_qc.TechnicalQCReport(
        probe=technical_qc.MediaProbe(
            duration_s=2.0, width=1080, height=2400, has_video=True, has_audio=True,
            video_codec="h264", audio_codec="opus",
        ),
        decodes_cleanly=True,
        checks={"probe": "pass", "decode": "pass", "scene_detect": "pass", "blank_or_frozen": "pass"},
    )
    monkeypatch.setattr(capture_service.technical_qc, "run_technical_qc", lambda path: report)
    return report


def _decision(action_type: str, memory: dict | None = None, note: str | None = None) -> OperatorDecision:
    return OperatorDecision(
        screen_classification="playing",
        reasoning="test",
        memory_update=memory or {},
        action=OperatorAction(type=action_type, x=0.5, y=0.5, note=note),
    )


def _setup_shot(session, *, serial="emulator-5554", source_type="gameplay") -> tuple[str, str]:
    project = projects_service.create_project(session, name="Cekim Testi")
    projects_service.put_brief(
        session,
        project.id,
        audience="test",
        single_message="test",
        objective="install",
        style_id="style-1",
        language="tr",
        target_frames=600,
        fps_num=30,
        fps_den=1,
        placement_id="placement-1",
        budget_microusd=5_000_000,
        product_name="Synova",
        description="Hafiza oyunu",
        cta="Simdi indir",
    )
    brief = projects_service.get_latest_brief(session, project.id)

    revision = Revision(
        project_id=project.id,
        brief_id=brief.id,
        sequence_no=1,
        status="draft",
        timeline_json={},
        content_hash="deadbeef",
        created_at=datetime.now(timezone.utc),
    )
    session.add(revision)
    session.flush()

    shot = Shot(
        revision_id=revision.id,
        order_index=0,
        source_type=source_type,
        purpose="Ana mekanigi goster",
        desired_event="4x4 gridde dogru sirayla tiklama",
        target_frames=90,
        success_predicate_json={"required_observations": ["sequence completed"], "evidence_required": True},
    )
    session.add(shot)

    device_profile = DeviceProfile(serial=serial, package_id="com.example.synova.dev")
    session.add(device_profile)
    session.flush()

    game_profile = GameProfile(
        project_id=project.id,
        device_profile_id=device_profile.id,
        mechanic_summary="4x4 grid memory game",
        confidence=0.72,
    )
    session.add(game_profile)
    session.commit()

    return project.id, shot.id


def test_capture_persists_asset_and_take_on_finish(monkeypatch, db_session, tmp_path):
    serial = f"emulator-test-{uuid.uuid4().hex[:8]}"
    _fake_adb(monkeypatch, serial=serial)
    project_id, shot_id = _setup_shot(db_session, serial=serial)

    decisions = [
        _decision("tap", {"screen": "playing"}),
        _decision("tap", {"screen": "playing", "step": 2}),
        _decision("finish_discovery", note="sequence completed"),
    ]
    fake_operator = MagicMock(side_effect=decisions)
    monkeypatch.setattr(capture_service.operator_agent, "decide_next_action", fake_operator)

    fake_manager = _FakeCaptureManager(tmp_path)

    take = capture_service.capture_gameplay_shot(
        db_session,
        project_id,
        shot_id,
        serial=serial,
        provider=MagicMock(),
        model="test/model",
        max_actions=10,
        capture_manager=fake_manager,
    )

    assert isinstance(take, Take)
    assert take.status == "pending"
    assert take.attempt == 1
    assert fake_operator.call_count == 3
    assert ("desired_event_reached", {"note": "sequence completed"}) in fake_manager.events

    fetched = db_session.get(Take, take.id)
    assert fetched.asset_id == take.asset_id
    assert fetched.event_evidence_json["actions_log"][-1]["action"]["type"] == "finish_discovery"


def test_capture_second_attempt_increments(monkeypatch, db_session, tmp_path):
    serial = f"emulator-test-{uuid.uuid4().hex[:8]}"
    _fake_adb(monkeypatch, serial=serial)
    project_id, shot_id = _setup_shot(db_session, serial=serial)
    monkeypatch.setattr(
        capture_service.operator_agent,
        "decide_next_action",
        MagicMock(return_value=_decision("finish_discovery", note="done")),
    )

    first = capture_service.capture_gameplay_shot(
        db_session, project_id, shot_id, serial=serial, provider=MagicMock(), model="m",
        capture_manager=_FakeCaptureManager(tmp_path),
    )
    second = capture_service.capture_gameplay_shot(
        db_session, project_id, shot_id, serial=serial, provider=MagicMock(), model="m",
        capture_manager=_FakeCaptureManager(tmp_path),
    )

    assert first.attempt == 1
    assert second.attempt == 2


def test_capture_takeover_persists_rejected_take_and_raises(monkeypatch, db_session, tmp_path):
    serial = f"emulator-test-{uuid.uuid4().hex[:8]}"
    _fake_adb(monkeypatch, serial=serial)
    project_id, shot_id = _setup_shot(db_session, serial=serial)
    monkeypatch.setattr(
        capture_service.operator_agent,
        "decide_next_action",
        MagicMock(return_value=_decision("request_takeover", note="Permission dialog")),
    )

    with pytest.raises(CaptureTakeoverRequested) as exc_info:
        capture_service.capture_gameplay_shot(
            db_session, project_id, shot_id, serial=serial, provider=MagicMock(), model="m",
            capture_manager=_FakeCaptureManager(tmp_path),
        )

    assert exc_info.value.note == "Permission dialog"
    take = db_session.get(Take, exc_info.value.take_id)
    assert take.status == "rejected"
    assert "Permission dialog" in take.rejection_reason


def test_capture_rejects_non_gameplay_shot(monkeypatch, db_session, tmp_path):
    serial = f"emulator-test-{uuid.uuid4().hex[:8]}"
    _fake_adb(monkeypatch, serial=serial)
    project_id, shot_id = _setup_shot(db_session, serial=serial, source_type="ai_generated")

    with pytest.raises(ValidationAppError):
        capture_service.capture_gameplay_shot(
            db_session, project_id, shot_id, serial=serial, provider=MagicMock(), model="m",
            capture_manager=_FakeCaptureManager(tmp_path),
        )


def test_capture_blocked_when_device_not_connected(monkeypatch, db_session, tmp_path):
    serial = f"emulator-test-{uuid.uuid4().hex[:8]}"
    _fake_adb(monkeypatch, serial=serial, connected=False)
    project_id, shot_id = _setup_shot(db_session, serial=serial)

    with pytest.raises(BlockedError):
        capture_service.capture_gameplay_shot(
            db_session, project_id, shot_id, serial=serial, provider=MagicMock(), model="m",
            capture_manager=_FakeCaptureManager(tmp_path),
        )


def test_capture_requires_game_profile(monkeypatch, db_session, tmp_path):
    serial = f"emulator-test-{uuid.uuid4().hex[:8]}"
    _fake_adb(monkeypatch, serial=serial)
    project = projects_service.create_project(db_session, name="Profilsiz Proje")
    projects_service.put_brief(
        db_session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=600, fps_num=30, fps_den=1,
        placement_id="p", budget_microusd=1, product_name="X", description="d", cta="c",
    )
    brief = projects_service.get_latest_brief(db_session, project.id)
    revision = Revision(
        project_id=project.id, brief_id=brief.id, sequence_no=1, status="draft",
        timeline_json={}, content_hash="x", created_at=datetime.now(timezone.utc),
    )
    db_session.add(revision)
    db_session.flush()
    shot = Shot(
        revision_id=revision.id, order_index=0, source_type="gameplay", purpose="p",
        target_frames=90,
    )
    db_session.add(shot)
    db_session.commit()

    with pytest.raises(ValidationAppError):
        capture_service.capture_gameplay_shot(
            db_session, project.id, shot.id, serial=serial, provider=MagicMock(), model="m",
            capture_manager=_FakeCaptureManager(tmp_path),
        )
