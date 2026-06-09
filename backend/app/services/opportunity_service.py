from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

from app.schemas.artifacts import DeveloperProfile
from app.schemas.opportunity import (
    CandidateOpportunityArea,
    OpportunityArea,
    OpportunityEvidence,
    OpportunityMatchResult,
    RejectedOpportunity,
    RiskPosture,
    Transformation,
    TransformationType,
)
from app.services.opportunity_llm import OpportunityJudgment, OpportunityJudgmentBatch

logger = logging.getLogger(__name__)

MAX_EXISTING_COMBINATIONS = 2   # 已有相同组合的游戏数超过该阈值视为不够稀缺，丢弃
# 送 LLM 判断的最大候选数。候选越多,单次 judge 的输入/输出越大、越慢——30 个会让
# 同步请求耗时远超前端代理容忍度(socket hang up)。默认 10 兼顾覆盖与延迟,可用
# LLM_MAX_CANDIDATES 环境变量按需调整。
TOP_N = int(os.environ.get("LLM_MAX_CANDIDATES", "10"))
MAX_PER_ANCHOR = 2      # 多样性主轴:同一锚点游戏最多 2 条变体
MAX_PER_DIMENSION = 5   # 多样性次轴软护栏:防止一种变形维度极端霸屏

# 替代作用的维度 label -> GameDimensions 属性名
_SUBSTITUTE_DIMENSIONS: dict[str, str] = {
    "Perspective": "perspectives",
    "ArtStyle": "art_styles",
    "Genre": "genres",
}


@dataclass
class GameDimensions:
    game_id: str
    summary: str
    genres: set[str] = field(default_factory=set)
    perspectives: set[str] = field(default_factory=set)
    art_styles: set[str] = field(default_factory=set)
    mechanics: set[str] = field(default_factory=set)


@dataclass
class GameDesignFacts:
    # 用 list（非 GameDimensions 的 set）：6.6 的 related_* 需保序去重供展示，
    # 而 GameDimensions 的 set 是为成员判断（value in ...）。两者用途不同，刻意有别。
    game_id: str
    mechanics: list[str] = field(default_factory=list)
    experiences: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    innovation_patterns: list[str] = field(default_factory=list)


def _candidate_id(anchor: str, kind: str, dimension: str, to_value: str) -> str:
    return f"opp|{anchor}|{kind}|{dimension}|{to_value}"


def _games_with_value(games: list[GameDimensions], attr: str, value: str) -> list[str]:
    return sorted(g.game_id for g in games if value in getattr(g, attr))


def _combination_game_ids(
    games: list[GameDimensions], anchor: GameDimensions, attr: str, value: str
) -> list[str]:
    return sorted(
        g.game_id
        for g in games
        if value in getattr(g, attr) and (g.genres & anchor.genres)
    )


def enumerate_candidates(games: list[GameDimensions]) -> list[CandidateOpportunityArea]:
    candidates: list[CandidateOpportunityArea] = []
    for anchor in games:
        candidates.extend(_substitute_candidates(games, anchor))
        candidates.extend(_combine_candidates(games, anchor))
    return candidates


def _substitute_candidates(
    games: list[GameDimensions], anchor: GameDimensions
) -> list[CandidateOpportunityArea]:
    out: list[CandidateOpportunityArea] = []
    for dimension, attr in _SUBSTITUTE_DIMENSIONS.items():
        anchor_values = getattr(anchor, attr)
        if not anchor_values:
            continue  # 锚点在该维度无值则无「原值」可替代（schema 要求 substitute 必带 from_value）
        all_values = {v for g in games for v in getattr(g, attr)}
        from_value = sorted(anchor_values)[0]  # 多值时取词典序最小者作为代表原值（保证确定性）
        for target in sorted(all_values - anchor_values):
            target_games = _games_with_value(games, attr, target)
            combo = _combination_game_ids(games, anchor, attr, target)
            out.append(
                CandidateOpportunityArea(
                    id=_candidate_id(anchor.game_id, "sub", dimension, target),
                    anchor_game_id=anchor.game_id,
                    anchor_summary=anchor.summary,
                    transformation=Transformation(
                        type=TransformationType.SUBSTITUTE,
                        dimension=dimension,
                        from_value=from_value,
                        to_value=target,
                    ),
                    existing_combination_count=len(combo),
                    evidence=OpportunityEvidence(
                        anchor_game_id=anchor.game_id,
                        target_value_game_ids=target_games,
                        combination_game_ids=combo,
                    ),
                )
            )
    return out


def _combine_candidates(
    games: list[GameDimensions], anchor: GameDimensions
) -> list[CandidateOpportunityArea]:
    out: list[CandidateOpportunityArea] = []
    all_mechanics = {m for g in games for m in g.mechanics}
    for target in sorted(all_mechanics - anchor.mechanics):
        target_games = _games_with_value(games, "mechanics", target)
        combo = _combination_game_ids(games, anchor, "mechanics", target)
        out.append(
            CandidateOpportunityArea(
                id=_candidate_id(anchor.game_id, "comb", "Mechanic", target),
                anchor_game_id=anchor.game_id,
                anchor_summary=anchor.summary,
                transformation=Transformation(
                    type=TransformationType.COMBINE,
                    dimension="Mechanic",
                    from_value=None,
                    to_value=target,
                ),
                existing_combination_count=len(combo),
                evidence=OpportunityEvidence(
                    anchor_game_id=anchor.game_id,
                    target_value_game_ids=target_games,
                    combination_game_ids=combo,
                ),
            )
        )
    return out


def rank_candidates(
    candidates: list[CandidateOpportunityArea],
    max_existing: int = MAX_EXISTING_COMBINATIONS,
    top_n: int = TOP_N,
    max_per_anchor: int = MAX_PER_ANCHOR,
    max_per_dimension: int = MAX_PER_DIMENSION,
) -> list[CandidateOpportunityArea]:
    viable = [c for c in candidates if c.existing_combination_count <= max_existing]
    viable.sort(
        key=lambda c: (
            c.existing_combination_count,
            -len(c.evidence.target_value_game_ids),
            c.id,
        )
    )

    selected: list[CandidateOpportunityArea] = []
    selected_ids: set[str] = set()
    per_anchor: dict[str, int] = {}
    per_dimension: dict[str, int] = {}

    # 第一遍:带配额贪心(从最新颖往下),主轴锚点、次轴维度
    for c in viable:
        if len(selected) >= top_n:
            break
        anchor = c.anchor_game_id
        dimension = c.transformation.dimension
        if (
            per_anchor.get(anchor, 0) < max_per_anchor
            and per_dimension.get(dimension, 0) < max_per_dimension
        ):
            selected.append(c)
            selected_ids.add(c.id)
            per_anchor[anchor] = per_anchor.get(anchor, 0) + 1
            per_dimension[dimension] = per_dimension.get(dimension, 0) + 1

    # 第二遍:放宽兜底——配额导致没凑满时,用剩余候选按新颖度补齐(刻意不更新配额计数)
    if len(selected) < top_n:
        for c in viable:
            if len(selected) >= top_n:
                break
            if c.id not in selected_ids:
                selected.append(c)
                selected_ids.add(c.id)

    return selected


SPARSE_AREA_THRESHOLD = 3
_NO_LLM_WARNING = "未配置 LLM，未做约束过滤与可行性判定。"
_LLM_FAILED_WARNING = "LLM 判断失败，已降级为全量保留。"
_EXHAUSTED_WARNING = "已无更多新机会：当前图谱中可探索的候选已全部呈现，可入库更多游戏以拓宽。"
_FALLBACK_FIT_REASON = "未做适配判断（降级保留）。"
_FALLBACK_RISK_REASON = "未做风险判断（降级保留）。"


class SupportsGameDimensions(Protocol):
    def fetch_game_dimensions(self) -> list[GameDimensions]: ...


class SupportsOpportunityJudgment(Protocol):
    def judge(
        self, profile: DeveloperProfile, candidates: list[CandidateOpportunityArea]
    ) -> OpportunityJudgmentBatch: ...


def _area_from_candidate(
    candidate: CandidateOpportunityArea,
    posture: RiskPosture,
    fit_reason: str,
    risk_reason: str,
) -> OpportunityArea:
    return OpportunityArea(
        **candidate.model_dump(),
        risk_posture=posture,
        fit_reason=fit_reason,
        risk_reason=risk_reason,
    )


def _fallback_result(
    profile_id: str,
    candidates: list[CandidateOpportunityArea],
    warning: str,
    extra_warnings: Iterable[str] = (),
) -> OpportunityMatchResult:
    areas = [
        _area_from_candidate(
            c, RiskPosture.BALANCED, _FALLBACK_FIT_REASON, _FALLBACK_RISK_REASON
        )
        for c in candidates
    ]
    return _finalize(profile_id, areas, [], [*extra_warnings, warning])


def _finalize(
    profile_id: str,
    areas: list[OpportunityArea],
    rejected: list[RejectedOpportunity],
    warnings: list[str],
) -> OpportunityMatchResult:
    final_warnings = list(warnings)
    if len(areas) < SPARSE_AREA_THRESHOLD:
        final_warnings.append(
            "匹配结果稀疏：当前图谱规模或约束压窄了可用机会，可继续入库更多游戏以拓宽。"
        )
    return OpportunityMatchResult(
        profile_id=profile_id, areas=areas, rejected=rejected, warnings=final_warnings
    )


def match_opportunities(
    profile: DeveloperProfile,
    repository: SupportsGameDimensions,
    llm_client: SupportsOpportunityJudgment | None,
    seen_ids: Iterable[str] = (),
) -> OpportunityMatchResult:
    games = repository.fetch_game_dimensions()
    seen = set(seen_ids)
    enumerated = enumerate_candidates(games)
    fresh = [c for c in enumerated if c.id not in seen]
    candidates = rank_candidates(fresh)
    exhausted = [_EXHAUSTED_WARNING] if (enumerated and not fresh) else []

    if llm_client is None:
        return _fallback_result(profile.id, candidates, _NO_LLM_WARNING, exhausted)

    try:
        batch = llm_client.judge(profile, candidates)
    except Exception:
        logger.warning("Opportunity LLM judge failed; falling back", exc_info=True)
        return _fallback_result(profile.id, candidates, _LLM_FAILED_WARNING, exhausted)

    by_id: dict[str, OpportunityJudgment] = {}
    duplicate_ids: list[str] = []
    for j in batch.judgments:
        if j.candidate_id in by_id:
            duplicate_ids.append(j.candidate_id)
        else:
            by_id[j.candidate_id] = j

    areas: list[OpportunityArea] = []
    rejected: list[RejectedOpportunity] = []
    warnings = list(batch.warnings)
    unjudged: list[str] = []

    for candidate in candidates:
        judgment = by_id.get(candidate.id)
        if judgment is None:
            unjudged.append(candidate.id)
            areas.append(
                _area_from_candidate(
                    candidate, RiskPosture.BALANCED, "LLM 未判定，默认保留。", "未判定。"
                )
            )
        elif judgment.decision == "reject":
            rejected.append(
                RejectedOpportunity(
                    candidate_id=candidate.id,
                    rejection_reason=judgment.rejection_reason or "未说明拒绝理由。",
                )
            )
        else:
            areas.append(
                _area_from_candidate(
                    candidate,
                    judgment.risk_posture or RiskPosture.BALANCED,
                    judgment.fit_reason or "LLM 未给出适配理由。",
                    judgment.risk_reason or "LLM 未给出风险说明。",
                )
            )

    if unjudged:
        warnings.append(
            f"以下候选未判定（LLM 未返回结果），已默认保留：{', '.join(unjudged)}"
        )
    if duplicate_ids:
        warnings.append(
            f"LLM 对以下候选给出重复判断，仅采用首个：{', '.join(sorted(set(duplicate_ids)))}"
        )
    unknown_ids = sorted(set(by_id) - {c.id for c in candidates})
    if unknown_ids:
        warnings.append(f"LLM 返回了未知候选 id，已忽略：{', '.join(unknown_ids)}")
    return _finalize(profile.id, areas, rejected, [*exhausted, *warnings])
