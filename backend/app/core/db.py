from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _db_path() -> Path:
    root = Path(settings.projects_root)
    root.mkdir(parents=True, exist_ok=True)
    return root / settings.app_db_filename


def make_engine():
    engine = create_engine(f"sqlite:///{_db_path()}", future=True)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        # SQLite's own default busy_timeout is 0: a writer that can't grab
        # the (single, even under WAL) write lock immediately fails on the
        # spot with "database is locked" instead of waiting. This app has
        # a background job worker thread writing continuously alongside
        # API requests — found live via a real 500 on a multi-row write
        # (POST .../variation) that succeeded on an immediate retry with no
        # code change. 5s gives a concurrent writer time to finish instead
        # of surfacing a spurious failure to the user.
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    return engine


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
