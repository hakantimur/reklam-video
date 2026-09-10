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
