from pydantic import BaseModel


class DeviceSummary(BaseModel):
    serial: str
    state: str
    model: str | None = None
    width: int | None = None
    height: int | None = None
    orientation: int | None = None


class PreflightResult(BaseModel):
    serial: str
    screenshot_ok: bool
    touch_ok: bool
    recording_ok: bool
    audio_detected: bool | None = None
    errors: list[str] = []
