"""OS credential store integration for provider API keys (spec 20.1).

Keys must land in the platform credential store (Windows Credential
Manager / macOS Keychain / Secret Service) via `keyring`, never in a
plaintext JSON file on disk. If no OS backend is available at runtime we
fall back to an in-memory, session-only store so the app stays usable, but
that fallback is explicit and disappears on restart — it must never
silently degrade into a plaintext file.
"""

from __future__ import annotations

import keyring
from keyring.errors import KeyringError

_SERVICE_NAME = "LocalAdDirector"

# Session-only fallback, used only when the OS backend itself is unavailable
# (spec 20.1: "OS credential store çalışmıyorsa session-only key sun;
# plaintext JSON'a sessiz fallback yapma"). Cleared on process restart.
_session_only_store: dict[str, str] = {}


def _mask(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    if len(value) <= 8:
        return f"{value[0]}{'*' * (len(value) - 2)}{value[-1]}"
    return f"{value[:2]}{'*' * (len(value) - 6)}{value[-4:]}"


def set_credential(provider: str, api_key: str) -> dict:
    if not api_key or not api_key.strip():
        raise ValueError("api_key must not be empty")
    try:
        keyring.set_password(_SERVICE_NAME, provider, api_key)
        _session_only_store.pop(provider, None)
        return {"provider": provider, "status": "saved", "masked_key": _mask(api_key)}
    except KeyringError:
        _session_only_store[provider] = api_key
        return {"provider": provider, "status": "session_only", "masked_key": _mask(api_key)}


def get_credential_status(provider: str) -> dict:
    """Masked status only — never returns the raw key (spec 20.1: logs/screen
    share/export must never expose it)."""

    try:
        value = keyring.get_password(_SERVICE_NAME, provider)
    except KeyringError:
        value = None
    if value:
        return {"provider": provider, "status": "saved", "masked_key": _mask(value)}
    if provider in _session_only_store:
        return {
            "provider": provider,
            "status": "session_only",
            "masked_key": _mask(_session_only_store[provider]),
        }
    return {"provider": provider, "status": "not_set", "masked_key": None}


def get_credential_value(provider: str) -> str | None:
    """Internal use only (provider adapters) — never surface this via an API response."""

    try:
        value = keyring.get_password(_SERVICE_NAME, provider)
    except KeyringError:
        value = None
    return value or _session_only_store.get(provider)
