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
    if area.synergy is not None:
        r = area.synergy
        path.append(
            f"协同：锚点提供「{r.anchor_role}」，借入补「{r.borrowed_role}」，模式预测「{r.predicted_experience}」"
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


def _fallback_area_label(area: OpportunityArea) -> str:
    return f"基于「{area.anchor_summary}」的机会：{_describe_transformation(area.transformation)}"


def _assemble(
    *,
    profile: DeveloperProfile,
    area: OpportunityArea,
    source_ids: list[str],
    related: tuple[list[str], list[str], list[str], list[str]],
    recommended: list[str],
    forbidden: list[str],
    evidence_path: list[str],
    opportunity_area: str,
    fit_reason: str,
    risk_reason: str,
    warnings: list[str],
) -> OpportunityFrame:
    mechanics, experiences, constraints, innovations = related
    return OpportunityFrame(
        id=f"frame|{area.id}",
        developer_profile_id=profile.id,
        opportunity_area=opportunity_area,
        source_game_ids=source_ids,
        related_mechanics=mechanics,
        related_player_experiences=experiences,
        related_constraints=constraints,
        related_innovation_patterns=innovations,
        recommended_transformations=recommended,
        forbidden_directions=forbidden,
        evidence_path=evidence_path,
        fit_reason=fit_reason,
        risk_reason=risk_reason,
        warnings=warnings,
    )


def build_frame(
    profile: DeveloperProfile,
    area: OpportunityArea,
    repository: SupportsFrameRepository,
    llm_client: SupportsFrameSynthesis | None,
) -> OpportunityFrame:
    source_ids = _source_game_ids(area)
    # related_* 的非空（OpportunityFrame 要求 min_length=1）依赖一条跨模块不变量：
    # 任何入库 Game 都经 GameImportDocument，其 GameDesignProfile 的 main_mechanics /
    # main_player_experiences / production_constraints / innovation_patterns 均 min_length=1，
    # 故每个源游戏必有对应边，并集必非空。source_ids 又必含 anchor。若图谱被部分删改破坏此前提，
    # 此处会在 _assemble 时抛 ValidationError（响亮失败，优于产出空证据的退化框架）。
    related = _union_related(repository.fetch_game_design_facts(source_ids))
    primary = _describe_transformation(area.transformation)
    evidence_path = _evidence_path(area)
    forbidden_base = _forbidden_base(profile)

    def fallback(warning: str) -> OpportunityFrame:
        return _assemble(
            profile=profile, area=area, source_ids=source_ids, related=related,
            recommended=[primary], forbidden=forbidden_base, evidence_path=evidence_path,
            opportunity_area=_fallback_area_label(area),
            fit_reason=area.fit_reason, risk_reason=area.risk_reason, warnings=[warning],
        )

    if llm_client is None:
        return fallback(_NO_LLM_WARNING)

    inputs = FrameInputs(
        related_mechanics=related[0],
        related_player_experiences=related[1],
        related_constraints=related[2],
        related_innovation_patterns=related[3],
        secondary_pool=_secondary_pool(repository, area),
    )
    try:
        synth = llm_client.synthesize(profile, area, inputs)
    except Exception:
        logger.warning("Opportunity frame LLM synthesize failed; falling back", exc_info=True)
        return fallback(_LLM_FAILED_WARNING)

    recommended = _dedup([primary, *synth.secondary_transformations])
    forbidden = _dedup([*forbidden_base, *synth.forbidden_directions])
    return _assemble(
        profile=profile, area=area, source_ids=source_ids, related=related,
        recommended=recommended, forbidden=forbidden, evidence_path=evidence_path,
        opportunity_area=synth.opportunity_area or _fallback_area_label(area),
        fit_reason=synth.fit_reason or area.fit_reason,
        risk_reason=synth.risk_reason or area.risk_reason,
        warnings=_dedup(list(synth.warnings)),  # 过滤 LLM 可能返回的空串，否则 NonEmptyStr 校验 500
    )
