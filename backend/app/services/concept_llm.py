from __future__ import annotations

from pydantic import ConfigDict, Field

from app.schemas.artifacts import OpportunityFrame
from app.schemas.common import NonEmptyStr, StrictBaseModel
from app.services.llm_client import LlmClient, get_llm_client

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
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    def generate(self, frame: OpportunityFrame) -> ConceptGenerationBatch:
        return self._llm.call_tool(
            system_prompt=SYSTEM_PROMPT,
            user_message=_frame_block(frame),
            tool_name=TOOL_NAME,
            response_model=ConceptGenerationBatch,
            tool_description="Emit exactly three concept cards within the opportunity frame.",
        )


def get_concept_llm_client() -> ConceptLlmClient | None:
    llm = get_llm_client()
    if llm is None:
        return None
    return ConceptLlmClient(llm)
