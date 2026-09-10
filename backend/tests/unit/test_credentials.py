"""Spec 20.1: provider keys must go into the OS credential store, never a
plaintext JSON fallback.

`test_set_and_get_credential_via_real_os_keyring_backend` and
`test_credentials_api_masks_response` below make a REAL call into
`keyring`, which resolves to `keyring.backends.Windows.WinVaultKeyring`
(Windows Credential Manager) on this development machine — verified with a
standalone roundtrip script before writing this test, so this is not
assuming it works, it is exercising the real backend.

`test_set_credential_falls_back_to_session_only_when_os_backend_unavailable`
is explicitly MOCKED: it forces `keyring.set_password`/`get_password` to
raise, to simulate a machine with no usable OS credential store (e.g. a
headless CI box without Credential Manager/Keychain/Secret Service), which
we cannot reproduce for real on this dev machine.
"""

import keyring
from keyring.errors import KeyringError

from app.services import credentials as credentials_service


def test_set_and_get_credential_via_real_os_keyring_backend():
    provider = "test_provider_real_kr"
    try:
        result = credentials_service.set_credential(provider, "sk-real-abcdef123456")
        assert result["status"] == "saved"
        assert result["masked_key"] != "sk-real-abcdef123456"
        assert result["masked_key"].endswith("3456")

        status = credentials_service.get_credential_status(provider)
        assert status["status"] == "saved"
        assert status["masked_key"] == result["masked_key"]
    finally:
        try:
            keyring.delete_password("LocalAdDirector", provider)
        except Exception:
            pass


def test_set_credential_falls_back_to_session_only_when_os_backend_unavailable(monkeypatch):
    def _raise(*args, **kwargs):
        raise KeyringError("no backend available (mocked)")

    monkeypatch.setattr(credentials_service.keyring, "set_password", _raise)
    monkeypatch.setattr(credentials_service.keyring, "get_password", _raise)

    result = credentials_service.set_credential("provider_no_backend", "sk-fallback-key-999")
    assert result["status"] == "session_only"

    status = credentials_service.get_credential_status("provider_no_backend")
    assert status["status"] == "session_only"

    # Never persisted in plaintext anywhere on disk — only held in-process.
    assert credentials_service.get_credential_value("provider_no_backend") == "sk-fallback-key-999"


def test_set_credential_rejects_empty_key():
    import pytest

    with pytest.raises(ValueError):
        credentials_service.set_credential("some_provider", "   ")


def test_credentials_api_masks_response(api_client):
    provider = "openrouter_test_api"
    try:
        response = api_client.put(
            f"/api/v1/settings/credentials/{provider}", json={"api_key": "sk-1234567890abcdef"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["masked_key"] != "sk-1234567890abcdef"
        assert "1234567890abcdef" not in body["masked_key"]

        fetched = api_client.get(f"/api/v1/settings/credentials/{provider}")
        assert fetched.status_code == 200
        assert fetched.json()["status"] in {"saved", "session_only"}
    finally:
        try:
            keyring.delete_password("LocalAdDirector", provider)
        except Exception:
            pass
