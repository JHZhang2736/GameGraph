from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import ConfigDict, Field

from app.schemas.artifacts import DeveloperProfile
from app.schemas.common import StrictBaseModel
from app.schemas.opportunity import CandidateOpportunityArea, OpportunityArea
# 有意复用 6.5 的 LLM 设施（DRY）：_candidate_block / _profile_block 是 6.5 的私有 prompt
# 渲染器，6.6 沿用以保证两模块 prompt 风格一致。若 6.5 改这两者的格式，会同步影响本模块。
from app.services.llm_client import LlmClient, get_llm_client
from app.services.opportunity_llm import _candidate_block, _profile_block

TOOL_NAME = "emit_opportunity_frame"

SYSTEM_PROMPT = (
    "你是独立游戏创意系统的机会框架综合器。"
    "给你开发者画像、一个【被选中的机会区域】(锚点×主变形+证据)、一份【同证据次变形候选池】"
    "以及已由图谱确定性取出的相关机制/体验/约束/创新模式。"
    "请只做叙述综合，不得发明：\n"
    "1. opportunity_area：给这个机会一个简洁主题标签。\n"
    "2. secondary_transformations：只能从【次变形候选池】里挑选并叙述，"
    "禁止发明池子之外、图谱零证据的变形;主变形不要重复(它由系统置于首位)。\n"
    "3. forbidden_directions：把候选池里看似新颖但不自洽/做不出的(dead-zone)写成禁止方向并说明为何行不通"
    "(硬约束禁止项由系统自动补，无需重复)。\n"
    "4. fit_reason / risk_reason：适配理由与风险/取舍说明。\n"
    "不得引入相关机制/来源游戏证据之外的机制或参考。"
)


@dataclass
class FrameInputs:
    related_mechanics: list[str] = field(default_factory=list)
    related_player_experiences: list[str] = field(default_factory=list)
    related_constraints: list[str] = field(default_factory=list)
    related_innovation_patterns: list[str] = field(default_factory=list)
    secondary_pool: list[CandidateOpportunityArea] = field(default_factory=list)


class FrameSynthesis(StrictBaseModel):
    # extra="ignore"：LLM 可能多返字段，宽容忽略（与 opportunity_llm.OpportunityJudgment 一致）。
    model_config = ConfigDict(extra="ignore")

    # 文本字段默认 ""（而非必填）是有意的：build_frame 用 `synth.x or 回退值` 做字段级降级，
    # LLM 漏填单个字段时保留其余已填字段，不让整次综合炸成全量降级。
    opportunity_area: str = ""
    secondary_transformations: list[str] = Field(default_factory=list)
    forbidden_directions: list[str] = Field(default_factory=list)
    fit_reason: str = ""
    risk_reason: str = ""
    warnings: list[str] = Field(default_factory=list)


def _related_block(inputs: FrameInputs) -> str:
    return (
        f"相关机制:{', '.join(inputs.related_mechanics)}\n"
        f"相关体验:{', '.join(inputs.related_player_experiences)}\n"
        f"相关约束:{', '.join(inputs.related_constraints)}\n"
        f"相关创新模式:{', '.join(inputs.related_innovation_patterns)}"
    )


def _selected_block(area: OpportunityArea) -> str:
    t = area.transformation
    change = f"{t.from_value}->{t.to_value}" if t.from_value else f"+{t.to_value}"
    return f"锚点={area.anchor_summary} 主变形={t.type.value}:{t.dimension}({change})"


def _user_block(profile: DeveloperProfile, area: OpportunityArea, inputs: FrameInputs) -> str:
    pool_text = _candidate_block(inputs.secondary_pool) or "（无同证据次变形）"
    return (
        f"开发者画像：\n{_profile_block(profile)}\n\n"
        f"被选中的机会区域：\n{_selected_block(area)}\n\n"
        f"次变形候选池：\n{pool_text}\n\n"
        f"图谱相关材料：\n{_related_block(inputs)}"
    )


class OpportunityFrameLlmClient:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    def synthesize(
        self, profile: DeveloperProfile, area: OpportunityArea, inputs: FrameInputs
    ) -> FrameSynthesis:
        return self._llm.call_tool(
            system_prompt=SYSTEM_PROMPT,
            user_message=_user_block(profile, area, inputs),
            tool_name=TOOL_NAME,
            response_model=FrameSynthesis,
            tool_description="Synthesize the narrative fields of one opportunity frame.",
        )


def get_opportunity_frame_llm_client() -> OpportunityFrameLlmClient | None:
    llm = get_llm_client()
    if llm is None:
        return None
    return OpportunityFrameLlmClient(llm)
