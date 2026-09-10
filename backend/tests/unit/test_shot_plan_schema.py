import pytest
from pydantic import ValidationError

from app.schemas.shot_plan import ShotPlan


def _shot(id_: str, frames: int) -> dict:
    return {
        "id": id_,
        "source_type": "gameplay",
        "purpose": "test",
        "target_frames": frames,
        "success_predicate": {"required_observations": ["ok"], "evidence_required": True},
    }


def test_valid_plan_with_frames_summing_to_target():
    plan = ShotPlan(
        schema_version=1,
        fps={"num": 30, "den": 1},
        target_frames=600,
        shots=[_shot("s1", 300), _shot("s2", 300)],
    )
    assert len(plan.shots) == 2


def test_plan_rejects_frame_total_beyond_one_frame_tolerance():
    with pytest.raises(ValidationError):
        ShotPlan(
            schema_version=1,
            fps={"num": 30, "den": 1},
            target_frames=600,
            shots=[_shot("s1", 300), _shot("s2", 280)],
        )


def test_plan_allows_one_frame_rounding_tolerance():
    plan = ShotPlan(
        schema_version=1,
        fps={"num": 30, "den": 1},
        target_frames=600,
        shots=[_shot("s1", 300), _shot("s2", 299)],
    )
    assert sum(s.target_frames for s in plan.shots) == 599
