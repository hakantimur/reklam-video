"""Take listing/selection (spec §7.2 `shots.selected_take_id`) — read/write
side of the capture pipeline in `app.services.capture`."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.creative import Revision, Shot, Take
from app.services.errors import NotFoundError


def _get_shot_in_project(session: Session, project_id: str, shot_id: str) -> Shot:
    shot = session.get(Shot, shot_id)
    if shot is None:
        raise NotFoundError(f"Shot {shot_id} not found", details={"shot_id": shot_id})
    revision = session.get(Revision, shot.revision_id)
    if revision is None or revision.project_id != project_id:
        raise NotFoundError(f"Shot {shot_id} not found for this project", details={"shot_id": shot_id})
    return shot


def list_takes_for_shot(session: Session, project_id: str, shot_id: str) -> list[Take]:
    _get_shot_in_project(session, project_id, shot_id)
    return list(
        session.execute(select(Take).where(Take.shot_id == shot_id).order_by(Take.attempt)).scalars().all()
    )


def select_take(session: Session, project_id: str, shot_id: str, take_id: str) -> Shot:
    shot = _get_shot_in_project(session, project_id, shot_id)
    take = session.get(Take, take_id)
    if take is None or take.shot_id != shot_id:
        raise NotFoundError(f"Take {take_id} not found for shot {shot_id}", details={"take_id": take_id})
    shot.selected_take_id = take.id
    session.commit()
    session.refresh(shot)
    return shot
