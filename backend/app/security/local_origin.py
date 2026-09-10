from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

_ALLOWED_HOSTS = {f"{settings.host}:{settings.port}", "127.0.0.1", "localhost"}

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class LocalOriginMiddleware(BaseHTTPMiddleware):
    """Rejects cross-origin mutations against the loopback-only backend.

    Spec 20.1: no CORS wildcard; Host/Origin must be validated on mutating
    requests so no foreign web page can drive this local API via the
    browser's ambient session.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method not in _SAFE_METHODS:
            host = (request.headers.get("host") or "").split(",")[0].strip()
            origin = request.headers.get("origin")
            host_ok = host.split(":")[0] in {"127.0.0.1", "localhost"}
            origin_ok = origin is None or origin.split("//")[-1].split(":")[0] in {
                "127.0.0.1",
                "localhost",
            }
            if not (host_ok and origin_ok):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "origin_rejected",
                            "message": "Cross-origin request rejected",
                            "retryable": False,
                            "details": {},
                            "job_id": None,
                        }
                    },
                )
        return await call_next(request)
