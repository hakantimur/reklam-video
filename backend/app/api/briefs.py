from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.errors import error_response
from app.core.db import get_session
from app.schemas.brief import BriefOut, BriefPut
from app.services import projects as projects_service
from app.services.errors import ServiceError

router = APIRouter(tags=["briefs"])


@router.put("/projects/{project_id}/brief", response_model=BriefOut, status_code=201)
def put_brief(project_id: str, body: BriefPut, session: Session = Depends(get_session)):
    try:
        brief = projects_service.put_brief(
            session,
            project_id,
            audience=body.audience,
            single_message=body.single_message,
            objective=body.objective,
            style_id=body.style_id,
            language=body.language,
            target_frames=body.target_frames,
            fps_num=body.fps_num,
            fps_den=body.fps_den,
            placement_id=body.placement_id,
            budget_microusd=body.budget_microusd,
        )
    except ServiceError as exc:
        return error_response(exc)
    return BriefOut.model_validate(brief)
