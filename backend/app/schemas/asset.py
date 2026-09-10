from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    type: str
    origin: str
    relative_path: str
    sha256: str
    byte_size: int
    duration_us: int | None
    timebase_json: dict
    dimensions_json: dict
    audio_info_json: dict
    metadata_json: dict
    created_at: datetime


class AssetListOut(BaseModel):
    items: list[AssetOut]
