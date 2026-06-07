from pathlib import Path

from app.schemas.common import ConfidenceLevel, QualityStatus
from app.services.fixture_pipeline import (
    build_graph_relations_from_claims,
    run_fixture_pipeline,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "fixtures" / "golden_flow.json"
)


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
