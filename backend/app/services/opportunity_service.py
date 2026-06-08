from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.opportunity import (
    CandidateOpportunityArea,
    OpportunityEvidence,
    Transformation,
    TransformationType,
)

MAX_EXISTING_COMBINATIONS = 2   # 已有相同组合的游戏数超过该阈值视为不够稀缺，丢弃
TOP_N = 30                      # 送 LLM 判断的最大候选数

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
) -> list[CandidateOpportunityArea]:
    viable = [c for c in candidates if c.existing_combination_count <= max_existing]
    viable.sort(
        key=lambda c: (
            c.existing_combination_count,
            -len(c.evidence.target_value_game_ids),
            c.id,
        )
    )
    return viable[:top_n]
