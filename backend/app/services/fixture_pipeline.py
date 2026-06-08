from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from app.schemas.artifacts import (
    ConceptCard,
    DesignClaim,
    DeveloperProfile,
    GraphRelation,
    OpportunityFrame,
    PrototypeBrief,
    SeedGame,
)
from app.schemas.common import StrictBaseModel


PROMISED_CONCEPT_OUTCOME_TERMS = (
    "fun",
    "commercial success",
    "commercially successful",
    "guaranteed hit",
    "market success",
    "profitable",
    "viral hit",
    "will sell",
)

OBSERVABLE_SIGNAL_TERMS = (
    "ask",
    "asks",
    "can",
    "cannot",
    "choose",
    "chooses",
    "click",
    "clicks",
    "complete",
    "completes",
    "explain",
    "explains",
    "finish",
    "finishes",
    "player",
    "players",
    "playtester",
    "predict",
    "predicts",
    "restart",
    "restarts",
    "say",
    "says",
    "solve",
    "solves",
    "tester",
    "tries",
    "use",
    "uses",
    "verbalize",
    "verbalizes",
)

VAGUE_SIGNAL_VALUES = {
    "bad",
    "boring",
    "engaging",
    "failure",
    "fun",
    "good",
    "not fun",
    "success",
    "works",
}

VAGUE_RISK_HYPOTHESES = {
    "fun",
    "it is fun",
    "it works",
    "players have fun",
    "players like it",
    "success",
}


class ContractViolation(ValueError):
    pass


class FixturePipelineResult(StrictBaseModel):
    seed_games: list[SeedGame]
    design_claims: list[DesignClaim]
    graph_relations: list[GraphRelation]
    developer_profile: DeveloperProfile
    opportunity_frame: OpportunityFrame
    concept_cards: list[ConceptCard]
    prototype_brief: PrototypeBrief


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_graph_relations_from_claims(claims: list[DesignClaim]) -> list[GraphRelation]:
    return [
        GraphRelation(
            id=f"rel_{claim.id}",
            source_node=claim.subject,
            relation=claim.relation,
            target_node=claim.object,
            claim_id=claim.id,
            evidence=claim.evidence,
            confidence=claim.confidence,
            quality_status=claim.quality_status,
        )
        for claim in claims
    ]


def validate_graph_relations(
    graph_relations: list[GraphRelation],
    design_claims: list[DesignClaim],
) -> None:
    claim_ids = {claim.id for claim in design_claims}

    for relation in graph_relations:
        if relation.claim_id not in claim_ids:
            raise ContractViolation("GraphRelation must reference an existing design claim")


def validate_opportunity_frame(
    opportunity_frame: OpportunityFrame,
    developer_profile: DeveloperProfile,
    seed_games: list[SeedGame],
    design_claims: list[DesignClaim],
    graph_relations: list[GraphRelation],
) -> None:
    if opportunity_frame.developer_profile_id != developer_profile.id:
        raise ContractViolation("OpportunityFrame must reference the developer profile")

    seed_game_ids = {seed_game.id for seed_game in seed_games}
    if any(source_id not in seed_game_ids for source_id in opportunity_frame.source_game_ids):
        raise ContractViolation("OpportunityFrame must reference existing seed games")

    evidence_ids = {claim.id for claim in design_claims} | {
        relation.id for relation in graph_relations
    }
    if any(evidence_id not in evidence_ids for evidence_id in opportunity_frame.evidence_path):
        raise ContractViolation("OpportunityFrame must include a valid evidence path")


def searchable_concept_text(concept: ConceptCard) -> str:
    search_values: list[str] = []

    for value in concept.model_dump().values():
        if isinstance(value, str):
            search_values.append(value)
        elif isinstance(value, list):
            search_values.extend(item for item in value if isinstance(item, str))

    return " ".join(search_values).lower()


def validate_concept_cards(
    concept_cards: list[ConceptCard],
    opportunity_frame: OpportunityFrame,
) -> None:
    for concept in concept_cards:
        if concept.opportunity_frame_id != opportunity_frame.id:
            raise ContractViolation("ConceptCard must reference an existing opportunity frame")

        concept_text = searchable_concept_text(concept)
        forbidden_directions = [
            direction.strip().lower()
            for direction in opportunity_frame.forbidden_directions
            if direction.strip()
        ]

        if any(direction in concept_text for direction in forbidden_directions):
            raise ContractViolation("ConceptCard must not include forbidden directions")

        if _promises_fun_or_commercial_success(concept_text):
            raise ContractViolation("ConceptCard must not promise fun or commercial success")


def validate_prototype_brief(
    prototype_brief: PrototypeBrief,
    concept_cards: list[ConceptCard],
) -> None:
    concept_card_ids = {concept.id for concept in concept_cards}
    if prototype_brief.concept_card_id not in concept_card_ids:
        raise ContractViolation("PrototypeBrief must reference an existing concept card")

    if not _signals_are_observable(
        prototype_brief.success_signals,
        prototype_brief.failure_signals,
    ):
        raise ContractViolation(
            "PrototypeBrief must define observable success and failure signals"
        )

    if not _specific_largest_risk_hypothesis(prototype_brief.largest_risk_hypothesis):
        raise ContractViolation("PrototypeBrief must define a specific largest risk hypothesis")


def _promises_fun_or_commercial_success(concept_text: str) -> bool:
    normalized_text = concept_text.replace("-", " ")

    if _contains_word(normalized_text, "fun"):
        return True

    return any(term in normalized_text for term in PROMISED_CONCEPT_OUTCOME_TERMS[1:])


def _signals_are_observable(
    success_signals: list[str],
    failure_signals: list[str],
) -> bool:
    return all(
        _observable_signal(signal)
        for signal in [*success_signals, *failure_signals]
    )


def _observable_signal(signal: str) -> bool:
    normalized = _normalize_contract_text(signal)

    if normalized in VAGUE_SIGNAL_VALUES:
        return False
    if len(normalized.split()) < 3:
        return False

    return any(_contains_word(normalized, term) for term in OBSERVABLE_SIGNAL_TERMS)


def _specific_largest_risk_hypothesis(hypothesis: str) -> bool:
    normalized = _normalize_contract_text(hypothesis)

    if normalized in VAGUE_RISK_HYPOTHESES:
        return False
    if len(normalized.split()) < 6:
        return False

    return any(
        _contains_word(normalized, term)
        for term in (
            "after",
            "before",
            "can",
            "cannot",
            "during",
            "player",
            "players",
            "within",
        )
    )


def _normalize_contract_text(value: str) -> str:
    return " ".join(value.lower().split())


def _contains_word(value: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", value) is not None


def run_fixture_pipeline(path: Path) -> FixturePipelineResult:
    return run_fixture_pipeline_from_dict(load_fixture(path))


def run_fixture_pipeline_from_dict(raw: dict[str, Any]) -> FixturePipelineResult:
    seed_games = TypeAdapter(list[SeedGame]).validate_python(raw["seed_games"])
    design_claims = TypeAdapter(list[DesignClaim]).validate_python(raw["design_claims"])
    graph_relations = build_graph_relations_from_claims(design_claims)
    developer_profile = DeveloperProfile.model_validate(raw["developer_profile"])
    opportunity_frame = OpportunityFrame.model_validate(raw["opportunity_frame"])
    concept_cards = TypeAdapter(list[ConceptCard]).validate_python(raw["concept_cards"])
    prototype_brief = PrototypeBrief.model_validate(raw["prototype_brief"])

    validate_graph_relations(graph_relations, design_claims)
    validate_opportunity_frame(
        opportunity_frame,
        developer_profile,
        seed_games,
        design_claims,
        graph_relations,
    )
    validate_concept_cards(concept_cards, opportunity_frame)
    validate_prototype_brief(prototype_brief, concept_cards)

    return FixturePipelineResult(
        seed_games=seed_games,
        design_claims=design_claims,
        graph_relations=graph_relations,
        developer_profile=developer_profile,
        opportunity_frame=opportunity_frame,
        concept_cards=concept_cards,
        prototype_brief=prototype_brief,
    )
