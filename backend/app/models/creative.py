from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Concept(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "concepts"

    brief_id: Mapped[str] = mapped_column(ForeignKey("briefs.id"), index=True)
    angle: Mapped[str] = mapped_column(String(200))
    hook: Mapped[str] = mapped_column(String(1000))
    rationale: Mapped[str] = mapped_column(String(2000))
    claim_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)


class CharacterProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "character_profiles"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    description: Mapped[str] = mapped_column(String(2000))
    wardrobe: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    location: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    voice_profile_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reference_asset_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    continuity_notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class Revision(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "revisions"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("revisions.id"), nullable=True)
    brief_id: Mapped[str] = mapped_column(ForeignKey("briefs.id"))
    sequence_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    timeline_json: Mapped[dict] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    change_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class Shot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "shots"

    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id"), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(30))  # gameplay | ai_generated | composed
    purpose: Mapped[str] = mapped_column(String(500))
    desired_event: Mapped[str | None] = mapped_column(String(200), nullable=True)
    start_state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    success_predicate_json: Mapped[dict] = mapped_column(JSON, default=dict)
    action_constraints_json: Mapped[dict] = mapped_column(JSON, default=dict)
    target_frames: Mapped[int] = mapped_column(Integer)
    handles_frames: Mapped[dict] = mapped_column(JSON, default=dict)
    character_id: Mapped[str | None] = mapped_column(
        ForeignKey("character_profiles.id"), nullable=True
    )
    generation_prompt: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    voice_text: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    caption_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    selected_take_id: Mapped[str | None] = mapped_column(
        ForeignKey("takes.id", use_alter=True, name="fk_shots_selected_take"), nullable=True
    )
    locks_json: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "visual": False,
            "source_range": False,
            "timing": False,
            "voice": False,
            "caption": False,
            "music": False,
        },
    )


class Take(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "takes"

    shot_id: Mapped[str] = mapped_column(ForeignKey("shots.id"), index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # accepted|rejected|uncertain|pending
    in_us: Mapped[int] = mapped_column(Integer, default=0)
    out_us: Mapped[int] = mapped_column(Integer, default=0)
    event_evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    quality_json: Mapped[dict] = mapped_column(JSON, default=dict)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
