from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
from pydantic import Field

from app.schemas.common import ConfidenceLevel, ConstraintType, StrictBaseModel
from app.schemas.developer_profile import ProfileParseInput

TOOL_NAME = "emit_developer_profile"

SYSTEM_PROMPT = (
    "你是独立游戏创意系统的开发者画像抽取器。"
    "从开发者的自由表达中抽取结构化画像字段，并通过工具调用返回。"
    "区分硬性约束(hard)、强偏好(strong_preference)、软偏好(soft_preference)；"
    "不要把喜欢的游戏当成约束。"
    "每个抽取出的关键字段都尽量给出原文片段作为来源。"
    "无法判断的字段返回 null 或空列表，不要编造。"
)


@dataclass(frozen=True)
class LlmSettings:
    base_url: str
    api_key: str
    model: str
    timeout: float

    @classmethod
    def from_env(cls) -> "LlmSettings":
        return cls(
            base_url=os.environ.get("LLM_BASE_URL", "").strip(),
            api_key=os.environ.get("LLM_API_KEY", "").strip(),
            model=os.environ.get("LLM_MODEL", "").strip(),
            timeout=float(os.environ.get("LLM_TIMEOUT", "30")),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)


class ExtractedConstraint(StrictBaseModel):
    type: ConstraintType
    statement: str = Field(min_length=1)


class ExtractedSource(StrictBaseModel):
    field: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
    confidence: ConfidenceLevel


class ProfileExtraction(StrictBaseModel):
    team_size: str | None = None
    time_budget: str | None = None
    programming_ability: str | None = None
    art_ability: str | None = None
    audio_ability: str | None = None
    content_production_ability: str | None = None
    liked_references: list[str] = Field(default_factory=list)
    disliked_references_or_mechanics: list[str] = Field(default_factory=list)
    desired_player_experiences: list[str] = Field(default_factory=list)
    constraints: list[ExtractedConstraint] = Field(default_factory=list)
    field_sources: list[ExtractedSource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def build_tool_schema() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": "Return the structured developer profile extracted from the input.",
                "parameters": ProfileExtraction.model_json_schema(),
            },
        }
    ]


def _user_message(input_data: ProfileParseInput) -> str:
    lines = [f"自由描述：{input_data.raw_text}"]
    if input_data.liked_references:
        lines.append(f"显式喜欢参考：{', '.join(input_data.liked_references)}")
    if input_data.disliked_references_or_mechanics:
        lines.append(
            f"显式讨厌参考或机制：{', '.join(input_data.disliked_references_or_mechanics)}"
        )
    if input_data.expected_project_scale:
        lines.append(f"显式项目规模：{input_data.expected_project_scale}")
    return "\n".join(lines)


class ProfileLlmClient:
    def __init__(self, settings: LlmSettings, http_client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout)

    def extract(self, input_data: ProfileParseInput) -> ProfileExtraction:
        payload = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_message(input_data)},
            ],
            "tools": build_tool_schema(),
            "tool_choice": {"type": "function", "function": {"name": TOOL_NAME}},
        }
        response = self._client.post(
            f"{self._settings.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self._settings.api_key}"},
            json=payload,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise ValueError(
                f"LLM request failed with {error.response.status_code}: {error.response.text}"
            ) from error
        data = response.json()
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError(f"Unexpected LLM response shape: {data}") from error
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            raise ValueError("LLM response missing tool_call")
        arguments = tool_calls[0]["function"]["arguments"]
        return ProfileExtraction.model_validate_json(arguments)


def get_llm_client() -> ProfileLlmClient | None:
    settings = LlmSettings.from_env()
    if not settings.is_configured:
        return None
    return ProfileLlmClient(settings)
