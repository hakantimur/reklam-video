from pydantic import BaseModel, Field

# JSON schema handed to the LLM via generate_structured's response_format
# (spec §10.2 ConceptSet). Three genuinely different angles, never the same
# idea reworded — enforced by the director system prompt, spot-checked by
# `concepts_are_meaningfully_different` below.
CONCEPT_SET_JSON_SCHEMA: dict = {
    "title": "concept_set",
    "type": "object",
    "properties": {
        "concepts": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "angle": {"type": "string", "description": "Short name for this creative angle"},
                    "hook": {"type": "string", "description": "The opening line/moment, in the brief's language"},
                    "rationale": {
                        "type": "string",
                        "description": "Why this angle fits the verified brief; cites only given facts",
                    },
                    "claim_refs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Which verified claims from the brief this concept relies on",
                    },
                },
                "required": ["angle", "hook", "rationale", "claim_refs"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["concepts"],
    "additionalProperties": False,
}


class ConceptCandidate(BaseModel):
    angle: str = Field(min_length=1, max_length=200)
    hook: str = Field(min_length=1, max_length=1000)
    rationale: str = Field(min_length=1, max_length=2000)
    claim_refs: list[str] = Field(default_factory=list)


class ConceptSetCandidate(BaseModel):
    concepts: list[ConceptCandidate] = Field(min_length=3, max_length=3)


class ConceptOut(BaseModel):
    id: str
    angle: str
    hook: str
    rationale: str
    claim_refs: list[str]
    selected: bool

    model_config = {"from_attributes": False}
