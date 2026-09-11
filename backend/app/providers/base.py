"""Provider adapter interfaces (spec IMPLEMENTATION_SPEC_TR.md §9.2).

These are the contracts every concrete provider (OpenRouter, ElevenLabs, ...)
implements. They are intentionally provider-agnostic: nothing here assumes a
specific vendor's request/response shape. `cancel()` on `VideoProvider` raises
`UnsupportedOperationError` when a provider does not document remote
cancellation — callers must treat that as an explicit capability limit, never
as an implicit success.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from app.schemas.provider import ProviderModel


class UnsupportedOperationError(NotImplementedError):
    """Raised when a provider does not support a requested capability.

    This must be raised explicitly rather than silently faking success
    (spec §9.2: "destek yoksa açık Unsupported").
    """


class SubmissionUnknownError(RuntimeError):
    """A paid POST timed out/failed without a confirmed remote outcome.

    Spec §9.4/§19.2: when a provider offers no documented idempotency
    guarantee, a timed-out paid submission must never be blindly retried.
    Callers surface this as job state `submission_unknown` and require an
    explicit user/operator decision before doing anything further.
    """

    def __init__(self, message: str, *, request_hash: str | None = None) -> None:
        super().__init__(message)
        self.request_hash = request_hash


@dataclass
class StructuredGenerationOptions:
    temperature: float | None = None
    max_output_tokens: int | None = None
    timeout_s: float = 60.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    # A plain string for text-only messages, or a list of OpenAI/OpenRouter-
    # style content parts (`{"type": "text", "text": ...}` /
    # `{"type": "image_url", "image_url": {"url": ...}}`) for a message that
    # attaches an image (spec §11: the operator agent is vision-based —
    # it decides its next action from a real screenshot, not a text
    # description of one).
    content: str | list[dict[str, Any]]


def image_content_part(png_bytes: bytes) -> dict[str, Any]:
    import base64

    encoded = base64.b64encode(png_bytes).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}}


def text_content_part(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


@dataclass
class VideoGenerationRequest:
    model_id: str
    prompt: str
    duration_s: float
    ratio: str
    resolution: str | None = None
    reference_image_paths: list[str] = field(default_factory=list)
    generate_audio: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class VideoValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    resolved_duration_s: float | None = None
    resolved_ratio: str | None = None
    resolved_resolution: str | None = None


@dataclass
class CostEstimate:
    amount_microusd: int | None
    confidence: Literal["estimated", "unknown"]
    basis: str


@dataclass
class VideoPollResult:
    remote_id: str
    state: Literal["queued", "running", "completed", "failed"]
    progress_note: str | None = None
    download_url: str | None = None
    error: str | None = None
    # Real, provider-confirmed spend (OpenRouter's `usage.cost`, in USD) —
    # only ever a number the provider itself reports, never an estimate
    # (see `estimate_cost()` for the pre-flight guess, which is unreliable
    # for most real models' pricing shapes).
    cost_usd: float | None = None


@runtime_checkable
class TextVisionProvider(Protocol):
    def list_models(self) -> list[ProviderModel]: ...

    def generate_structured(
        self,
        model: str,
        messages: list[ChatMessage],
        schema: dict[str, Any],
        options: StructuredGenerationOptions | None = None,
    ) -> dict[str, Any]: ...


@runtime_checkable
class VideoProvider(Protocol):
    def list_models(self) -> list[ProviderModel]: ...

    def validate_request(self, request: VideoGenerationRequest) -> VideoValidationResult: ...

    def estimate_cost(self, request: VideoGenerationRequest) -> CostEstimate: ...

    def submit(self, request: VideoGenerationRequest, *, idempotency_key: str) -> str: ...

    def poll(self, remote_id: str) -> VideoPollResult: ...

    def download(self, remote_id: str, destination: Path) -> Path: ...

    def cancel(self, remote_id: str) -> None:
        """Raise UnsupportedOperationError when the provider has no documented
        remote-cancel endpoint. Never claim silent success."""
        ...


@runtime_checkable
class SpeechProvider(Protocol):
    def list_voices(self) -> list[dict[str, Any]]: ...

    def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str,
        voice_settings: dict[str, float | bool] | None = None,
    ) -> bytes: ...


@runtime_checkable
class LipSyncProvider(Protocol):
    def align(
        self,
        video_asset: Path,
        speech_asset: Path,
        options: dict[str, Any] | None = None,
    ) -> Path: ...
