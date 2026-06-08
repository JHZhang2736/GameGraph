from copy import deepcopy
from pathlib import Path

import pytest

from app.schemas.common import ConfidenceLevel, QualityStatus
from app.services.fixture_pipeline import (
    ContractViolation,
    build_graph_relations_from_claims,
    load_fixture,
    run_fixture_pipeline,
    run_fixture_pipeline_from_dict,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "fixtures" / "golden_flow.json"
)


def golden_raw() -> dict:
    return deepcopy(load_fixture(FIXTURE_PATH))


def test_build_graph_relations_preserves_claim_evidence_and_quality() -> None:
    result = run_fixture_pipeline(FIXTURE_PATH)
    relations = build_graph_relations_from_claims(result.design_claims)

    relation_by_claim = {relation.claim_id: relation for relation in relations}
    weak_relation = relation_by_claim["claim_symbolic_ui_low_art_cost"]

    assert weak_relation.confidence == ConfidenceLevel.LOW
    assert weak_relation.quality_status == QualityStatus.WEAK_EVIDENCE
    assert weak_relation.evidence[0].notes == "Weak evidence included to prove downstream confidence handling."


def test_golden_flow_runs_end_to_end() -> None:
    result = run_fixture_pipeline(FIXTURE_PATH)

    assert len(result.seed_games) == 3
    assert len(result.design_claims) == 4
    assert len(result.graph_relations) == 4
    assert result.developer_profile.id == "profile_solo_systems"
    assert result.opportunity_frame.id == "frame_rule_tactics"
    assert [concept.id for concept in result.concept_cards] == ["concept_ruleforge_tactics"]
    assert result.prototype_brief.id == "brief_ruleforge_tactics"


def test_opportunity_frame_must_reference_existing_evidence() -> None:
    raw = golden_raw()
    raw["opportunity_frame"]["evidence_path"] = ["claim_missing"]

    with pytest.raises(
        ContractViolation,
        match="OpportunityFrame must include a valid evidence path",
    ):
        run_fixture_pipeline_from_dict(raw)


def test_concept_card_must_reference_existing_opportunity_frame() -> None:
    raw = golden_raw()
    raw["concept_cards"][0]["opportunity_frame_id"] = "frame_missing"

    with pytest.raises(
        ContractViolation,
        match="ConceptCard must reference an existing opportunity frame",
    ):
        run_fixture_pipeline_from_dict(raw)


def test_concept_card_must_not_include_forbidden_directions() -> None:
    raw = golden_raw()
    raw["concept_cards"][0][
        "one_sentence_concept"
    ] = "A short-run tactics game with online multiplayer rule battles."

    with pytest.raises(
        ContractViolation,
        match="ConceptCard must not include forbidden directions",
    ):
        run_fixture_pipeline_from_dict(raw)


def test_concept_card_must_not_promise_fun_or_commercial_success() -> None:
    raw = golden_raw()
    raw["concept_cards"][0][
        "one_sentence_concept"
    ] = "A short-run tactics game that will be fun."

    with pytest.raises(
        ContractViolation,
        match="ConceptCard must not promise fun or commercial success",
    ):
        run_fixture_pipeline_from_dict(raw)


def test_prototype_brief_must_reference_existing_concept_card() -> None:
    raw = golden_raw()
    raw["prototype_brief"]["concept_card_id"] = "concept_missing"

    with pytest.raises(
        ContractViolation,
        match="PrototypeBrief must reference an existing concept card",
    ):
        run_fixture_pipeline_from_dict(raw)


def test_prototype_brief_must_define_observable_signals() -> None:
    raw = golden_raw()
    raw["prototype_brief"]["success_signals"] = ["fun"]
    raw["prototype_brief"]["failure_signals"] = ["not fun"]

    with pytest.raises(
        ContractViolation,
        match="PrototypeBrief must define observable success and failure signals",
    ):
        run_fixture_pipeline_from_dict(raw)
