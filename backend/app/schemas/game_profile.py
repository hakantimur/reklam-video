from pydantic import BaseModel, Field

GAME_PROFILE_SUMMARY_JSON_SCHEMA: dict = {
    "title": "game_profile_summary",
    "type": "object",
    "properties": {
        "mechanic_summary": {
            "type": "string",
            "description": "Plain-language summary of the core game mechanic actually observed",
        },
        "navigation": {
            "type": "object",
            "description": "Known screens and how to reach them, keyed by screen name",
            "additionalProperties": True,
        },
        "state_signals": {
            "type": "object",
            "description": "How to recognize each screen/state from a screenshot",
            "additionalProperties": True,
        },
        "supported_actions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Concrete actions this game responds to, e.g. 'tap sequence tiles in order'",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Your own confidence that mechanic_summary is accurate, not a random guess",
        },
    },
    "required": ["mechanic_summary", "navigation", "state_signals", "supported_actions", "confidence"],
    "additionalProperties": False,
}


class GameProfileSummary(BaseModel):
    mechanic_summary: str = Field(min_length=1)
    navigation: dict = Field(default_factory=dict)
    state_signals: dict = Field(default_factory=dict)
    supported_actions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
