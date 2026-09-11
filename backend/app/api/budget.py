from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.services import budget as budget_service

router = APIRouter(tags=["budget"])


class BudgetSummaryOut(BaseModel):
    user_cap_microusd: int | None
    settled_cost_microusd: int
    active_reservations_microusd: int
    available_microusd: int | None


@router.get("/projects/{project_id}/budget", response_model=BudgetSummaryOut)
def get_budget(project_id: str, session: Session = Depends(get_session)):
    """Spec §19.1: `available = user_cap - settled_cost - active_reservations`.
    Real settlements (see `app.jobs.handlers._settle_llm_cost` /
    `_settle_generation_cost`) have been accumulating in `BudgetEntry`
    since earlier this session with nothing to read them back — this is
    that read side."""

    summary = budget_service.get_budget_summary(session, project_id)
    return BudgetSummaryOut(**summary.as_dict())
