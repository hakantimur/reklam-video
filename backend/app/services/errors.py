"""Service-layer exceptions mapped 1:1 onto the API error envelope.

Spec 8.1 fixes the error shape as::

    {"error": {"code", "message", "retryable", "details", "job_id"}}

Because `app/main.py` is off-limits to this round of work (the app factory
is wired up by the integration owner), we cannot register a global FastAPI
exception handler there. Instead every service raises one of these typed
errors, and every API route catches `ServiceError` once and renders it with
`app.api.errors.error_response`, so the envelope is correct regardless of
how the routers eventually get mounted.
"""

from __future__ import annotations


class ServiceError(Exception):
    code = "internal_error"
    status_code = 500
    retryable = False

    def __init__(self, message: str, *, details: dict | None = None, job_id: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.job_id = job_id


class NotFoundError(ServiceError):
    code = "not_found"
    status_code = 404


class ValidationAppError(ServiceError):
    code = "validation_error"
    status_code = 422


class VersionConflictError(ServiceError):
    """Spec 7.1: stale `version` on a mutating write must 409, never merge silently."""

    code = "version_conflict"
    status_code = 409


class ConflictError(ServiceError):
    code = "conflict"
    status_code = 409


class BlockedError(ServiceError):
    """Spec 8.2 `blocked` job state: missing credentials/device/budget etc."""

    code = "blocked"
    status_code = 409
    retryable = True
