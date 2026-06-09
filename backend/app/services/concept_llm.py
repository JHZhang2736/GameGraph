from __future__ import annotations

import httpx
from pydantic import ConfigDict, Field

from app.schemas.artifacts import OpportunityFrame
from app.schemas.common import NonEmptyStr, StrictBaseModel
# 有意复用 6.5 的 LLM 设施（DRY）：LlmSettings 的 env 读取与 is_configured。
from app.services.opportunity_llm import LlmSettings

TOOL_NAME = "emit_concept_cards"

SYSTEM_PROMPT = (
    "你是独立游戏创意系统的概念生成器。"
    "给你一个【机会框架】(自包含创意简报：机会主题、来源游戏、相关机制/体验/约束/创新模式、"
    "推荐变形、禁止方向、证据路径、适配与风险理由)。"
    "请在这个框架划定的设计空间内生成【恰好 3 个】具体、可被评估的游戏概念，要求：\n"
    "1. 三个概念必须在核心玩法(core_loop)与核心幻想(core_fantasy)上各不相同，"
    "不得是同一想法的改写。\n"
    "2. reference_sources 只能引用框架的 source_game_ids；"
    "main_mechanics 取自框架的 related_mechanics / recommended_transformations。\n"
    "3. 不得生成踩 forbidden_directions 的概念；不得引入框架证据之外的机制或参考。\n"
    "4. 每个概念都要给出制作风险与设计风险；证据弱时在 novelty_reason / design_risks 体现"
    "适当不确定性，不得宣称概念一定好玩或成功。"
)


class ConceptDraft(StrictBaseModel):
    # extra="ignore"：LLM 可能多返字段，宽容忽略（与 opportunity_frame_llm.FrameSynthesis 一致）。
    # = ConceptCard 去掉 id / opportunity_frame_id 的全部创意字段，均必填（tool schema 标 required）。
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1)
    one_sentence_concept: str = Field(min_length=1)
    core_fantasy: str = Field(min_length=1)
    core_loop: str = Field(min_length=1)
    main_player_decisions: list[NonEmptyStr] = Field(min_length=1)
    main_mechanics: list[NonEmptyStr] = Field(min_length=1)
    reference_sources: list[NonEmptyStr] = Field(min_length=1)
    difference_from_references: str = Field(min_length=1)
    fit_reason: str = Field(min_length=1)
    production_risks: list[NonEmptyStr] = Field(min_length=1)
    design_risks: list[NonEmptyStr] = Field(min_length=1)
    novelty_reason: str = Field(min_length=1)
    suggested_prototype_scope: str = Field(min_length=1)


class ConceptGenerationBatch(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")

    concepts: list[ConceptDraft] = Field(default_factory=list)


def build_concept_tool_schema() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": "Emit exactly three concept cards within the opportunity frame.",
                "parameters": ConceptGenerationBatch.model_json_schema(),
            },
        }
    ]


def _frame_block(frame: OpportunityFrame) -> str:
    return (
        f"机会主题：{frame.opportunity_area}\n"
        f"来源游戏(reference_sources 只能取这些)：{', '.join(frame.source_game_ids)}\n"
        f"相关机制：{', '.join(frame.related_mechanics)}\n"
        f"相关体验：{', '.join(frame.related_player_experiences)}\n"
        f"相关约束：{', '.join(frame.related_constraints)}\n"
        f"相关创新模式：{', '.join(frame.related_innovation_patterns)}\n"
        f"推荐变形(主变形在首位)：{', '.join(frame.recommended_transformations)}\n"
        f"禁止方向(不得触犯)：{', '.join(frame.forbidden_directions)}\n"
        f"证据路径：{', '.join(frame.evidence_path)}\n"
        f"适配理由：{frame.fit_reason}\n"
        f"风险理由：{frame.risk_reason}"
    )


class ConceptLlmClient:
    def __init__(self, settings: LlmSettings, http_client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout)

    def generate(self, frame: OpportunityFrame) -> ConceptGenerationBatch:
        payload = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _frame_block(frame)},
            ],
            "tools": build_concept_tool_schema(),
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
        try:
            arguments = tool_calls[0]["function"]["arguments"]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError(f"Malformed tool_call in LLM response: {data}") from error
        return ConceptGenerationBatch.model_validate_json(arguments)


def get_concept_llm_client() -> ConceptLlmClient | None:
    settings = LlmSettings.from_env()
    if not settings.is_configured:
        return None
    return ConceptLlmClient(settings)
