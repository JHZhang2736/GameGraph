import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.artifacts import (
    ConceptCard,
    DesignClaim,
    DeveloperConstraint,
    DeveloperProfile,
    GraphRelation,
    OpportunityFrame,
    PrototypeBrief,
    SeedGame,
)
from app.schemas.common import ConstraintType


def test_shared_enums_expose_expected_values() -> None:
    assert ConstraintType.HARD == "hard"


def test_seed_game_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SeedGame(
            id="seed-1",
            title="Into the Breach",
            short_description="Compact turn-based tactics about preventing kaiju attacks.",
            selection_reason="Useful reference for readable tactical consequences.",
            source_refs=[],
        )


def test_core_artifacts_accept_minimal_valid_payloads() -> None:
    constraint = DeveloperConstraint(
        id="constraint-1",
        type=ConstraintType.HARD,
        statement="Solo developer, no networked multiplayer.",
    )
    seed_game = SeedGame(
        id="seed-1",
        title="Into the Breach",
        short_description="Compact turn-based tactics about preventing kaiju attacks.",
        selection_reason="Readable consequences are a useful design reference.",
    )
    claim = DesignClaim(
        id="claim-1",
        subject=seed_game.id,
        relation="demonstrates",
        object="previewed consequences",
        explanation="Enemy intent is visible before the player acts.",
    )
    relation = GraphRelation(
        id="relation-1",
        source_node=seed_game.id,
        relation="supports",
        target_node="pattern-previewed-consequences",
        claim_id=claim.id,
    )
    profile = DeveloperProfile(
        id="profile-1",
        team_size="solo",
        time_budget="three months",
        programming_ability="intermediate",
        art_ability="simple 2D",
        audio_ability="basic",
        content_production_ability="low",
        liked_references=[seed_game.id],
        disliked_references_or_mechanics=["precision platforming"],
        desired_player_experiences=["clever tactical saves"],
        constraints=[constraint],
    )
    opportunity = OpportunityFrame(
        id="opportunity-1",
        developer_profile_id=profile.id,
        opportunity_area="Small tactical puzzler with visible cascading consequences.",
        source_game_ids=[seed_game.id],
        related_mechanics=["enemy intent preview"],
        related_player_experiences=["feeling clever under pressure"],
        related_constraints=[constraint.id],
        related_innovation_patterns=["consequence preview"],
        recommended_transformations=["compress battles into five-minute puzzles"],
        forbidden_directions=["large content treadmill"],
        evidence_path=[relation.id],
        fit_reason="Matches low content budget and tactical preferences.",
        risk_reason="Needs enough variety without many bespoke units.",
    )
    concept = ConceptCard(
        id="concept-1",
        opportunity_frame_id=opportunity.id,
        title="Clockwork Rescue",
        one_sentence_concept="A compact tactics puzzle about rescuing civilians from scheduled hazards.",
        core_fantasy="Outsmarting a disaster clock with perfect information.",
        core_loop="Preview, reposition, trigger, and resolve a tiny tactical scene.",
        main_player_decisions=["which hazard to redirect"],
        main_mechanics=["intent preview"],
        reference_sources=[seed_game.id],
        difference_from_references="Focuses on rescue chains instead of combat trades.",
        fit_reason="Small scope with high decision density.",
        production_risks=["puzzle variety may require careful tooling"],
        design_risks=["perfect information can become rote"],
        novelty_reason="Turns enemy intent into environmental rescue choreography.",
        suggested_prototype_scope="Three hazards, one map, five handmade puzzles.",
    )
    brief = PrototypeBrief(
        id="prototype-1",
        concept_card_id=concept.id,
        largest_risk_hypothesis="Players can discover satisfying rescue chains quickly.",
        minimum_prototype_scope="A five-puzzle playable loop with placeholder art.",
        target_playtest_duration="10 minutes",
        success_signals=["players verbalize multiple viable plans"],
        failure_signals=["players solve by trial and error only"],
        do_not_build_yet=["meta progression"],
    )

    assert claim.subject == seed_game.id
    assert relation.claim_id == claim.id
    assert opportunity.developer_profile_id == profile.id
    assert opportunity.source_game_ids == [seed_game.id]
    assert concept.opportunity_frame_id == opportunity.id
    assert brief.concept_card_id == concept.id


def test_prototype_brief_requires_success_and_failure_signals() -> None:
    with pytest.raises(ValidationError):
        PrototypeBrief(
            id="prototype-1",
            concept_card_id="concept-1",
            largest_risk_hypothesis="Players can discover satisfying rescue chains quickly.",
            minimum_prototype_scope="A five-puzzle playable loop with placeholder art.",
            target_playtest_duration="10 minutes",
            success_signals=[],
            failure_signals=["players solve by trial and error only"],
            do_not_build_yet=["meta progression"],
        )

    with pytest.raises(ValidationError):
        PrototypeBrief(
            id="prototype-1",
            concept_card_id="concept-1",
            largest_risk_hypothesis="Players can discover satisfying rescue chains quickly.",
            minimum_prototype_scope="A five-puzzle playable loop with placeholder art.",
            target_playtest_duration="10 minutes",
            success_signals=["players verbalize multiple viable plans"],
            failure_signals=[],
            do_not_build_yet=["meta progression"],
        )


def test_opportunity_frame_rejects_blank_list_items() -> None:
    valid_payload = {
        "id": "opportunity-1",
        "developer_profile_id": "profile-1",
        "opportunity_area": "Small tactical puzzler with visible cascading consequences.",
        "source_game_ids": ["seed-1"],
        "related_mechanics": ["enemy intent preview"],
        "related_player_experiences": ["feeling clever under pressure"],
        "related_constraints": ["constraint-1"],
        "related_innovation_patterns": ["consequence preview"],
        "recommended_transformations": ["compress battles into five-minute puzzles"],
        "forbidden_directions": ["large content treadmill"],
        "evidence_path": ["relation-1"],
        "fit_reason": "Matches low content budget and tactical preferences.",
        "risk_reason": "Needs enough variety without many bespoke units.",
    }

    with pytest.raises(ValidationError):
        OpportunityFrame(**{**valid_payload, "source_game_ids": [""]})

    with pytest.raises(ValidationError):
        OpportunityFrame(**{**valid_payload, "evidence_path": ["   "]})


def test_prototype_brief_rejects_blank_success_signals() -> None:
    with pytest.raises(ValidationError):
        PrototypeBrief(
            id="prototype-1",
            concept_card_id="concept-1",
            largest_risk_hypothesis="Players can discover satisfying rescue chains quickly.",
            minimum_prototype_scope="A five-puzzle playable loop with placeholder art.",
            target_playtest_duration="10 minutes",
            success_signals=["   "],
            failure_signals=["players solve by trial and error only"],
            do_not_build_yet=["meta progression"],
        )


def test_golden_fixture_core_payloads_match_artifact_schemas() -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "golden_flow.json"
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))

    seed_games = TypeAdapter(list[SeedGame]).validate_python(raw["seed_games"])
    design_claims = TypeAdapter(list[DesignClaim]).validate_python(raw["design_claims"])
    developer_profile = DeveloperProfile.model_validate(raw["developer_profile"])
    opportunity_frame = OpportunityFrame.model_validate(raw["opportunity_frame"])
    concept_cards = TypeAdapter(list[ConceptCard]).validate_python(raw["concept_cards"])
    prototype_brief = PrototypeBrief.model_validate(raw["prototype_brief"])

    assert {game.id for game in seed_games} == {
        "game_balatro",
        "game_into_the_breach",
        "game_baba_is_you",
    }
    assert {claim.id for claim in design_claims}
    assert developer_profile.id == "profile_solo_systems"
    assert opportunity_frame.id == "frame_rule_tactics"
    assert concept_cards[0].opportunity_frame_id == opportunity_frame.id
    assert prototype_brief.concept_card_id == concept_cards[0].id
