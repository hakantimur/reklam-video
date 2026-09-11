from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.errors import error_response
from app.core.db import get_session
from app.services import qa as qa_service
from app.services.errors import ServiceError

router = APIRouter(tags=["qa"])


class QAReportOut(BaseModel):
    revision_id: str
    passed: bool
    issues: list[str]


@router.get("/projects/{project_id}/revisions/{revision_id}/qa", response_model=QAReportOut)
def get_revision_qa(project_id: str, revision_id: str, session: Session = Depends(get_session)):
    try:
        report = qa_service.run_revision_qa(session, project_id, revision_id)
    except ServiceError as exc:
        return error_response(exc)
    return QAReportOut(revision_id=report.revision_id, passed=report.passed, issues=report.issues)
