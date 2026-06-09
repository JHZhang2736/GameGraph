from __future__ import annotations

from pydantic import ConfigDict, Field

from app.schemas.common import ConfidenceLevel, ConstraintType, StrictBaseModel
from app.schemas.developer_profile import ProfileParseInput
from app.services.llm_client import LlmClient, get_llm_client as get_llm_client_base

TOOL_NAME = "emit_developer_profile"

SYSTEM_PROMPT = (
    "你是独立游戏创意系统的开发者画像抽取器。"
    "从开发者的自由表达中抽取结构化画像字段，并通过工具调用返回。"
    "区分硬性约束(hard)、强偏好(strong_preference)、软偏好(soft_preference)；"
    "不要把喜欢的游戏当成约束。"
    "每个抽取出的关键字段都尽量给出原文片段作为来源。"
    "无法判断的字段返回 null 或空列表，不要编造。"
)


class ExtractedConstraint(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")

    type: ConstraintType
    statement: str = Field(min_length=1)


class ExtractedSource(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")

    field: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
    confidence: ConfidenceLevel


class ProfileExtraction(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")

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
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    def extract(self, input_data: ProfileParseInput) -> ProfileExtraction:
        return self._llm.call_tool(
            system_prompt=SYSTEM_PROMPT,
            user_message=_user_message(input_data),
            tool_name=TOOL_NAME,
            response_model=ProfileExtraction,
            tool_description="Return the structured developer profile extracted from the input.",
        )


def get_llm_client() -> ProfileLlmClient | None:
    llm = get_llm_client_base()
    if llm is None:
        return None
    return ProfileLlmClient(llm)
