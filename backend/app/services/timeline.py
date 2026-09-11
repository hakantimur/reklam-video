"""Spec §16.1/§21 Safha 9: assemble a real Timeline JSON
(packages/contracts/timeline.schema.json) from a Revision's Shots and their
selected Takes / voice-over Assets.

A shot with no take yet is still emitted as a video track item, just with
`asset_id: null` — the Remotion composition's existing placeholder rendering
is what shows for it (spec's "never silently pass a placeholder off as
final" behavior belongs to the renderer, not this assembly step).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.creative import Shot, Take
from app.services import plans as plans_service
from app.services import projects as projects_service
from app.services.errors import ValidationAppError

# Spec §7.2 doesn't record a canvas size anywhere yet (placement_id -> aspect
# ratio mapping is not implemented) — a 9:16 vertical canvas is the sane
# default for the ad formats this app targets, applied uniformly for now.
DEFAULT_CANVAS = {"width": 1080, "height": 1920}


def selected_or_best_take(session: Session, shot: Shot) -> Take | None:
    if shot.selected_take_id:
        take = session.get(Take, shot.selected_take_id)
        if take is not None:
            return take
    return (
        session.execute(
            select(Take)
            .where(Take.shot_id == shot.id, Take.status != "rejected")
            .order_by(Take.attempt.desc())
        )
        .scalars()
        .first()
    )


def _voice_asset_for_shot(session: Session, project_id: str, shot_id: str) -> Asset | None:
    return (
        session.execute(
            select(Asset)
            .where(
                Asset.project_id == project_id,
                Asset.type == "audio",
                func.json_extract(Asset.metadata_json, "$.shot_id") == shot_id,
                func.json_extract(Asset.metadata_json, "$.role") == "voice_over",
            )
            .order_by(Asset.created_at.desc())
        )
        .scalars()
        .first()
    )


def build_timeline(session: Session, project_id: str) -> dict:
    revision = plans_service.get_latest_revision(session, project_id)
    if revision is None:
        raise ValidationAppError(
            "Timeline oluşturmadan önce bir çekim planı üretilmelidir.", details={"project_id": project_id}
        )

    shots = plans_service.get_shots_for_revision(session, revision.id)
    if not shots:
        raise ValidationAppError("Bu revizyonda hiç sahne yok.", details={"revision_id": revision.id})

    brief = projects_service.get_latest_brief(session, project_id)
    fps_num = brief.fps_num if brief else 30
    fps_den = brief.fps_den if brief else 1

    video_items: list[dict] = []
    voice_items: list[dict] = []
    subtitle_items: list[dict] = []
    cursor = 0

    for shot in shots:
        start = cursor
        duration = shot.target_frames
        take = selected_or_best_take(session, shot)
        locks = shot.locks_json or {}
        voice_asset = _voice_asset_for_shot(session, project_id, shot.id)

        video_items.append(
            {
                "id": f"video-{shot.id}",
                "shot_id": shot.id,
                "asset_id": take.asset_id if take else None,
                "start_frame": start,
                "duration_frames": duration,
                "source_in_us": take.in_us if take else None,
                "transform": {
                    "placeholderLabel": shot.purpose,
                    # Spec §16 audio ducking: a shot's own clip audio must
                    # not fight a voice-over reading over it — the two are
                    # always the same start/duration (see the voice item
                    # below), so this is a per-item decision, not a
                    # per-frame envelope.
                    "hasVoiceOver": voice_asset is not None,
                },
                "opacity": 1,
                "lock": bool(locks.get("visual")),
            }
        )

        if voice_asset is not None:
            voice_items.append(
                {
                    "id": f"voice-{shot.id}",
                    "shot_id": shot.id,
                    "asset_id": voice_asset.id,
                    "start_frame": start,
                    "duration_frames": duration,
                    "gain": 1.0,
                    "lock": bool(locks.get("voice")),
                }
            )

        if shot.caption_text:
            subtitle_items.append(
                {
                    "id": f"caption-{shot.id}",
                    "shot_id": shot.id,
                    "start_frame": start,
                    "duration_frames": duration,
                    "transform": {"captionText": shot.caption_text},
                    "lock": bool(locks.get("caption")),
                }
            )

        cursor += duration

    timeline = {
        "schema_version": 1,
        "revision_id": revision.id,
        "fps": {"num": fps_num, "den": fps_den},
        "duration_frames": cursor,
        "canvas": DEFAULT_CANVAS,
        "tracks": [
            {"id": "video", "kind": "video", "items": video_items},
            {"id": "voice", "kind": "audio", "items": voice_items},
            {"id": "captions", "kind": "subtitle", "items": subtitle_items},
        ],
    }

    revision.timeline_json = timeline
    session.commit()
    return timeline
