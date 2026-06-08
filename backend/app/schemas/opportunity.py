# backend/app/schemas/opportunity.py
from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from app.schemas.common import NonEmptyStr, StrictBaseModel


class TransformationType(StrEnum):
    SUBSTITUTE = "substitute"   # 替代：换一个维度值
    COMBINE = "combine"         # 组合：借入一个机制


class Transformation(StrictBaseModel):
    type: TransformationType
    dimension: str = Field(min_length=1)          # "Perspective"/"ArtStyle"/"Genre"/"Mechanic"
    from_value: str | None = Field(default=None, min_length=1)  # 替代=原值；组合=None
    to_value: str = Field(min_length=1)           # 替代=新值；组合=借入机制名


class OpportunityEvidence(StrictBaseModel):
    anchor_game_id: str = Field(min_length=1)
    target_value_game_ids: list[NonEmptyStr] = Field(min_length=1)
    combination_game_ids: list[NonEmptyStr] = Field(default_factory=list)


class CandidateOpportunityArea(StrictBaseModel):
    id: str = Field(min_length=1)
    anchor_game_id: str = Field(min_length=1)
    anchor_summary: str = Field(min_length=1)
    transformation: Transformation
    novelty_count: int = Field(ge=0)
    evidence: OpportunityEvidence


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
