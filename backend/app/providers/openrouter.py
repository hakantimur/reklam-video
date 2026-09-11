"""OpenRouter provider adapter (spec IMPLEMENTATION_SPEC_TR.md §9).

Contract verified live (no API key needed) on 2026-09-11 against
`https://openrouter.ai/openapi.json` and a real `GET /models` /
`GET /videos/models` call:

  GET  /models                  -> {"data": [ ... 400+ real models ... ]}
  GET  /videos/models           -> {"data": [ ... real video models ... ]}
  POST /videos                  -> 202 {"id", "polling_url", "status": "pending", ...}
  GET  /videos/{jobId}          -> {"status", "unsigned_urls": [...], "usage": {...}}
  GET  /videos/{jobId}/content  -> raw "video/mp4" bytes proxied from upstream
  POST /chat/completions        -> response_format.type == "json_schema" for
                                    structured output (ChatFormatJsonSchemaConfig)

There is no documented DELETE/cancel endpoint for `/videos/{jobId}` in the
live OpenAPI spec, so `OpenRouterVideoProvider.cancel()` raises
`UnsupportedOperationError` rather than pretending to cancel a remote job
(spec §9.2/§19.2).

Everything that requires an Authorization header (chat completions, video
submit/poll/download) needs a real API key, which this machine does not have
(spec §2.2) -- those paths are exercised only by mock/contract tests here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.providers.base import (
    ChatMessage,
    CostEstimate,
    StructuredGenerationOptions,
    SubmissionUnknownError,
    UnsupportedOperationError,
    VideoGenerationRequest,
    VideoPollResult,
    VideoValidationResult,
)
from app.providers.network import (
    download_with_retry,
    get_with_retry,
    is_safe_public_url,
    validate_downloaded_media,
)
from app.schemas.provider import ProviderModel, utcnow_iso

# OpenRouter's own video-generation status vocabulary, mapped onto the job
# states used across the app (spec §8.2). "cancelled"/"expired" are terminal
# non-success outcomes, so they map to "failed" here.
_VIDEO_STATUS_TO_STATE = {
    "pending": "queued",
    "in_progress": "running",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "failed",
    "expired": "failed",
}


def _bool_or_none(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _list_or_empty(value: Any) -> list:
    return value if isinstance(value, list) else []


def normalize_text_model(raw: dict[str, Any]) -> ProviderModel:
    """Map one raw `/models` catalog entry onto the spec §9.1 schema.

    `roles` is a candidate list derived from modality + tool-call support,
    never a compatibility guarantee -- `capability_status` stays
    "unverified" regardless of how rich the catalog entry is.
    """
    architecture = raw.get("architecture") or {}
    input_modalities = _list_or_empty(architecture.get("input_modalities"))
    output_modalities = _list_or_empty(architecture.get("output_modalities"))
    supported_parameters = _list_or_empty(raw.get("supported_parameters"))
    supports_tools = "tools" in supported_parameters if supported_parameters else None

    roles: list[str] = []
    if "text" in output_modalities:
        roles.extend(["director", "reviewer"])
        if supports_tools:
            roles.append("operator")

    return ProviderModel(
        id=raw["id"],
        roles=roles,
        input_modalities=input_modalities,
        output_modalities=output_modalities,
        supports_tools=supports_tools,
        pricing=raw.get("pricing") or {},
        capability_status="unverified",
        fetched_at=utcnow_iso(),
    )


def normalize_video_model(raw: dict[str, Any]) -> ProviderModel:
    """Map one raw `/videos/models` catalog entry onto the spec §9.1 schema."""
    durations = _list_or_empty(raw.get("supported_durations"))
    ratios = _list_or_empty(raw.get("supported_aspect_ratios"))
    resolutions = _list_or_empty(raw.get("supported_resolutions"))
    frame_images = raw.get("supported_frame_images")
    supports_reference_images = bool(frame_images) if isinstance(frame_images, list) else None

    return ProviderModel(
        id=raw["id"],
        roles=["video"],
        input_modalities=["text"],
        output_modalities=["video"],
        supports_tools=None,
        supported_durations_s=[float(d) for d in durations],
        supported_ratios=[str(r) for r in ratios],
        supported_resolutions=[str(r) for r in resolutions],
        supports_reference_images=supports_reference_images,
        supports_native_audio=_bool_or_none(raw.get("generate_audio")),
        supports_audio_driven_lipsync=None,
        pricing=raw.get("pricing_skus") or {},
        capability_status="unverified",
        fetched_at=utcnow_iso(),
    )


class OpenRouterClient:
    """Low-level HTTP wrapper shared by the text/vision and video adapters."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        http_client: httpx.Client | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self.base_url = (base_url or settings.openrouter_base_url).rstrip("/")
        self.api_key = api_key
        self._owns_client = http_client is None
        # follow_redirects=True is safe here: httpx's own redirect handling
        # (Client._redirect_headers) strips Authorization whenever a redirect
        # crosses origins, satisfying spec §9.4's "Authorization yabancı
        # host'a taşınmaz" rule without any custom code.
        self._client = http_client or httpx.Client(timeout=timeout_s, follow_redirects=True)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return get_with_retry(self._client, f"{self.base_url}{path}", headers=self.headers(), **kwargs)

    def post(self, path: str, json_body: dict[str, Any]) -> httpx.Response:
        # Paid/mutating POST: never auto-retried (spec §9.4/§19.2). A single
        # attempt only; callers decide what a timeout/5xx means for job state.
        return self._client.post(f"{self.base_url}{path}", headers=self.headers(), json=json_body)


class OpenRouterTextVisionProvider:
    """`TextVisionProvider` backed by OpenRouter `/models` + `/chat/completions`."""

    def __init__(self, client: OpenRouterClient | None = None) -> None:
        self._client = client or OpenRouterClient()

    def list_models(self) -> list[ProviderModel]:
        response = self._client.get("/models")
        response.raise_for_status()
        data = response.json().get("data", [])
        return [normalize_text_model(item) for item in data]

    def generate_structured(
        self,
        model: str,
        messages: list[ChatMessage],
        schema: dict[str, Any],
        options: StructuredGenerationOptions | None = None,
    ) -> dict[str, Any]:
        if not self._client.api_key:
            raise UnsupportedOperationError(
                "OpenRouter API key required for generate_structured (spec §2.2)"
            )
        options = options or StructuredGenerationOptions()
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.get("title", "structured_response"),
                    "schema": schema,
                    "strict": True,
                },
            },
        }
        if options.temperature is not None:
            body["temperature"] = options.temperature
        if options.max_output_tokens is not None:
            body["max_tokens"] = options.max_output_tokens
        body.update(options.extra)

        response = self._client.post("/chat/completions", body)
        if response.status_code >= 400:
            raise RuntimeError(
                f"OpenRouter chat completion failed: {response.status_code} {response.text}"
            )
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)


class OpenRouterVideoProvider:
    """`VideoProvider` backed by OpenRouter `/videos*` (spec §9.3)."""

    def __init__(self, client: OpenRouterClient | None = None) -> None:
        self._client = client or OpenRouterClient()
        self._model_cache: dict[str, ProviderModel] | None = None

    def list_models(self) -> list[ProviderModel]:
        response = self._client.get("/videos/models")
        response.raise_for_status()
        data = response.json().get("data", [])
        models = [normalize_video_model(item) for item in data]
        self._model_cache = {m.id: m for m in models}
        return models

    def _model(self, model_id: str) -> ProviderModel | None:
        if self._model_cache is None:
            self.list_models()
        return (self._model_cache or {}).get(model_id)

    def validate_request(self, request: VideoGenerationRequest) -> VideoValidationResult:
        model = self._model(request.model_id)
        if model is None:
            return VideoValidationResult(ok=False, errors=[f"unknown video model: {request.model_id}"])

        errors: list[str] = []
        if model.supported_durations_s and request.duration_s not in model.supported_durations_s:
            errors.append(
                f"duration {request.duration_s}s not in supported durations "
                f"{model.supported_durations_s}; planner must render the nearest "
                "supported duration and trim the used span (spec §9.3), not "
                "arbitrarily speed up the clip"
            )
        if model.supported_ratios and request.ratio not in model.supported_ratios:
            errors.append(f"ratio {request.ratio!r} not in supported ratios {model.supported_ratios}")
        if (
            request.resolution
            and model.supported_resolutions
            and request.resolution not in model.supported_resolutions
        ):
            errors.append(
                f"resolution {request.resolution!r} not in supported resolutions "
                f"{model.supported_resolutions}"
            )
        if request.reference_image_paths and model.supports_reference_images is False:
            errors.append(f"model {model.id} does not support reference images")

        ok = not errors
        return VideoValidationResult(
            ok=ok,
            errors=errors,
            resolved_duration_s=request.duration_s if ok else None,
            resolved_ratio=request.ratio if ok else None,
            resolved_resolution=request.resolution if ok else None,
        )

    def estimate_cost(self, request: VideoGenerationRequest) -> CostEstimate:
        model = self._model(request.model_id)
        if model is None:
            return CostEstimate(
                amount_microusd=None, confidence="unknown", basis="model not found in catalog"
            )
        cents_per_second = model.pricing.get("cents_per_second_output")
        if cents_per_second is None:
            # Spec §19.1: unknown price is not zero -- report unknown, never
            # a silent free estimate.
            return CostEstimate(
                amount_microusd=None, confidence="unknown", basis="no per-second pricing published"
            )
        try:
            total_cents = float(cents_per_second) * request.duration_s
        except (TypeError, ValueError):
            return CostEstimate(
                amount_microusd=None, confidence="unknown", basis="unparsable pricing_skus value"
            )
        amount_microusd = round(total_cents * 10_000)  # 1 USD cent = 10,000 micro-USD
        return CostEstimate(
            amount_microusd=amount_microusd,
            confidence="estimated",
            basis="pricing_skus.cents_per_second_output * duration_s",
        )

    def submit(self, request: VideoGenerationRequest, *, idempotency_key: str) -> str:
        if not self._client.api_key:
            raise UnsupportedOperationError(
                "OpenRouter API key required to submit a video generation job (spec §2.2)"
            )
        body: dict[str, Any] = {
            "model": request.model_id,
            "prompt": request.prompt,
            "duration": request.duration_s,
            "aspect_ratio": request.ratio,
        }
        if request.resolution:
            body["resolution"] = request.resolution
        if request.generate_audio:
            body["generate_audio"] = True
        if request.reference_image_paths:
            body["frame_images"] = [
                {"frame_type": "first_frame", "image_url": path}
                for path in request.reference_image_paths
            ]
        body.update(request.extra)

        try:
            response = self._client.post("/videos", body)
        except httpx.TransportError as exc:
            raise SubmissionUnknownError(
                f"video submit transport failure with no confirmed remote id: {exc}",
                request_hash=idempotency_key,
            ) from exc

        if response.status_code == 202:
            return response.json()["id"]
        if response.status_code >= 500:
            # Spec §9.4/§19.2: a paid POST that fails server-side with no
            # confirmed remote id must not be blindly retried.
            raise SubmissionUnknownError(
                f"video submit returned {response.status_code} with no confirmed remote id",
                request_hash=idempotency_key,
            )
        raise RuntimeError(f"OpenRouter video submit rejected: {response.status_code} {response.text}")

    def poll(self, remote_id: str) -> VideoPollResult:
        response = self._client.get(f"/videos/{remote_id}")
        response.raise_for_status()
        payload = response.json()
        status = payload["status"]
        unsigned_urls = payload.get("unsigned_urls") or []
        usage = payload.get("usage") or {}
        return VideoPollResult(
            remote_id=remote_id,
            state=_VIDEO_STATUS_TO_STATE.get(status, "running"),
            progress_note=status,
            download_url=unsigned_urls[0] if unsigned_urls else None,
            error=payload.get("error"),
            cost_usd=usage.get("cost"),
        )

    def download(self, remote_id: str, destination: Path) -> Path:
        # Prefer OpenRouter's own documented content-proxy endpoint over a
        # provider-supplied `unsigned_urls` entry: it is always our own host,
        # so it can never smuggle a private-IP/localhost/file:// SSRF target.
        # We still run it through the same is_safe_public_url() gate as any
        # other media URL (spec §9.4) rather than special-casing it.
        url = f"{self._client.base_url}/videos/{remote_id}/content"
        if not is_safe_public_url(url):
            raise ValueError(f"refusing to download from unsafe URL: {url}")

        content_type = download_with_retry(
            self._client._client, url, destination, headers=self._client.headers()
        )
        try:
            validate_downloaded_media(destination, content_type_header=content_type)
        except Exception:
            # Never leave an HTML/JSON error body sitting at the final .mp4
            # path (spec §9.4): the transport layer already succeeded, but
            # content validation failed, so remove the bad file.
            if destination.exists():
                destination.unlink()
            raise
        return destination

    def cancel(self, remote_id: str) -> None:
        raise UnsupportedOperationError(
            "OpenRouter's live OpenAPI spec documents no DELETE/cancel route for "
            "/videos/{jobId}; local polling can stop, but the remote job may "
            "continue running and billing (spec §9.2/§19.2)"
        )
