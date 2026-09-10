from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_projects_root() -> str:
    documents = Path.home() / "Documents"
    return str(documents / "LocalAdDirector" / "Projects")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LAD_", env_file=".env")

    host: str = "127.0.0.1"
    port: int = 8765

    projects_root: str = _default_projects_root()
    app_db_filename: str = "app.sqlite3"

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    elevenlabs_base_url: str = "https://api.elevenlabs.io/v1"

    catalog_cache_hours: int = 24
    job_heartbeat_seconds: int = 5
    job_lease_seconds: int = 30
    provider_poll_interval_seconds: int = 30


settings = Settings()
