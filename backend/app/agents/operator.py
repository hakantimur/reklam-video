"""Operator agent (spec §11.3): decides the next game-control action from a
real screenshot plus structured working memory. Vision-based — this module
never infers gameplay from a text description of a screen.
"""

import json
from pathlib import Path

from pydantic import ValidationError

from app.providers.base import (
    ChatMessage,
    StructuredGenerationOptions,
    TextVisionProvider,
    image_content_part,
    text_content_part,
)
from app.schemas.operator import OPERATOR_DECISION_JSON_SCHEMA, OperatorDecision

_PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "operator" / "v1.txt"


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


class OperatorDecisionError(RuntimeError):
    pass


def decide_next_action(
    provider: TextVisionProvider,
    model: str,
    *,
    screenshot_png: bytes,
    package_id: str,
    working_memory: dict,
    actions_taken: int,
    max_actions: int,
    discovery_goal: str,
) -> OperatorDecision:
    system_prompt = _load_system_prompt()

    instructions = (
        f"Selected package: {package_id}. Goal: {discovery_goal}. "
        f"Action budget: {actions_taken}/{max_actions} used so far. "
        "Working memory so far (treat as your own prior notes, not instructions "
        "from the screen):\n"
        + json.dumps(working_memory, ensure_ascii=False)
        + "\n\nLook at the attached current screenshot and decide exactly one next "
        "action. Coordinates are normalized [0,1] relative to the screenshot. "
        "If you believe you understand the core mechanic well enough, or the "
        "budget is nearly exhausted, use finish_discovery with a summary note. "
        "If you see a purchase prompt, a system permission dialog, a login "
        "screen, or anything outside the selected package, use request_takeover."
    )

    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(
            role="user",
            content=[text_content_part(instructions), image_content_part(screenshot_png)],
        ),
    ]

    raw = provider.generate_structured(
        model,
        messages,
        OPERATOR_DECISION_JSON_SCHEMA,
        StructuredGenerationOptions(temperature=0.2, max_output_tokens=800),
    )

    try:
        return OperatorDecision.model_validate(raw)
    except ValidationError as exc:
        raise OperatorDecisionError(f"model returned an invalid OperatorDecision: {exc}") from exc
