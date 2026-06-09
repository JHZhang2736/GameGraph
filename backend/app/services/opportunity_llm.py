from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field

from app.schemas.artifacts import DeveloperProfile
from app.schemas.common import StrictBaseModel
from app.schemas.opportunity import CandidateOpportunityArea, RiskPosture
from app.services.llm_client import LlmClient, LlmSettings, get_llm_client  # noqa: F401  (LlmSettings 再导出)

TOOL_NAME = "emit_opportunity_judgments"

SYSTEM_PROMPT = (
    "你是独立游戏创意系统的机会匹配判断器。"
    "给你开发者画像和一组『锚点×变形』候选机会区域（每个含图谱证据与稀缺度）。"
    "对每个候选给出判断：尊重硬约束(hard)，违反者 decision=reject 并说明；"
    "强偏好(strong_preference)可保留但 risk_posture=challenging 并在 risk_reason 写明警告；"
    "看似新颖但不自洽/做不出的候选 decision=reject 并说明为何行不通；"
    "尽量让保留的候选覆盖稳妥/平衡/挑战多种风险姿态。"
    "你不得修改候选的锚点、变形或稀缺度，只做判断。"
)


class OpportunityJudgment(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")

    candidate_id: str = Field(min_length=1)
    decision: Literal["keep", "reject"] = Field(
        description="keep 时需给出 risk_posture/fit_reason/risk_reason；reject 时需给出 rejection_reason",
    )
    risk_posture: RiskPosture | None = None
    fit_reason: str | None = None
    risk_reason: str | None = None
    rejection_reason: str | None = None


class OpportunityJudgmentBatch(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")

    judgments: list[OpportunityJudgment] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _profile_block(profile: DeveloperProfile) -> str:
    lines = [
        f"团队:{profile.team_size} 时间:{profile.time_budget}",
        f"能力 程序:{profile.programming_ability} 美术:{profile.art_ability} "
        f"音频:{profile.audio_ability} 内容产出:{profile.content_production_ability}",
        f"喜欢:{', '.join(profile.liked_references)}",
        f"讨厌:{', '.join(profile.disliked_references_or_mechanics)}",
        f"期望体验:{', '.join(profile.desired_player_experiences)}",
    ]
    if profile.constraints:
        lines.append("约束:")
        for c in profile.constraints:
            lines.append(f"  - [{c.type.value}] {c.statement}")
    return "\n".join(lines)


def _candidate_block(candidates: list[CandidateOpportunityArea]) -> str:
    out = []
    for c in candidates:
        t = c.transformation
        change = f"{t.from_value}->{t.to_value}" if t.from_value else f"+{t.to_value}"
        out.append(
            f"[{c.id}] 锚点={c.anchor_summary} 变形={t.type.value}:{t.dimension}({change}) "
            f"目标值佐证游戏数={len(c.evidence.target_value_game_ids)} "
            f"已有相同组合的游戏数={c.existing_combination_count}（越少越新颖）"
        )
    return "\n".join(out)


class OpportunityLlmClient:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    def judge(
        self, profile: DeveloperProfile, candidates: list[CandidateOpportunityArea]
    ) -> OpportunityJudgmentBatch:
        user = f"开发者画像：\n{_profile_block(profile)}\n\n候选机会：\n{_candidate_block(candidates)}"
        return self._llm.call_tool(
            system_prompt=SYSTEM_PROMPT,
            user_message=user,
            tool_name=TOOL_NAME,
            response_model=OpportunityJudgmentBatch,
            tool_description="Return keep/reject judgments for the supplied opportunity candidates.",
        )


def get_opportunity_llm_client() -> OpportunityLlmClient | None:
    llm = get_llm_client()
    if llm is None:
        return None
    return OpportunityLlmClient(llm)
