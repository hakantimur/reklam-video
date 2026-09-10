from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.errors import error_response
from app.core.db import get_session
from app.schemas.project import ProjectCreate, ProjectListOut, ProjectOut, ProjectUpdate
from app.services import projects as projects_service
from app.services.errors import ServiceError

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=ProjectListOut)
def list_projects(session: Session = Depends(get_session)):
    items = projects_service.list_projects(session)
    return ProjectListOut(items=[ProjectOut.model_validate(p) for p in items])


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, session: Session = Depends(get_session)):
    try:
        project = projects_service.create_project(session, name=body.name, locale=body.locale)
    except ServiceError as exc:
        return error_response(exc)
    return ProjectOut.model_validate(project)


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, session: Session = Depends(get_session)):
    try:
        project = projects_service.get_project(session, project_id)
    except ServiceError as exc:
        return error_response(exc)
    return ProjectOut.model_validate(project)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, body: ProjectUpdate, session: Session = Depends(get_session)):
    try:
        project = projects_service.update_project(
            session,
            project_id,
            expected_version=body.version,
            name=body.name,
            locale=body.locale,
            active_revision_id=body.active_revision_id,
        )
    except ServiceError as exc:
        return error_response(exc)
    return ProjectOut.model_validate(project)
