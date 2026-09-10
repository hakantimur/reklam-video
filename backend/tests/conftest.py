import os
import tempfile

# Must run before any `app.core.config` import (module-level Settings()).
os.environ.setdefault("LAD_PROJECTS_ROOT", os.path.join(tempfile.gettempdir(), "lad_test_projects"))

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def _migrated_test_db():
    """Run the real Alembic migration chain against the test SQLite file
    once per test session, so tests exercise the same schema production
    would get — rather than a parallel `Base.metadata.create_all()` that
    could silently drift from what `alembic upgrade head` actually does.
    """

    backend_dir = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_dir / "alembic.ini"))
    command.upgrade(cfg, "head")


@pytest.fixture()
def db_session():
    from app.core.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def api_client() -> TestClient:
    """A FastAPI app carrying only this round's routers (projects, briefs,
    assets, jobs, settings, events) plus the same loopback-origin guard
    `app.main` uses. `app.main.app` itself is not touched by this round of
    work — the coordinator wires these routers into it separately — so
    tests that need to exercise the HTTP layer build their own tiny app
    here instead of importing `app.main`.
    """

    from app.api import ROUTERS
    from app.security.local_origin import LocalOriginMiddleware

    test_app = FastAPI()
    test_app.add_middleware(LocalOriginMiddleware)
    for router in ROUTERS:
        test_app.include_router(router, prefix="/api/v1")
    # LocalOriginMiddleware (spec 20.1) rejects mutating requests whose Host
    # header isn't 127.0.0.1/localhost — TestClient's default "testserver"
    # base_url would otherwise get every POST/PATCH/PUT rejected with 403.
    return TestClient(test_app, base_url="http://127.0.0.1")
