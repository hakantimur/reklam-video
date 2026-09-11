"""Mock-only tests for `app.device.adb`'s foreground-detection helpers (no
real device needed) -- fakes `adb._run` entirely."""

from app.device import adb


def test_foreground_package_parses_mcurrentfocus_line(monkeypatch):
    output = (
        "  mCurrentFocus=Window{2c0e15b u0 com.noriloop.synova/com.noriloop.synova.MainActivity}\n"
    )
    monkeypatch.setattr(adb, "_run", lambda argv: output)

    assert adb.foreground_package("emulator-5554") == "com.noriloop.synova"


def test_foreground_package_returns_none_when_unparsable(monkeypatch):
    monkeypatch.setattr(adb, "_run", lambda argv: "nothing useful here\n")

    assert adb.foreground_package("emulator-5554") is None


def test_foreground_package_returns_none_on_adb_error(monkeypatch):
    def raise_error(argv):
        raise adb.AdbError("boom")

    monkeypatch.setattr(adb, "_run", raise_error)

    assert adb.foreground_package("emulator-5554") is None


def test_wait_for_foreground_returns_true_once_package_is_focused(monkeypatch):
    """Found live (2026-09-11): a real, asset-heavy app's cold start took
    longer than the flat 2s sleep this replaces, causing the vision agent's
    first observation to land on the home screen and waste a real API call
    requesting a human takeover. This must return as soon as the target
    package is confirmed foreground, not wait out the full timeout."""
    calls = []

    def fake_foreground_package(serial):
        calls.append(serial)
        return "com.noriloop.synova" if len(calls) >= 2 else "com.android.launcher"

    monkeypatch.setattr(adb, "foreground_package", fake_foreground_package)

    result = adb.wait_for_foreground(
        "emulator-5554", "com.noriloop.synova", timeout_s=5.0, poll_interval_s=0.01
    )

    assert result is True
    assert len(calls) == 2


def test_wait_for_foreground_returns_false_on_timeout(monkeypatch):
    monkeypatch.setattr(adb, "foreground_package", lambda serial: "com.android.launcher")

    result = adb.wait_for_foreground(
        "emulator-5554", "com.noriloop.synova", timeout_s=0.05, poll_interval_s=0.01
    )

    assert result is False
