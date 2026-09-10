"""Asset upload and lookup (spec 7.4, 20.1).

Upload contract: stream the multipart body to a `.partial` sibling file
while hashing it, only `os.replace` it into its final name once the whole
body has landed cleanly, and only then create the DB row. A half-written
upload (client disconnect, crash, disk full) can never become a usable
asset, because the DB row and the final filename both come into existence
atomically together, after the bytes are already safely on disk.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import ASSET_ORIGINS, ASSET_TYPES, Asset
from app.services.errors import NotFoundError, ValidationAppError
from app.services.projects import get_project

_CHUNK_SIZE = 1024 * 1024
_DEFAULT_MAX_BYTES = 20 * 1024 * 1024 * 1024  # 20 GiB safety ceiling (spec 20.1: reject oversize uploads)

# Where each asset type lands inside the project directory (spec 7.3 layout).
_TYPE_SUBDIR = {
    "video": "sources",
    "image": "sources",
    "audio": "sources",
    "subtitle": "sources",
    "storyboard": "storyboards",
    "proxy": "proxies",
    "export": "exports/v001",
    "evidence": "captures/events",
}


def _safe_filename(filename: str | None) -> str:
    """Strip any directory components from a client-supplied filename.

    This is the path-traversal / zip-slip guard called for in spec 20.1: a
    filename like `../../../etc/passwd` or `C:\\Windows\\x` must never be
    able to escape the target asset subdirectory. `Path(...).name` collapses
    it to the last path segment only.
    """

    name = Path((filename or "upload.bin").replace("\x00", "")).name
    if not name or name in {".", ".."}:
        name = "upload.bin"
    return name


async def save_uploaded_asset(
    session: Session,
    project_id: str,
    upload: UploadFile,
    *,
    asset_type: str,
    origin: str,
    max_bytes: int = _DEFAULT_MAX_BYTES,
) -> Asset:
    if asset_type not in ASSET_TYPES:
        raise ValidationAppError(
            f"Unknown asset type '{asset_type}'", details={"allowed": list(ASSET_TYPES)}
        )
    if origin not in ASSET_ORIGINS:
        raise ValidationAppError(
            f"Unknown asset origin '{origin}'", details={"allowed": list(ASSET_ORIGINS)}
        )

    project = get_project(session, project_id)
    target_dir = Path(project.root_path) / _TYPE_SUBDIR.get(asset_type, "sources")
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_filename(upload.filename)
    final_path = target_dir / safe_name
    if final_path.exists():
        # Never silently overwrite a same-named asset; disambiguate instead.
        final_path = target_dir / f"{uuid.uuid4().hex[:8]}-{safe_name}"
    partial_path = final_path.with_name(final_path.name + ".partial")

    sha256 = hashlib.sha256()
    byte_size = 0
    try:
        with open(partial_path, "wb") as out:
            while True:
                chunk = await upload.read(_CHUNK_SIZE)
                if not chunk:
                    break
                byte_size += len(chunk)
                if byte_size > max_bytes:
                    raise ValidationAppError(
                        "Uploaded file exceeds the maximum allowed size",
                        details={"max_bytes": max_bytes},
                    )
                sha256.update(chunk)
                out.write(chunk)
        if byte_size == 0:
            raise ValidationAppError("Uploaded file is empty")
    except Exception:
        partial_path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    # Atomic rename: only a fully written, validated file ever gets the final name.
    os.replace(partial_path, final_path)

    relative_path = str(final_path.relative_to(Path(project.root_path)))
    asset = Asset(
        project_id=project.id,
        type=asset_type,
        origin=origin,
        relative_path=relative_path,
        sha256=sha256.hexdigest(),
        byte_size=byte_size,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def list_assets(
    session: Session,
    project_id: str,
    *,
    type: str | None = None,
    origin: str | None = None,
    text: str | None = None,
) -> list[Asset]:
    get_project(session, project_id)  # 404 for an unknown project rather than an empty list

    query = select(Asset).where(Asset.project_id == project_id)
    if type is not None:
        query = query.where(Asset.type == type)
    if origin is not None:
        query = query.where(Asset.origin == origin)
    if text:
        query = query.where(Asset.relative_path.contains(text))
    query = query.order_by(Asset.created_at.desc())
    return list(session.execute(query).scalars())


def get_asset(session: Session, asset_id: str) -> Asset:
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError(f"Asset {asset_id} not found", details={"asset_id": asset_id})
    return asset


def resolve_asset_path(session: Session, asset_id: str) -> tuple[Asset, Path]:
    """Resolve an asset id to its absolute on-disk path for `GET /assets/{id}/content`.

    The asset endpoint must never accept an arbitrary filesystem path from
    the client (spec 20.1) — only an opaque asset id, resolved server-side
    against the owning project's root and the asset's own stored relative
    path (itself already sanitized at upload time).
    """

    asset = get_asset(session, asset_id)
    project = get_project(session, asset.project_id)
    path = Path(project.root_path) / asset.relative_path
    if not path.is_file():
        raise NotFoundError(
            f"Asset {asset_id} file is missing on disk", details={"asset_id": asset_id, "path": str(path)}
        )
    return asset, path
