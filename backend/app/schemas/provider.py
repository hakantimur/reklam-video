"""Normalized provider model catalog schema (spec IMPLEMENTATION_SPEC_TR.md §9.1).

The catalog returned by a provider (e.g. OpenRouter `/models`, `/videos/models`)
is never trusted as a compatibility verdict. `capability_status` always starts
as "unverified" here; it can only become "verified" or "incompatible" once a
real compatibility test has run against the concrete model. Individual
capability fields (e.g. `supports_native_audio`) may carry a real value taken
directly from the catalog when the provider explicitly reports it, but
`None` means "unknown" and must never be silently treated as `False`/`True`.
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

CapabilityStatus = Literal["unverified", "verified", "incompatible"]
ModelRole = Literal["director", "operator", "reviewer", "video"]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProviderModel(BaseModel):
    """Normalized catalog entry. Field names and defaults match spec §9.1 exactly."""

    id: str
    roles: list[ModelRole] = Field(default_factory=list)
    input_modalities: list[str] = Field(default_factory=list)
    output_modalities: list[str] = Field(default_factory=list)
    supports_tools: bool | None = None
    supported_durations_s: list[float] = Field(default_factory=list)
    supported_ratios: list[str] = Field(default_factory=list)
    supported_resolutions: list[str] = Field(default_factory=list)
    supports_reference_images: bool | None = None
    supports_native_audio: bool | None = None
    supports_audio_driven_lipsync: bool | None = None
    pricing: dict = Field(default_factory=dict)
    capability_status: CapabilityStatus = "unverified"
    fetched_at: str = Field(default_factory=utcnow_iso)


class ProviderCatalog(BaseModel):
    """A fetched-and-cached snapshot of one provider's model catalog."""

    provider: str
    models: list[ProviderModel] = Field(default_factory=list)
    fetched_at: str = Field(default_factory=utcnow_iso)
    stale: bool = False
    source: Literal["live", "cache"] = "live"
