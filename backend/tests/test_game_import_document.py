import pytest
from pydantic import ValidationError

from app.schemas.artifacts import GameDesignProfile, ReferenceValueTag
from app.schemas.common import ConfidenceLevel, EvidenceRef, QualityStatus


def evidence() -> EvidenceRef:
    return EvidenceRef(
        title="Design summary",
        quote_or_summary="Abstract card UI keeps art load low.",
        notes="Curated design interpretation.",
    )


def valid_profile_kwargs() -> dict:
    return {
        "game_id": "game_balatro",
        "one_sentence_summary": "Poker-hand roguelike deckbuilder built on score multipliers.",
        "core_loop": "Play poker hands, buy jokers that rewrite scoring, beat escalating blinds.",
        "progression_model": "Run-based economy buying jokers and upgrades between blinds.",
        "failure_model": "Failing to reach the blind score ends the run.",
        "content_structure": "Procedural run with a fixed escalating blind ladder.",
        "main_player_actions": ["select cards for a hand", "buy and arrange jokers"],
        "main_player_decisions": ["which hand to build", "which joker synergy to chase"],
        "main_player_experiences": ["snowballing payoff", "combo discovery"],
        "main_mechanics": ["poker hand building", "score multiplier engine"],
        "replayability_sources": ["randomized joker pools", "deck variety"],
        "production_constraints": ["abstract card UI", "no character animation"],
        "innovation_patterns": ["familiar rules as on-ramp to systemic depth"],
        "reusable_reference_patterns": ["score multiplier engine", "familiar rule vocabulary"],
        "non_replicable_risks": ["balancing exponential scoring is hard"],
        "reference_value_tags": [
            ReferenceValueTag(
                tag="low art cost reference",
                confidence=ConfidenceLevel.HIGH,
                quality_status=QualityStatus.REVIEWED,
                evidence=[evidence()],
            )
        ],
        "evidence": [evidence()],
        "confidence": ConfidenceLevel.HIGH,
        "quality_status": QualityStatus.REVIEWED,
    }


def test_reference_value_tag_allows_empty_evidence() -> None:
    tag = ReferenceValueTag(
        tag="high systemic depth reference",
        confidence=ConfidenceLevel.MEDIUM,
        quality_status=QualityStatus.DRAFT,
    )
    assert tag.evidence == []


def test_game_design_profile_accepts_valid_payload() -> None:
    profile = GameDesignProfile(**valid_profile_kwargs())
    assert profile.game_id == "game_balatro"
    assert profile.confidence == ConfidenceLevel.HIGH
    assert len(profile.main_mechanics) == 2


def test_game_design_profile_rejects_empty_list_field() -> None:
    kwargs = valid_profile_kwargs()
    kwargs["main_mechanics"] = []
    with pytest.raises(ValidationError):
        GameDesignProfile(**kwargs)


def test_game_design_profile_rejects_unknown_field() -> None:
    kwargs = valid_profile_kwargs()
    kwargs["extra_field"] = "nope"
    with pytest.raises(ValidationError):
        GameDesignProfile(**kwargs)
