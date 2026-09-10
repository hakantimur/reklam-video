from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.shot_plan import Fps


class Canvas(BaseModel):
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class TrackItem(BaseModel):
    id: str
    shot_id: str | None = None
    asset_id: str | None = None
    start_frame: int = Field(ge=0)
    duration_frames: int = Field(ge=1)
    source_in_us: int | None = Field(default=None, ge=0)
    transform: dict = Field(default_factory=dict)
    opacity: float = Field(default=1.0, ge=0, le=1)
    gain: float = 1.0
    lock: bool = False


class Track(BaseModel):
    id: str
    kind: Literal["video", "graphics", "audio", "subtitle"]
    items: list[TrackItem] = Field(default_factory=list)


class Timeline(BaseModel):
    schema_version: Literal[1] = 1
    revision_id: str
    fps: Fps
    duration_frames: int = Field(ge=1)
    canvas: Canvas
    tracks: list[Track] = Field(default_factory=list)
