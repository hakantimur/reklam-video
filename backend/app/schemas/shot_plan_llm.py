"""Hand-written JSON Schema for ShotPlan, used as the LLM `response_format`.

OpenRouter/OpenAI-style strict structured outputs require every property to
be listed in `required` (optional fields are modeled as nullable types, not
omitted) and `additionalProperties: false` on every object — Pydantic's
auto-generated `model_json_schema()` does neither by default and uses
`$ref`/`$defs`, which is less reliably supported across providers than a
fully inlined schema. This mirrors `app/schemas/shot_plan.py`'s ShotPlan
exactly; `ShotPlan.model_validate(...)` is still the source of truth for
validation after the call returns.
"""

SHOT_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "source_type": {"type": "string", "enum": ["gameplay", "ai_generated", "composed"]},
        "purpose": {"type": "string"},
        "target_frames": {"type": "integer", "minimum": 1},
        "handles_frames": {
            "type": "object",
            "properties": {
                "before": {"type": "integer", "minimum": 0},
                "after": {"type": "integer", "minimum": 0},
            },
            "required": ["before", "after"],
            "additionalProperties": False,
        },
        "start_state": {"type": "object", "additionalProperties": True},
        "desired_event": {"type": ["string", "null"]},
        "success_predicate": {
            "type": "object",
            "properties": {
                "required_observations": {"type": "array", "items": {"type": "string"}},
                "evidence_required": {"type": "boolean"},
            },
            "required": ["required_observations", "evidence_required"],
            "additionalProperties": False,
        },
        "action_constraints": {
            "type": "object",
            "properties": {
                "max_attempts": {"type": "integer", "minimum": 1, "maximum": 3},
                "max_seconds": {"type": "integer", "minimum": 1},
            },
            "required": ["max_attempts", "max_seconds"],
            "additionalProperties": False,
        },
        "caption": {"type": ["string", "null"]},
        "voice_text": {"type": ["string", "null"]},
        "fallback": {"type": ["string", "null"]},
        "locks": {
            "type": "object",
            "properties": {
                "visual": {"type": "boolean"},
                "voice": {"type": "boolean"},
                "caption": {"type": "boolean"},
                "timing": {"type": "boolean"},
            },
            "required": ["visual", "voice", "caption", "timing"],
            "additionalProperties": False,
        },
    },
    "required": [
        "id",
        "source_type",
        "purpose",
        "target_frames",
        "handles_frames",
        "start_state",
        "desired_event",
        "success_predicate",
        "action_constraints",
        "caption",
        "voice_text",
        "fallback",
        "locks",
    ],
    "additionalProperties": False,
}

SHOT_PLAN_JSON_SCHEMA: dict = {
    "title": "shot_plan",
    "type": "object",
    "properties": {
        "schema_version": {"type": "integer", "const": 1},
        "fps": {
            "type": "object",
            "properties": {"num": {"type": "integer", "minimum": 1}, "den": {"type": "integer", "minimum": 1}},
            "required": ["num", "den"],
            "additionalProperties": False,
        },
        "target_frames": {"type": "integer", "minimum": 1},
        "shots": {"type": "array", "minItems": 1, "maxItems": 12, "items": SHOT_JSON_SCHEMA},
    },
    "required": ["schema_version", "fps", "target_frames", "shots"],
    "additionalProperties": False,
}
