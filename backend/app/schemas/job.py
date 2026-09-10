from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    revision_id: str | None
    kind: str
    state: str
    payload_json: dict
    result_json: dict
    idempotency_key: str
    attempt: int
    error_code: str | None
    lease_owner: str | None
    created_at: datetime
    updated_at: datetime


class JobAcceptedOut(BaseModel):
    """Spec 8.1: long-running operations answer 202 with this shape."""

    job_id: str
    revision_id: str | None
    state: str
