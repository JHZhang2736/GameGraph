import pytest
from pydantic import ValidationError

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
from app.schemas.common import (
    ConfidenceLevel,
    ConstraintType,
    EvidenceRef,
    QualityStatus,
)


def evidence() -> EvidenceRef:
    return EvidenceRef(
        title="Steam page",
        url="https://store.steampowered.com/app/example",
        notes="Primary store reference.",
    )


def test_shared_enums_expose_expected_values() -> None:
    assert ConfidenceLevel.LOW == "low"
    assert ConfidenceLevel.MEDIUM == "medium"
    assert ConfidenceLevel.HIGH == "high"
    assert QualityStatus.REVIEWED == "reviewed"
    assert ConstraintType.HARD == "hard"


def test_evidence_ref_accepts_url_or_summary() -> None:
    with_url = EvidenceRef(
        title="Steam page",
        url="https://store.steampowered.com/app/example",
        notes="Primary store reference.",
    )
    with_summary = EvidenceRef(
        title="Design note",
        quote_or_summary="The game uses a compact tactical board.",
        notes="Manual curation note.",
    )

    assert with_url.url == "https://store.steampowered.com/app/example"
    assert with_summary.quote_or_summary == "The game uses a compact tactical board."


def test_evidence_ref_rejects_missing_reference_payload() -> None:
    with pytest.raises(ValidationError, match="EvidenceRef requires url or quote_or_summary"):
        EvidenceRef(title="Empty source", notes="No reference payload.")


def test_evidence_ref_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        EvidenceRef(
            title="Unexpected source",
            url="https://example.com",
            notes="Unknown fields should not be accepted.",
            confidence="high",
        )


def test_seed_game_requires_source_refs() -> None:
    with pytest.raises(ValidationError):
        SeedGame(
            id="seed-1",
            title="Into the Breach",
            source_refs=[],
            short_description="Compact turn-based tactics about preventing kaiju attacks.",
            selection_reason="Useful reference for readable tactical consequences.",
        )


def test_design_claim_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        DesignClaim(
            id="claim-1",
            subject="Into the Breach",
            relation="uses",
            object="previewed enemy intent",
            explanation="Enemy plans are visible before commitment.",
            evidence=[],
            confidence=ConfidenceLevel.HIGH,
            quality_status=QualityStatus.REVIEWED,
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
        source_refs=[evidence()],
        short_description="Compact turn-based tactics about preventing kaiju attacks.",
        selection_reason="Readable consequences are a useful design reference.",
    )
    claim = DesignClaim(
        id="claim-1",
        subject=seed_game.id,
        relation="demonstrates",
        object="previewed consequences",
        explanation="Enemy intent is visible before the player acts.",
        evidence=[evidence()],
        confidence=ConfidenceLevel.HIGH,
        quality_status=QualityStatus.REVIEWED,
    )
    relation = GraphRelation(
        id="relation-1",
        source_node=seed_game.id,
        relation="supports",
        target_node="pattern-previewed-consequences",
        claim_id=claim.id,
        evidence=[evidence()],
        confidence=ConfidenceLevel.MEDIUM,
        quality_status=QualityStatus.DRAFT,
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
