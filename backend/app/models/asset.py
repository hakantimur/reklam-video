from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# assets.type values (spec 7.2)
ASSET_TYPES = (
    "video",
    "image",
    "audio",
    "subtitle",
    "storyboard",
    "proxy",
    "export",
    "evidence",
)

# assets.origin values (spec 7.2) — "synthetic_test" origin blocks final QA.
ASSET_ORIGINS = (
    "user_upload",
    "emulator_capture",
    "provider_generation",
    "derived",
    "synthetic_test",
)


class Asset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "assets"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    type: Mapped[str] = mapped_column(String(30))
    origin: Mapped[str] = mapped_column(String(30))
    relative_path: Mapped[str] = mapped_column(String(1024))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    byte_size: Mapped[int] = mapped_column(Integer)
    duration_us: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timebase_json: Mapped[dict] = mapped_column(JSON, default=dict)
    dimensions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    audio_info_json: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class AssetRights(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "asset_rights"

    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    license_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    user_provided: Mapped[bool] = mapped_column(Boolean, default=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
