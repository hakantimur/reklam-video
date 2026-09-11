from pydantic import BaseModel, Field

REVIEW_JSON_SCHEMA: dict = {
    "title": "take_review",
    "type": "object",
    "properties": {
        "outcome": {"type": "string", "enum": ["pass", "fail", "uncertain"]},
        "reasoning": {"type": "string", "description": "One or two sentences, grounded in what is visible"},
        "defects": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Concrete, specific defects found — empty if outcome is pass",
        },
    },
    "required": ["outcome", "reasoning", "defects"],
    "additionalProperties": False,
}


class TakeReview(BaseModel):
    outcome: str = Field(pattern="^(pass|fail|uncertain)$")
    reasoning: str
    defects: list[str] = Field(default_factory=list)
