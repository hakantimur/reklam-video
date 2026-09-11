from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.diagnostics import run_diagnostics
from app.jobs.worker import is_running as worker_is_running

router = APIRouter(tags=["health"])


@router.get("/health")
def health(session: Session = Depends(get_session)) -> dict:
    db_ok = True
    db_error = None
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - report, don't crash the health check
        db_ok = False
        db_error = str(exc)

    diagnostics = run_diagnostics()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": {"ok": db_ok, "error": db_error},
        "disk": diagnostics["disk"],
        "worker": {"status": "running" if worker_is_running() else "not_started"},
    }


@router.get("/diagnostics")
def diagnostics() -> dict:
    return run_diagnostics()
