"""Renders `ServiceError` into the exact envelope required by spec 8.1:

    {"error": {"code", "message", "retryable", "details", "job_id"}}

`app/main.py` is off-limits this round, so there is no global FastAPI
exception handler to lean on — every route in this package catches
`ServiceError` itself and calls `error_response`. See
`app/services/errors.py` for why.
"""

from __future__ import annotations

from fastapi.responses import JSONResponse

from app.services.errors import ServiceError


def error_response(exc: ServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "retryable": exc.retryable,
                "details": exc.details,
                "job_id": exc.job_id,
            }
        },
    )
