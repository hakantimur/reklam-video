"""ElevenLabs SpeechProvider adapter (spec IMPLEMENTATION_SPEC_TR.md §9.2/§9.3).

Default second speech path when OpenRouter itself does not offer a
documented TTS contract (spec §9.2: "Varsayılan ikinci ses yolu ElevenLabs
resmi API'si; anahtar isteğe bağlı Ayarlar alanı"). Uses the v1 REST surface
consistent with `settings.elevenlabs_base_url`
("https://api.elevenlabs.io/v1"): `GET /voices` and
`POST /text-to-speech/{voice_id}`, authenticated with the `xi-api-key`
header (ElevenLabs' documented API-key header, distinct from OpenRouter's
`Authorization: Bearer`).

No ElevenLabs key exists on this machine (spec §2.2), so every call here
needs a real key and is exercised only via mock/contract tests, never live.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.providers.base import UnsupportedOperationError
from app.providers.network import get_with_retry


class ElevenLabsProvider:
    """`SpeechProvider` backed by the ElevenLabs REST API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        http_client: httpx.Client | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self.base_url = (base_url or settings.elevenlabs_base_url).rstrip("/")
        self.api_key = api_key
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout_s, follow_redirects=True)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["xi-api-key"] = self.api_key
        return headers

    def list_voices(self) -> list[dict[str, Any]]:
        if not self.api_key:
            raise UnsupportedOperationError(
                "ElevenLabs API key required to list voices (spec §2.2)"
            )
        response = get_with_retry(self._client, f"{self.base_url}/voices", headers=self._headers())
        response.raise_for_status()
        return response.json().get("voices", [])

    # Found live (2026-09-11): leaving `voice_settings` out entirely makes
    # ElevenLabs fall back to whatever default is stored against the voice
    # on the account, which the user heard as "çok robotik" on the real
    # Synova ad's voice-over. These are ElevenLabs' own documented
    # defaults for a natural, expressive `eleven_multilingual_v2` read —
    # lower stability trades a little consistency for a much less flat/
    # monotone delivery, `use_speaker_boost` clarifies the specific voice's
    # timbre instead of the model's generic average.
    DEFAULT_VOICE_SETTINGS: dict[str, float | bool] = {
        "stability": 0.4,
        "similarity_boost": 0.8,
        "style": 0.25,
        "use_speaker_boost": True,
    }

    def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str,
        voice_settings: dict[str, float | bool] | None = None,
    ) -> bytes:
        if not self.api_key:
            raise UnsupportedOperationError(
                "ElevenLabs API key required to synthesize speech (spec §2.2)"
            )
        body: dict[str, Any] = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": voice_settings or self.DEFAULT_VOICE_SETTINGS,
        }
        if language:
            body["language_code"] = language

        headers = {**self._headers(), "Content-Type": "application/json", "Accept": "audio/mpeg"}
        # Paid POST: never auto-retried here (spec §9.4/§19.2).
        response = self._client.post(
            f"{self.base_url}/text-to-speech/{voice_id}", json=body, headers=headers
        )
        if response.status_code >= 400:
            raise RuntimeError(f"ElevenLabs synthesize failed: {response.status_code} {response.text}")
        return response.content
