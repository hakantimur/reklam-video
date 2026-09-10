from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    locale: str = Field(default="tr-TR", max_length=10)


class ProjectUpdate(BaseModel):
    """Spec 7.1: any mutation must carry the `version` the client last saw.

    A stale `version` must 409 rather than silently overwrite concurrent
    changes, so this is required on every PATCH, even one that only touches
    a single field.
    """

    version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    locale: str | None = Field(default=None, max_length=10)
    active_revision_id: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    root_path: str
    locale: str
    active_revision_id: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class ProjectListOut(BaseModel):
    items: list[ProjectOut]
