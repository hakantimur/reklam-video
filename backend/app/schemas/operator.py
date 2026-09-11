from pydantic import BaseModel, Field

# Strict structured-output schema (spec §11.2's allowed action set, narrowed
# to what a pure *discovery* pass needs — no start/stop_recording or
# checkpoints here, since spec §4.4 explicitly says discovery footage is
# never auto-accepted as ad footage, so discovery never records).
OPERATOR_DECISION_JSON_SCHEMA: dict = {
    "title": "operator_decision",
    "type": "object",
    "properties": {
        "screen_classification": {
            "type": "string",
            "enum": ["menu", "ready", "playing", "result", "loading", "unknown"],
        },
        "reasoning": {"type": "string", "description": "One or two sentences, why this action"},
        "memory_update": {
            "type": "object",
            "description": "New structured facts learned this turn, to merge into working memory",
            "additionalProperties": True,
        },
        "action": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["tap", "swipe", "press_back", "wait", "finish_discovery", "request_takeover"],
                },
                "x": {"type": ["number", "null"], "description": "Normalized [0,1], for tap/swipe start"},
                "y": {"type": ["number", "null"], "description": "Normalized [0,1], for tap/swipe start"},
                "x2": {"type": ["number", "null"], "description": "Normalized [0,1], swipe end only"},
                "y2": {"type": ["number", "null"], "description": "Normalized [0,1], swipe end only"},
                "duration_ms": {"type": ["integer", "null"], "description": "swipe or wait duration"},
                "note": {
                    "type": ["string", "null"],
                    "description": "Required human-readable reason when type is finish_discovery or request_takeover",
                },
            },
            "required": ["type", "x", "y", "x2", "y2", "duration_ms", "note"],
            "additionalProperties": False,
        },
    },
    "required": ["screen_classification", "reasoning", "memory_update", "action"],
    "additionalProperties": False,
}


class OperatorAction(BaseModel):
    type: str = Field(pattern="^(tap|swipe|press_back|wait|finish_discovery|request_takeover)$")
    x: float | None = None
    y: float | None = None
    x2: float | None = None
    y2: float | None = None
    duration_ms: int | None = None
    note: str | None = None


class OperatorDecision(BaseModel):
    screen_classification: str
    reasoning: str
    memory_update: dict = Field(default_factory=dict)
    action: OperatorAction
