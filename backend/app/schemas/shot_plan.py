from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Fps(BaseModel):
    num: int = Field(ge=1)
    den: int = Field(ge=1)


class HandlesFrames(BaseModel):
    before: int = Field(default=0, ge=0)
    after: int = Field(default=0, ge=0)


class SuccessPredicate(BaseModel):
    required_observations: list[str] = Field(default_factory=list)
    evidence_required: bool = True


class ActionConstraints(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=3)
    max_seconds: int = Field(default=60, ge=1)


class ShotLocks(BaseModel):
    visual: bool = False
    voice: bool = False
    caption: bool = False
    timing: bool = False


class Shot(BaseModel):
    id: str
    source_type: Literal["gameplay", "ai_generated", "composed"]
    purpose: str
    target_frames: int = Field(ge=1)
    handles_frames: HandlesFrames = Field(default_factory=HandlesFrames)
    start_state: dict = Field(default_factory=dict)
    desired_event: str | None = None
    success_predicate: SuccessPredicate
    action_constraints: ActionConstraints = Field(default_factory=ActionConstraints)
    caption: str | None = None
    voice_text: str | None = None
    fallback: str | None = None
    locks: ShotLocks = Field(default_factory=ShotLocks)


class ShotPlan(BaseModel):
    schema_version: Literal[1] = 1
    fps: Fps
    target_frames: int = Field(ge=1)
    shots: list[Shot] = Field(min_length=1)

    @model_validator(mode="after")
    def frames_must_sum_to_target(self) -> "ShotPlan":
        total = sum(s.target_frames for s in self.shots)
        # Spec 3.2: plan total duration tolerance is at most 1 timeline frame.
        if abs(total - self.target_frames) > 1:
            raise ValueError(
                f"sum(shot.target_frames)={total} exceeds 1-frame tolerance of "
                f"target_frames={self.target_frames}"
            )
        return self
