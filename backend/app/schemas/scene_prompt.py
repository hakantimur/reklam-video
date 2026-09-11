from pydantic import BaseModel

SCENE_PROMPT_JSON_SCHEMA: dict = {
    "title": "scene_prompt",
    "type": "object",
    "properties": {
        "video_prompt": {
            "type": "string",
            "description": "A concrete, visual, single-scene video-generation prompt in English",
        },
    },
    "required": ["video_prompt"],
    "additionalProperties": False,
}


class ScenePrompt(BaseModel):
    video_prompt: str
