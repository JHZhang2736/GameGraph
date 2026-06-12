# backend/tests/test_opportunity_schemas.py
import pytest
from pydantic import ValidationError

from app.schemas.opportunity import (
    CandidateOpportunityArea,
    FunctionalRole,
    OpportunityArea,
    OpportunityEvidence,
    OpportunityMatchResult,
    RejectedOpportunity,
    RiskPosture,
    SynergyRationale,
    SynergyRule,
    Transformation,
    TransformationType,
)


def _candidate(**overrides) -> CandidateOpportunityArea:
    data = dict(
        id="opp_1",
        anchor_game_id="game_a",
        anchor_summary="一句话概括",
        transformation=Transformation(
            type=TransformationType.SUBSTITUTE,
            dimension="Perspective",
            from_value="横版2D",
            to_value="第一人称",
        ),
        existing_combination_count=0,
        evidence=OpportunityEvidence(
            anchor_game_id="game_a",
            target_value_game_ids=["game_b"],
            combination_game_ids=[],
        ),
    )
    data.update(overrides)
    return CandidateOpportunityArea(**data)


def test_candidate_round_trips() -> None:
    candidate = _candidate()
    dumped = candidate.model_dump_json()
    restored = CandidateOpportunityArea.model_validate_json(dumped)
    assert restored == candidate
    assert restored.transformation.type == TransformationType.SUBSTITUTE


def test_opportunity_area_extends_candidate_with_judgment_fields() -> None:
    area = OpportunityArea(
        **_candidate().model_dump(),
        risk_posture=RiskPosture.CHALLENGING,
        fit_reason="契合开发者对探索的偏好",
        risk_reason="3D 视角抬高美术成本",
    )
    assert area.risk_posture == RiskPosture.CHALLENGING
    assert area.anchor_game_id == "game_a"


def test_combine_transformation_allows_null_from_value() -> None:
    t = Transformation(
        type=TransformationType.COMBINE,
        dimension="Mechanic",
        from_value=None,
        to_value="护符定制",
    )
    assert t.from_value is None


def test_result_collects_areas_rejected_and_warnings() -> None:
    result = OpportunityMatchResult(
        profile_id="profile_1",
        areas=[
            OpportunityArea(
                **_candidate().model_dump(),
                risk_posture=RiskPosture.BALANCED,
                fit_reason="ok",
                risk_reason="ok",
            )
        ],
        rejected=[
            RejectedOpportunity(candidate_id="opp_2", rejection_reason="违反硬约束：不做联网多人")
        ],
        warnings=["匹配结果稀疏"],
    )
    assert result.areas[0].risk_posture == RiskPosture.BALANCED
    assert result.rejected[0].candidate_id == "opp_2"


def test_empty_fit_reason_is_rejected() -> None:
    with pytest.raises(ValidationError):
        OpportunityArea(
            **_candidate().model_dump(),
            risk_posture=RiskPosture.SAFE,
            fit_reason="",
            risk_reason="ok",
        )


def test_substitute_requires_from_value() -> None:
    with pytest.raises(ValidationError):
        Transformation(
            type=TransformationType.SUBSTITUTE,
            dimension="Perspective",
            from_value=None,
            to_value="第一人称",
        )


# ---------------------------------------------------------------------------
# FunctionalRole / SynergyRule / SynergyRationale tests
# ---------------------------------------------------------------------------

def test_functional_role_has_twenty_members() -> None:
    assert len(list(FunctionalRole)) == 20
    assert FunctionalRole.HIGH_VARIANCE_FAILURE == "高方差失败源"
    assert FunctionalRole.EMOTIONAL_BOND == "情感羁绊"


def test_synergy_rule_round_trips() -> None:
    rule = SynergyRule(
        id="r1",
        role_a=FunctionalRole.HIGH_VARIANCE_FAILURE,
        role_b=FunctionalRole.SOCIAL_AMPLIFIER,
        experience="欢乐混乱",
        evidence_games=["game_gamble_with_your_friends"],
    )
    assert SynergyRule.model_validate_json(rule.model_dump_json()) == rule


def test_candidate_synergy_defaults_none_and_accepts() -> None:
    # Default: synergy is None
    candidate = _candidate()
    assert candidate.synergy is None

    # Explicit SynergyRationale round-trips
    rationale = SynergyRationale(
        rule_id="r1",
        anchor_role=FunctionalRole.SOCIAL_AMPLIFIER,
        borrowed_role=FunctionalRole.HIGH_VARIANCE_FAILURE,
        predicted_experience="欢乐混乱",
    )
    with_synergy = _candidate(synergy=rationale)
    restored = CandidateOpportunityArea.model_validate_json(with_synergy.model_dump_json())
    assert restored.synergy is not None
    assert restored.synergy.rule_id == "r1"
