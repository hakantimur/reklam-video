"""Mock-only tests: fakes `app.device.adb` entirely (no real device needed)
and a canned sequence of operator decisions, to prove the discovery loop's
own logic (budget, memory merge, finish/takeover handling, persistence)
independent of any real hardware or LLM call.
"""

from unittest.mock import MagicMock

import pytest

from app.device import adb
from app.models.device import DeviceProfile, GameProfile
from app.schemas.game_profile import GameProfileSummary
from app.schemas.operator import OperatorAction, OperatorDecision
from app.services import discovery as discovery_service
from app.services import projects as projects_service
from app.services.discovery import DiscoveryTakeoverRequested
from app.services.errors import BlockedError

_TINY_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


def _fake_adb(monkeypatch, *, connected=True):
    monkeypatch.setattr(
        adb,
        "list_devices",
        lambda: [adb.ConnectedDevice(serial="emulator-5554", state="device" if connected else "offline")],
    )
    monkeypatch.setattr(adb, "screen_size", lambda serial: (1080, 2400))
    monkeypatch.setattr(adb, "orientation", lambda serial: 0)
    monkeypatch.setattr(adb, "screenshot_png", lambda serial: _TINY_PNG)
    monkeypatch.setattr(adb, "launch_app", lambda serial, package: None)
    monkeypatch.setattr(adb, "wait_for_foreground", lambda *a, **k: True)
    monkeypatch.setattr(adb, "tap", lambda serial, x, y: None)
    monkeypatch.setattr(adb, "swipe", lambda *a, **k: None)
    monkeypatch.setattr(adb, "press_back", lambda serial: None)


def _decision(action_type: str, memory: dict | None = None, note: str | None = None) -> OperatorDecision:
    return OperatorDecision(
        screen_classification="playing",
        reasoning="test",
        memory_update=memory or {},
        action=OperatorAction(type=action_type, x=0.5, y=0.5, note=note),
    )


def test_discovery_stops_at_finish_discovery_and_persists_game_profile(monkeypatch, db_session):
    _fake_adb(monkeypatch)
    project_id = projects_service.create_project(db_session, name="Discovery Testi 1").id

    decisions = [
        _decision("tap", {"screen": "menu"}),
        _decision("tap", {"screen": "playing", "mechanic": "memory sequence"}),
        _decision("finish_discovery"),
    ]
    fake_operator = MagicMock(side_effect=decisions)
    monkeypatch.setattr(discovery_service.operator_agent, "decide_next_action", fake_operator)

    fake_summary = GameProfileSummary(
        mechanic_summary="Player repeats a shown sequence of tiles",
        navigation={"menu": "tap play to start"},
        state_signals={"menu": "logo visible"},
        supported_actions=["tap tile in sequence"],
        confidence=0.7,
    )
    monkeypatch.setattr(
        discovery_service, "generate_game_profile_summary", lambda *a, **k: fake_summary
    )

    profile = discovery_service.run_discovery(
        db_session,
        project_id,
        serial="emulator-5554",
        package_id="com.example.synova.dev",
        provider=MagicMock(),
        model="test/model",
        max_actions=10,
    )

    assert isinstance(profile, GameProfile)
    assert profile.mechanic_summary == "Player repeats a shown sequence of tiles"
    assert profile.confidence == 0.7
    assert fake_operator.call_count == 3  # stopped at finish_discovery, no 4th call

    device_profile = db_session.query(DeviceProfile).filter_by(serial="emulator-5554").one()
    assert device_profile.package_id == "com.example.synova.dev"
    assert device_profile.width == 1080


def test_discovery_stops_at_max_actions_budget(monkeypatch, db_session):
    _fake_adb(monkeypatch)
    project_id = projects_service.create_project(db_session, name="Discovery Testi 2").id

    # Every decision keeps tapping — the loop must stop on its own budget,
    # not rely on the model ever choosing to finish.
    fake_operator = MagicMock(return_value=_decision("tap"))
    monkeypatch.setattr(discovery_service.operator_agent, "decide_next_action", fake_operator)
    monkeypatch.setattr(
        discovery_service,
        "generate_game_profile_summary",
        lambda *a, **k: GameProfileSummary(
            mechanic_summary="unclear after budget exhausted",
            navigation={},
            state_signals={},
            supported_actions=[],
            confidence=0.1,
        ),
    )

    discovery_service.run_discovery(
        db_session,
        project_id,
        serial="emulator-5554",
        package_id="com.example.synova.dev",
        provider=MagicMock(),
        model="test/model",
        max_actions=3,
    )

    assert fake_operator.call_count == 3


def test_discovery_raises_takeover_without_persisting_a_game_profile(monkeypatch, db_session):
    _fake_adb(monkeypatch)
    project_id = projects_service.create_project(db_session, name="Discovery Testi 3").id

    monkeypatch.setattr(
        discovery_service.operator_agent,
        "decide_next_action",
        MagicMock(return_value=_decision("request_takeover", note="Login screen detected")),
    )

    with pytest.raises(DiscoveryTakeoverRequested) as exc_info:
        discovery_service.run_discovery(
            db_session,
            project_id,
            serial="emulator-5554",
            package_id="com.example.synova.dev",
            provider=MagicMock(),
            model="test/model",
            max_actions=10,
        )

    assert exc_info.value.note == "Login screen detected"
    assert db_session.query(GameProfile).filter_by(project_id=project_id).count() == 0


def test_discovery_blocked_when_device_not_connected(monkeypatch, db_session):
    _fake_adb(monkeypatch, connected=False)

    with pytest.raises(BlockedError):
        discovery_service.run_discovery(
            db_session,
            "project-not-checked-before-device",
            serial="emulator-5554",
            package_id="com.example.synova.dev",
            provider=MagicMock(),
            model="test/model",
        )
