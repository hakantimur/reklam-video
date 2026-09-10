from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import ROUTERS as CORE_ROUTERS
from app.api.devices import router as devices_router
from app.api.health import router as health_router
from app.api.providers import router as providers_router
from app.security.local_origin import LocalOriginMiddleware

_WEB_DIST = Path(__file__).resolve().parents[2] / "apps" / "web" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="Local Ad Director API", version="0.1.0")
    app.add_middleware(LocalOriginMiddleware)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(devices_router, prefix="/api/v1")
    app.include_router(providers_router, prefix="/api/v1")
    for router in CORE_ROUTERS:
        app.include_router(router, prefix="/api/v1")

    # Spec 20.2: the built UI is served by FastAPI in normal use; a Vite dev
    # server is only needed while actively developing the frontend. Mounted
    # last and only if a build exists, so /api/v1/* always takes priority.
    if _WEB_DIST.is_dir():
        app.mount("/", StaticFiles(directory=_WEB_DIST, html=True), name="web")

    return app


app = create_app()
