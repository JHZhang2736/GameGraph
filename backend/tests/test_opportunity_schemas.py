# backend/tests/test_opportunity_schemas.py
import pytest
from pydantic import ValidationError

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
        novelty_count=0,
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
