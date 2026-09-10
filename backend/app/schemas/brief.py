from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BriefPut(BaseModel):
    """Body of `PUT /projects/{id}/brief`.

    Every PUT creates a *new* brief revision (spec 8.1) — briefs are
    append-only history, never edited in place.
    """

    # Spec 4.2/3.2: only product_name/description/cta are truly mandatory on
    # the brief screen; everything else is "varsayılanla doldurulur" (filled
    # with a default) rather than blocking the save. audience/single_message
    # therefore accept blank input here — `put_brief` substitutes a real
    # default before the row is written, so the *stored* Brief still always
    # has meaningful, non-empty creative fields.
    audience: str = Field(default="", max_length=500)
    single_message: str = Field(default="", max_length=500)
    objective: str = Field(min_length=1, max_length=200)
    style_id: str = Field(min_length=1, max_length=100)
    language: str = Field(default="tr", max_length=10)
    target_frames: int = Field(ge=1)
    fps_num: int = Field(default=30, ge=1)
    fps_den: int = Field(default=1, ge=1)
    placement_id: str = Field(min_length=1, max_length=100)
    budget_microusd: int = Field(ge=0)

    # Spec 4.2: the brief screen also captures the brand profile's mandatory
    # fields in the same form. product_name/description/cta are required;
    # `put_brief` upserts a `brand_profiles` row alongside the new revision.
    product_name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    cta: str = Field(min_length=1, max_length=200)
    destination_url: str | None = Field(default=None, max_length=2000)


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
