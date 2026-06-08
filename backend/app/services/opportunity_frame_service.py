from __future__ import annotations

import logging
from typing import Protocol

from app.schemas.artifacts import DeveloperProfile, OpportunityFrame
from app.schemas.common import ConstraintType
from app.schemas.opportunity import OpportunityArea, Transformation, TransformationType
from app.services.opportunity_frame_llm import FrameInputs, FrameSynthesis
from app.services.opportunity_service import (
    CandidateOpportunityArea,
    GameDesignFacts,
    GameDimensions,
    enumerate_candidates,
    rank_candidates,
)

logger = logging.getLogger(__name__)

_NO_LLM_WARNING = "未配置 LLM，机会框架未做叙述综合与次变形扩展，仅返回确定性证据组装。"
_LLM_FAILED_WARNING = "LLM 综合失败，机会框架已降级为确定性证据组装。"
_NO_EXPLICIT_FORBIDDEN = "不要在框架证据范围之外自由发挥（引入无来源支撑的机制或参考）。"


class SupportsFrameRepository(Protocol):
    def fetch_game_dimensions(self) -> list[GameDimensions]: ...
    def fetch_game_design_facts(self, game_ids: list[str]) -> list[GameDesignFacts]: ...


class SupportsFrameSynthesis(Protocol):
    def synthesize(
        self, profile: DeveloperProfile, area: OpportunityArea, inputs: FrameInputs
    ) -> FrameSynthesis: ...


def _dedup(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out


def _source_game_ids(area: OpportunityArea) -> list[str]:
    return _dedup(
        [area.anchor_game_id, *area.evidence.target_value_game_ids, *area.evidence.combination_game_ids]
    )


def _union_related(facts: list[GameDesignFacts]) -> tuple[list[str], list[str], list[str], list[str]]:
    def union(attr: str) -> list[str]:
        return _dedup([v for f in facts for v in getattr(f, attr)])

    return (
        union("mechanics"),
        union("experiences"),
        union("constraints"),
        union("innovation_patterns"),
    )


def _describe_transformation(t: Transformation) -> str:
    if t.type == TransformationType.SUBSTITUTE:
        return f"将 {t.dimension} 从「{t.from_value}」替代为「{t.to_value}」"
    return f"在 {t.dimension} 维度组合借入「{t.to_value}」"


def _evidence_path(area: OpportunityArea) -> list[str]:
    ev = area.evidence
    path = [f"锚点 {area.anchor_game_id} 提供成熟配方：{area.anchor_summary}"]
    path.append(
        f"目标值「{area.transformation.to_value}」在 {', '.join(ev.target_value_game_ids)} 上有据"
    )
    path.append(
        f"该组合在策展库中的现存游戏数 = {area.existing_combination_count}（越小越新颖）"
    )
    return path


def _forbidden_base(profile: DeveloperProfile) -> list[str]:
    base: list[str] = []
    for c in profile.constraints:
        if c.type == ConstraintType.HARD:
            base.append(f"违反硬约束：{c.statement}")
    for disliked in profile.disliked_references_or_mechanics:
        base.append(f"避免开发者明确反感的方向：{disliked}")
    if not base:
        base.append(_NO_EXPLICIT_FORBIDDEN)
    return _dedup(base)


def _secondary_pool(
    repository: SupportsFrameRepository, area: OpportunityArea
) -> list[CandidateOpportunityArea]:
    games = repository.fetch_game_dimensions()
    pool = [
        c
        for c in enumerate_candidates(games)
        if c.anchor_game_id == area.anchor_game_id and c.id != area.id
    ]
    return rank_candidates(pool)
