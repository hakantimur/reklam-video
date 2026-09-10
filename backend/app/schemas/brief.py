from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BriefPut(BaseModel):
    """Body of `PUT /projects/{id}/brief`.

    Every PUT creates a *new* brief revision (spec 8.1) — briefs are
    append-only history, never edited in place.
    """

    audience: str = Field(min_length=1, max_length=500)
    single_message: str = Field(min_length=1, max_length=500)
    objective: str = Field(min_length=1, max_length=200)
    style_id: str = Field(min_length=1, max_length=100)
    language: str = Field(default="tr", max_length=10)
    target_frames: int = Field(ge=1)
    fps_num: int = Field(default=30, ge=1)
    fps_den: int = Field(default=1, ge=1)
    placement_id: str = Field(min_length=1, max_length=100)
    budget_microusd: int = Field(ge=0)


class BriefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    revision: int
    audience: str
    single_message: str
    objective: str
    style_id: str
    language: str
    target_frames: int
    fps_num: int
    fps_den: int
    placement_id: str
    budget_microusd: int
    created_at: datetime
