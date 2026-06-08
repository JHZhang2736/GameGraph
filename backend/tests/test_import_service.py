import pytest
from pydantic import ValidationError

from app.graph.connection import Neo4jSettings
from app.services.fixture_pipeline import ContractViolation
from app.services.import_service import build_graph_write_plan, summarize, validate_import_document


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
        "core_hook": "Familiar poker rules as an on-ramp to exponential scoring builds.",
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
        "genre": ["roguelike deckbuilder"],
        "art_style": ["abstract card art"],
        "audio_style": ["lo-fi ambient"],
        "perspective": ["top-down UI"],
        "theme": ["playing cards", "casino"],
        "narrative_style": ["minimal framing"],
        "game_feel": ["snappy card play"],
        "team_model": ["solo developer"],
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


def test_build_graph_write_plan_creates_game_node_with_document_json() -> None:
    document = validate_import_document(document_payload())
    plan = build_graph_write_plan(document)

    assert plan.game_id == "game_balatro"
    game_nodes = [node for node in plan.nodes if node.label == "Game"]
    assert len(game_nodes) == 1
    game = game_nodes[0]
    assert game.key == {"id": "game_balatro"}
    assert game.properties["title"] == "Balatro"
    assert game.properties["core_loop"].startswith("Play poker hands")
    assert game.properties["evidence_json"].startswith("[")
    assert game.properties["document_json"].startswith("{")


def test_build_graph_write_plan_creates_mechanic_and_tag_edges() -> None:
    document = validate_import_document(document_payload())
    plan = build_graph_write_plan(document)

    mechanic_edges = [edge for edge in plan.edges if edge.rel_type == "HAS_MECHANIC"]
    assert {edge.to_key["name"] for edge in mechanic_edges} == {
        "poker hand building",
        "score multiplier engine",
    }

    tag_edges = [edge for edge in plan.edges if edge.rel_type == "TAGGED"]
    assert len(tag_edges) == 1
    assert tag_edges[0].to_key["name"] == "low art cost reference"
    assert tag_edges[0].properties["confidence"] == "high"
    assert tag_edges[0].properties["evidence_json"].startswith("[")


def test_build_graph_write_plan_with_zero_claims_has_no_claim_edges() -> None:
    document = validate_import_document(document_payload())
    plan = build_graph_write_plan(document)
    assert [edge for edge in plan.edges if edge.rel_type == "CLAIM"] == []


def test_build_graph_write_plan_creates_claim_edges() -> None:
    payload = document_payload()
    payload["claims"] = [
        {
            "id": "claim_balatro_familiar_rules",
            "subject": "Balatro",
            "relation": "reduces",
            "object": "new player learning cost",
            "explanation": "Players already know poker hands.",
            "evidence": [evidence()],
            "confidence": "high",
            "quality_status": "reviewed",
        }
    ]
    document = validate_import_document(payload)
    plan = build_graph_write_plan(document)

    claim_edges = [edge for edge in plan.edges if edge.rel_type == "CLAIM"]
    assert len(claim_edges) == 1
    edge = claim_edges[0]
    assert edge.from_key == {"id": "game_balatro"}
    assert edge.to_label == "Concept"
    assert edge.to_key == {"name": "new player learning cost"}
    assert edge.properties["claim_id"] == "claim_balatro_familiar_rules"
    assert edge.properties["relation"] == "reduces"
    assert edge.properties["confidence"] == "high"


def test_summarize_counts_written_elements() -> None:
    document = validate_import_document(document_payload())
    summary = summarize(document)
    assert summary.game_id == "game_balatro"
    assert summary.mechanics_written == 2
    assert summary.experiences_written == 2
    assert summary.tags_written == 1
    assert summary.claims_written == 0
    assert summary.concepts_written == 0


def test_neo4j_settings_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret-password")

    settings = Neo4jSettings.from_env()

    assert settings.uri == "bolt://localhost:7687"
    assert settings.user == "neo4j"
    assert settings.password == "secret-password"


def test_neo4j_settings_defaults_uri(monkeypatch) -> None:
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret-password")

    settings = Neo4jSettings.from_env()

    assert settings.uri == "bolt://localhost:7687"
