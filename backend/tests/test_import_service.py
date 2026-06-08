import pytest
from pydantic import ValidationError

from app.schemas.common import ConfidenceLevel, EvidenceRef, QualityStatus
from app.services.fixture_pipeline import ContractViolation
from app.services.import_service import validate_import_document


def evidence() -> dict:
    return {
        "title": "Design summary",
        "quote_or_summary": "Abstract card UI keeps art load low.",
        "notes": "Curated design interpretation.",
    }


def profile_payload() -> dict:
    return {
        "game_id": "game_balatro",
        "one_sentence_summary": "Poker-hand roguelike deckbuilder built on score multipliers.",
        "core_loop": "Play poker hands, buy jokers that rewrite scoring, beat escalating blinds.",
        "progression_model": "Run-based economy buying jokers between blinds.",
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
            {
                "tag": "low art cost reference",
                "confidence": "high",
                "quality_status": "reviewed",
                "evidence": [evidence()],
            }
        ],
        "evidence": [evidence()],
        "confidence": "high",
        "quality_status": "reviewed",
    }


def document_payload() -> dict:
    return {
        "candidate": {
            "id": "game_balatro",
            "title": "Balatro",
            "source_refs": [evidence()],
            "short_description": "Poker-inspired roguelike deckbuilder.",
            "selection_reason": "Strong sample for familiar rules into systemic depth.",
        },
        "profile": profile_payload(),
        "claims": [],
    }


def test_validate_import_document_returns_typed_document() -> None:
    document = validate_import_document(document_payload())
    assert document.candidate.id == "game_balatro"
    assert document.profile.game_id == "game_balatro"


def test_validate_import_document_rejects_mismatched_game_id() -> None:
    payload = document_payload()
    payload["profile"]["game_id"] = "game_other"
    with pytest.raises(ContractViolation, match="profile.game_id must match candidate.id"):
        validate_import_document(payload)


def test_validate_import_document_raises_validation_error_on_bad_schema() -> None:
    payload = document_payload()
    payload["profile"]["main_mechanics"] = []
    with pytest.raises(ValidationError):
        validate_import_document(payload)
