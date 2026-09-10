from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class QAReport(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "qa_reports"

    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id"), index=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    scope: Mapped[str] = mapped_column(String(30))  # technical|content|visual|ad|placement|human
    checks_json: Mapped[dict] = mapped_column(JSON, default=dict)
    reviewer_model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20))  # pass|fail|uncertain
    human_status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Export(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "exports"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id"))
    placement_profile_version: Mapped[str] = mapped_column(String(50))
    file_asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    manifest_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PerformanceNote(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "performance_notes"

    export_id: Mapped[str] = mapped_column(ForeignKey("exports.id"), index=True)
    impressions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    views_definition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    installs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spend_microusd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class EventLog(Base):
    __tablename__ = "event_log"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(100))
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
