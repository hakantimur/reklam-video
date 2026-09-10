from fastapi import FastAPI

from app.api.health import router as health_router
from app.security.local_origin import LocalOriginMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="Local Ad Director API", version="0.1.0")
    app.add_middleware(LocalOriginMiddleware)
    app.include_router(health_router, prefix="/api/v1")
    return app


app = create_app()
