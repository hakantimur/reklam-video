from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# jobs.state values (spec 8.2)
JOB_STATES = (
    "queued",
    "running",
    "succeeded",
    "waiting_provider",
    "paused",
    "blocked",
    "failed",
    "cancel_requested",
    "cancelled",
    "interrupted",
    "submission_unknown",
)


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("project_id", "idempotency_key", name="uq_job_idempotency"),)

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    revision_id: Mapped[str | None] = mapped_column(ForeignKey("revisions.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(50))
    state: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    lease_owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)


class ProviderRequest(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "provider_requests"

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    provider: Mapped[str] = mapped_column(String(100))
    model_id: Mapped[str] = mapped_column(String(200))
    request_hash: Mapped[str] = mapped_column(String(64))
    remote_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    state: Mapped[str] = mapped_column(String(30), default="queued")
    params_json: Mapped[dict] = mapped_column(JSON, default=dict)
    catalog_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cost_microusd: Mapped[int | None] = mapped_column(Integer, nullable=True)


class BudgetEntry(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "budget_entries"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    entry_type: Mapped[str] = mapped_column(String(30))  # reservation | settlement | release
    amount_microusd: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[str] = mapped_column(String(20), default="estimated")  # estimated|confirmed
    provider_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("provider_requests.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
