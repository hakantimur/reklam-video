"""Spec §16/§21 Safha 9: turn a built Timeline into a real MP4.

Stages every track item's referenced Asset into `apps/render/public/`
(Remotion's documented way to serve local files to a composition via
`staticFile()`), then invokes the existing `apps/render` Remotion project
as a subprocess — the same `AdComposition` already contract-verified to
render a placeholder-only MP4 in the first Safha 9 pass, now fed real
files via each track item's `transform.realFile`.

`app.services.export` reuses `render_timeline_to_asset` (Safha 11) for the
QA-gated final export — same render mechanics, different output directory
and Asset type/origin.
"""

import hashlib
import json
import shutil
import subprocess
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.media import technical_qc
from app.models.asset import Asset
from app.services import assets as assets_service
from app.services import projects as projects_service
from app.services import timeline as timeline_service
from app.services.errors import ServiceError

RENDER_APP_DIR = Path(__file__).resolve().parents[3] / "apps" / "render"
PUBLIC_DIR = RENDER_APP_DIR / "public"
RENDER_TIMEOUT_S = 600.0


class RenderError(ServiceError):
    code = "render_failed"
    status_code = 500


def stage_asset(session: Session, asset_id: str, item_id: str) -> str:
    _, path = assets_service.resolve_asset_path(session, asset_id)
    filename = f"{item_id}{path.suffix}"
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, PUBLIC_DIR / filename)
    return filename


def render_timeline_to_asset(
    session: Session,
    project_id: str,
    *,
    output_dir_name: str,
    filename_prefix: str,
    asset_type: str,
    extra_metadata: dict | None = None,
) -> Asset:
    project = projects_service.get_project(session, project_id)
    timeline = timeline_service.build_timeline(session, project_id)

    for track in timeline["tracks"]:
        for item in track["items"]:
            asset_id = item.get("asset_id")
            if not asset_id:
                continue
            filename = stage_asset(session, asset_id, item["id"])
            item.setdefault("transform", {})["realFile"] = filename

    output_dir = Path(project.root_path) / output_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{filename_prefix}-{uuid.uuid4().hex[:8]}.mp4"

    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx is None:
        raise RenderError("npx bulunamadı; Node.js kurulumu kontrol edilmeli.")

    props_path = RENDER_APP_DIR / f".props-{uuid.uuid4().hex[:8]}.json"
    props_path.write_text(json.dumps({"timeline": timeline}, ensure_ascii=False), encoding="utf-8")
    try:
        result = subprocess.run(
            [npx, "remotion", "render", "src/index.ts", "AdComposition", str(output_path), f"--props={props_path}"],
            cwd=str(RENDER_APP_DIR),
            capture_output=True,
            text=True,
            timeout=RENDER_TIMEOUT_S,
            shell=False,
        )
    finally:
        props_path.unlink(missing_ok=True)

    if result.returncode != 0 or not output_path.exists():
        tail = (result.stderr or result.stdout or "")[-2000:]
        raise RenderError(f"Remotion render başarısız: {tail}")

    report = technical_qc.run_technical_qc(output_path)
    digest = hashlib.sha256()
    with output_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    duration_us = int(report.probe.duration_s * 1_000_000) if report.probe else None
    metadata = {
        "technical_qc": {"outcome": report.outcome, "checks": report.checks, "errors": report.errors},
        "timeline_revision_id": timeline["revision_id"],
    }
    metadata.update(extra_metadata or {})

    asset = Asset(
        project_id=project_id,
        type=asset_type,
        origin="derived",
        relative_path=str(output_path.relative_to(Path(project.root_path))),
        sha256=digest.hexdigest(),
        byte_size=output_path.stat().st_size,
        duration_us=duration_us,
        dimensions_json={"width": report.probe.width, "height": report.probe.height} if report.probe else {},
        metadata_json=metadata,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def render_preview_job(session: Session, project_id: str) -> Asset:
    return render_timeline_to_asset(
        session, project_id, output_dir_name="renders/preview", filename_prefix="preview", asset_type="proxy"
    )
