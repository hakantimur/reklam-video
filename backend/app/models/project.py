from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    root_path: Mapped[str] = mapped_column(String(1024))
    locale: Mapped[str] = mapped_column(String(10), default="tr-TR")
    active_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("revisions.id", use_alter=True, name="fk_projects_active_revision"),
        nullable=True,
    )


class BrandProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "brand_profiles"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    product_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(2000))
    verified_claims_json: Mapped[list] = mapped_column(JSON, default=list)
    forbidden_claims_json: Mapped[list] = mapped_column(JSON, default=list)
    colors_json: Mapped[dict] = mapped_column(JSON, default=dict)
    logo_asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    cta: Mapped[str | None] = mapped_column(String(200), nullable=True)
    destination_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class Brief(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "briefs"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    audience: Mapped[str] = mapped_column(String(500))
    single_message: Mapped[str] = mapped_column(String(500))
    objective: Mapped[str] = mapped_column(String(200))
    style_id: Mapped[str] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(10), default="tr")
    target_frames: Mapped[int] = mapped_column(Integer)
    fps_num: Mapped[int] = mapped_column(Integer, default=30)
    fps_den: Mapped[int] = mapped_column(Integer, default=1)
    placement_id: Mapped[str] = mapped_column(String(100))
    budget_microusd: Mapped[int] = mapped_column(Integer)
