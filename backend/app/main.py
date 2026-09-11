from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import ROUTERS as CORE_ROUTERS
from app.api.devices import router as devices_router
from app.api.health import router as health_router
from app.api.providers import router as providers_router
from app.jobs.worker import start_background_worker
from app.security.local_origin import LocalOriginMiddleware

_WEB_DIST = Path(__file__).resolve().parents[2] / "apps" / "web" / "dist"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Spec §6.2: FastAPI itself must not run long jobs; a background thread
    # actually consumes the job queue that app/jobs/handlers.py defines.
    start_background_worker()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Local Ad Director API", version="0.1.0", lifespan=_lifespan)
    app.add_middleware(LocalOriginMiddleware)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(devices_router, prefix="/api/v1")
    app.include_router(providers_router, prefix="/api/v1")
    for router in CORE_ROUTERS:
        app.include_router(router, prefix="/api/v1")

    # Spec 20.2: the built UI is served by FastAPI in normal use; a Vite dev
    # server is only needed while actively developing the frontend. Registered
    # last so /api/v1/* always takes priority. A plain StaticFiles(html=True)
    # mount only serves index.html for "/" itself, not for client-side routes
    # like /studyo/senaryo — those need an explicit SPA fallback, otherwise a
    # bookmark or refresh on any sub-route 404s instead of loading the app.
    if _WEB_DIST.is_dir():
        index_path = _WEB_DIST / "index.html"
        app.mount("/assets", StaticFiles(directory=_WEB_DIST / "assets"), name="web-assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def serve_spa(full_path: str) -> FileResponse:
            candidate = _WEB_DIST / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index_path)

    return app


app = create_app()
