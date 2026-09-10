"""Project CRUD and the on-disk project directory layout (spec 7.1, 7.3)."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import BrandProfile, Brief, Project
from app.services.errors import NotFoundError, ValidationAppError, VersionConflictError

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Spec 7.3 directory layout. `<project-root>/<product-slug>/<project-slug>--<short-id>/`
# is simplified to `<projects_root>/<project-slug>--<short-id>/` here because the
# product-slug segment depends on brand_profiles.product_name, which is only known
# once a brief/brand profile exists — not yet at project-creation time. Revisit once
# brand profile capture lands.
PROJECT_SUBDIRS = [
    "sources",
    "captures/raw",
    "captures/events",
    "captures/checkpoints",
    "generated/video",
    "generated/images",
    "audio/voice",
    "audio/music",
    "audio/sfx",
    "proxies",
    "storyboards",
    "revisions",
    "renders/preview",
    "exports/v001",
    "reports",
    "cache",
]


_TR_TRANSLITERATION = str.maketrans(
    {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"}
)


def _slugify(name: str) -> str:
    # Bare regex-stripping would silently drop Turkish letters entirely
    # (e.g. "Örnek" -> "rnek") instead of a readable "ornek" — this app's
    # default locale is tr-TR, so transliterate before stripping non-ASCII.
    transliterated = name.strip().lower().translate(_TR_TRANSLITERATION)
    slug = _SLUG_RE.sub("-", transliterated).strip("-")
    return slug or "project"


def _unique_slug(session: Session, base_slug: str) -> str:
    slug = base_slug
    suffix = 1
    while session.execute(select(Project.id).where(Project.slug == slug)).scalar_one_or_none() is not None:
        suffix += 1
        slug = f"{base_slug}-{suffix}"
    return slug


def create_project(session: Session, *, name: str, locale: str = "tr-TR") -> Project:
    if not name or not name.strip():
        raise ValidationAppError("Project name is required")

    base_slug = _slugify(name)
    slug = _unique_slug(session, base_slug)
    short_id = uuid.uuid4().hex[:8]
    root_path = Path(settings.projects_root) / f"{slug}--{short_id}"

    for sub in PROJECT_SUBDIRS:
        (root_path / sub).mkdir(parents=True, exist_ok=True)

    project = Project(name=name.strip(), slug=slug, root_path=str(root_path), locale=locale)
    session.add(project)
    session.flush()  # assign id/created_at before writing the manifest

    manifest = {
        "schema_version": 1,
        "project_id": project.id,
        "slug": project.slug,
        "name": project.name,
        "created_at": project.created_at.isoformat(),
    }
    (root_path / "project.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    session.commit()
    session.refresh(project)
    return project


def list_projects(session: Session) -> list[Project]:
    return list(session.execute(select(Project).order_by(Project.created_at.desc())).scalars())


def get_project(session: Session, project_id: str) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found", details={"project_id": project_id})
    return project


def update_project(
    session: Session,
    project_id: str,
    *,
    expected_version: int,
    name: str | None = None,
    locale: str | None = None,
    active_revision_id: str | None = None,
) -> Project:
    get_project(session, project_id)  # 404s before we worry about version conflicts

    values: dict = {}
    if name is not None:
        values["name"] = name
    if locale is not None:
        values["locale"] = locale
    if active_revision_id is not None:
        values["active_revision_id"] = active_revision_id

    if not values:
        return get_project(session, project_id)

    values["version"] = Project.version + 1
    result = session.execute(
        update(Project).where(Project.id == project_id, Project.version == expected_version).values(**values)
    )
    if result.rowcount == 0:
        session.rollback()
        current = get_project(session, project_id)
        raise VersionConflictError(
            f"Project {project_id} was modified concurrently "
            f"(expected version {expected_version}, current version {current.version})",
            details={
                "project_id": project_id,
                "expected_version": expected_version,
                "current_version": current.version,
            },
        )
    session.commit()
    return get_project(session, project_id)


_DEFAULT_AUDIENCE = "Genel hedef kitle"


def put_brief(
    session: Session,
    project_id: str,
    *,
    audience: str,
    single_message: str,
    objective: str,
    style_id: str,
    language: str,
    target_frames: int,
    fps_num: int,
    fps_den: int,
    placement_id: str,
    budget_microusd: int,
    product_name: str,
    description: str,
    cta: str,
    destination_url: str | None = None,
) -> Brief:
    """Spec 8.1: `PUT /projects/{id}/brief` always creates a new brief revision.

    Briefs are append-only history — a PUT never mutates an existing row, so
    prior revisions stay available for audit/rollback even after the user
    changes their mind.

    Spec 4.2: the brief screen also collects the brand profile's mandatory
    fields (product_name/description/cta) in the same form; those live in
    the separate `brand_profiles` table (spec 7.2) and are upserted here —
    one row per project, not revisioned like briefs.
    """

    get_project(session, project_id)  # 404 if the project does not exist

    # Spec 3.2: everything but product_name/description/cta "varsayılanla
    # doldurulur" — a blank audience/single_message must not block the save.
    resolved_audience = audience.strip() or _DEFAULT_AUDIENCE
    resolved_single_message = single_message.strip() or description.strip()

    next_revision = (
        session.execute(
            select(func.coalesce(func.max(Brief.revision), 0)).where(Brief.project_id == project_id)
        ).scalar_one()
        + 1
    )
    brief = Brief(
        project_id=project_id,
        revision=next_revision,
        audience=resolved_audience,
        single_message=resolved_single_message,
        objective=objective,
        style_id=style_id,
        language=language,
        target_frames=target_frames,
        fps_num=fps_num,
        fps_den=fps_den,
        placement_id=placement_id,
        budget_microusd=budget_microusd,
    )
    session.add(brief)

    brand_profile = session.execute(
        select(BrandProfile).where(BrandProfile.project_id == project_id)
    ).scalar_one_or_none()
    if brand_profile is None:
        brand_profile = BrandProfile(project_id=project_id)
        session.add(brand_profile)
    brand_profile.product_name = product_name
    brand_profile.description = description
    brand_profile.cta = cta
    brand_profile.destination_url = destination_url or None

    session.commit()
    session.refresh(brief)
    return brief


def get_latest_brief(session: Session, project_id: str) -> Brief | None:
    return (
        session.execute(
            select(Brief).where(Brief.project_id == project_id).order_by(Brief.revision.desc())
        )
        .scalars()
        .first()
    )
