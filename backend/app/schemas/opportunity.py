# backend/app/schemas/opportunity.py
from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from app.schemas.common import NonEmptyStr, StrictBaseModel


class TransformationType(StrEnum):
    SUBSTITUTE = "substitute"   # 替代：换一个维度值
    COMBINE = "combine"         # 组合：借入一个机制


class Transformation(StrictBaseModel):
    type: TransformationType
    dimension: str = Field(min_length=1)          # "Perspective"/"ArtStyle"/"Genre"/"Mechanic"
    from_value: str | None = Field(default=None, min_length=1)  # 替代=原值；组合=None
    to_value: str = Field(min_length=1)           # 替代=新值；组合=借入机制名

    @model_validator(mode="after")
    def substitute_requires_from_value(self) -> Self:
        if self.type == TransformationType.SUBSTITUTE and self.from_value is None:
            raise ValueError("substitute transformation requires from_value")
        return self


class OpportunityEvidence(StrictBaseModel):
    anchor_game_id: str = Field(min_length=1)
    target_value_game_ids: list[NonEmptyStr] = Field(min_length=1)
    combination_game_ids: list[NonEmptyStr] = Field(default_factory=list)


class FunctionalRole(StrEnum):
    """元素在「体验经济」里承担的功能角色（由核心四段受控词表分类得到：Mechanic/GameFeel/Theme/Genre）。"""
    # 张力 / 风险
    HIGH_VARIANCE_FAILURE = "高方差失败源"
    DREAD_SOURCE = "恐惧张力"
    PACING_COMPRESSOR = "节奏压缩器"
    COMPETITION = "竞技对抗"
    # 精通 / 技巧
    MASTERY_CURVE = "掌握曲线"
    VISCERAL_EXECUTION = "操作快感"
    SYSTEM_OPTIMIZATION = "系统优化"
    PUZZLE_INSIGHT = "解题洞察"
    # 认知 / 涌现
    COGNITIVE_OFFLOAD = "认知降负载"
    EMERGENCE_SOURCE = "涌现源"
    # 资源 / 成长
    RESOURCE_TENSION = "资源张力"
    POWER_ESCALATION = "成长权力"
    COLLECTION_DRIVE = "收集驱动"
    # 社交
    SOCIAL_AMPLIFIER = "社交放大器"
    # 探索 / 沉浸 / 叙事 / 创造 / 舒缓 / 羁绊
    EXPLORATION_DRIVE = "探索驱动"
    ATMOSPHERIC_IMMERSION = "沉浸氛围"
    NARRATIVE_HOOK = "叙事钩子"
    CREATIVE_AUTHORSHIP = "创造表达"
    COZY_COMFORT = "放松抚慰"
    EMOTIONAL_BOND = "情感羁绊"


class SynergyRule(StrictBaseModel):
    id: str = Field(min_length=1)
    role_a: FunctionalRole
    role_b: FunctionalRole
    experience: str = Field(min_length=1)
    evidence_games: list[NonEmptyStr] = Field(default_factory=list)


class SynergyRationale(StrictBaseModel):
    rule_id: str = Field(min_length=1)
    anchor_role: FunctionalRole
    borrowed_role: FunctionalRole
    predicted_experience: str = Field(min_length=1)


class CandidateOpportunityArea(StrictBaseModel):
    id: str = Field(min_length=1)
    anchor_game_id: str = Field(min_length=1)
    anchor_summary: str = Field(min_length=1)
    transformation: Transformation
    existing_combination_count: int = Field(ge=0)  # 已有相同组合的游戏数；越小越新颖
    evidence: OpportunityEvidence
    synergy: SynergyRationale | None = None  # None = 纯稀缺性候选（无规则命中）


class RiskPosture(StrEnum):
    SAFE = "safe"            # 稳妥
    BALANCED = "balanced"   # 平衡
    CHALLENGING = "challenging"  # 挑战


class OpportunityArea(CandidateOpportunityArea):
    risk_posture: RiskPosture
    fit_reason: str = Field(min_length=1)
    risk_reason: str = Field(min_length=1)


class RejectedOpportunity(StrictBaseModel):
    candidate_id: str = Field(min_length=1)
    rejection_reason: str = Field(min_length=1)


class OpportunityMatchResult(StrictBaseModel):
    profile_id: str = Field(min_length=1)
    areas: list[OpportunityArea] = Field(default_factory=list)
    rejected: list[RejectedOpportunity] = Field(default_factory=list)
    warnings: list[NonEmptyStr] = Field(default_factory=list)
