from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DeviceProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "device_profiles"

    serial: Mapped[str] = mapped_column(String(200), index=True)
    avd_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    android_api: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    orientation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    package_id: Mapped[str | None] = mapped_column(String(300), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capability_report_json: Mapped[dict] = mapped_column(JSON, default=dict)


class GameProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "game_profiles"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    device_profile_id: Mapped[str] = mapped_column(ForeignKey("device_profiles.id"))
    mechanic_summary: Mapped[str] = mapped_column(String(4000))
    navigation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    state_signals_json: Mapped[dict] = mapped_column(JSON, default=dict)
    supported_actions_json: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Checkpoint(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "checkpoints"

    game_profile_id: Mapped[str] = mapped_column(ForeignKey("game_profiles.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    snapshot_ref: Mapped[str] = mapped_column(String(300))
    app_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    emulator_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_evidence_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("assets.id"), nullable=True
    )
    valid: Mapped[bool] = mapped_column(Boolean, default=True)


class DeviceSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "device_sessions"

    device_profile_id: Mapped[str] = mapped_column(ForeignKey("device_profiles.id"), index=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    owner_token: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")


class DeviceEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "device_events"

    session_id: Mapped[str] = mapped_column(ForeignKey("device_sessions.id"), index=True)
    capture_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    monotonic_ns: Mapped[int] = mapped_column(Integer)
    media_pts_us: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mapping_uncertainty_us: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action_json: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
