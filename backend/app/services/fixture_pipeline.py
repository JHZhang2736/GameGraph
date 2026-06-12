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


PROMISED_CONCEPT_OUTCOME_MARKER_PATTERN = (
    r"\b(?:will|going\s+to|(?:is|are)\s+going\s+to|guaranteed(?:\s+to)?|"
    r"(?:is|are)\s+guaranteed\s+to|sure\s+to|certain\s+to|definitely)\b"
)
PROMISED_CONCEPT_OUTCOME_PATTERN = (
    r"\b(?:have\s+fun|commercial\s+success|commercially\s+successful|fun|hit|"
    r"success|successful|succeed|sell)\b"
)

PROMISED_CONCEPT_OUTCOME_PATTERNS = (
    r"\bcommercial\s+success\b",
    r"\bcommercial\s+hit\b",
    r"\bmarket\s+success\b",
    r"\bprofitable\b",
    r"\bviral\s+hit\b",
    r"\bcommercially\s+successful\b",
    r"\bguaranteed\s+fun\b",
    r"\bwill\s+have\s+fun\b",
    r"\bwill\s+be\s+fun\b",
    r"\bwill\s+be\s+a\s+fun\b",
    r"\bwill\s+be\s+successful\b",
    r"\bwill\s+be\s+commercially\s+successful\b",
    r"\bwill\s+be\s+a\s+hit\b",
    r"\bwill\s+be\s+a\s+success\b",
    r"\bwill\s+succeed\b",
    r"\bwill\s+sell\b",
    rf"{PROMISED_CONCEPT_OUTCOME_MARKER_PATTERN}"
    rf".{{0,40}}{PROMISED_CONCEPT_OUTCOME_PATTERN}",
    r"\b(?:is|are)\s+guaranteed\s+to\s+.{0,30}"
    r"\b(?:fun|hit|success|successful|succeed)\b",
    r"\bguarantees?\b.{0,30}\b(?:fun|hit|success|successful|succeed)\b",
)

PROMISED_CONCEPT_OUTCOME_PHRASES = (
    "一定好玩",
    "一定成功",
)

NEGATED_CONCEPT_OUTCOME_PATTERNS = (
    r"\b(?:will|may|might|could)\s+say\b.{0,40}\bnot\s+fun(?:\s+enough)?\b",
    r"\b(?:will|going\s+to|(?:is|are)\s+going\s+to)\s+not\b"
    r".{0,40}\b(?:have\s+fun|be\s+fun|fun|hit|success|successful|succeed|sell)\b",
)

OBSERVABLE_SIGNAL_TERMS = (
    "ask",
    "asks",
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
    "predict",
    "predicts",
    "restart",
    "restarts",
    "say",
    "says",
    "solve",
    "solves",
    "try",
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
    "players are bored",
    "players have fun",
}

VAGUE_RISK_HYPOTHESES = {
    "boring",
    "fun",
    "it is fun",
    "it works",
    "players are bored",
    "players have fun",
    "players enjoy it",
    "players like it",
    "success",
}

GENERIC_EXPERIENCE_OUTCOME_PATTERNS = (
    r"\bplayers?\s+(?:have|has|had)\s+fun\b",
    r"\bplayers?\s+(?:are|were|is|was|feel|feels)\s+"
    r"(?:bored|boring|engaged|engaging)\b",
    r"\bplayers?\s+(?:enjoy|enjoys|like|likes)\s+(?:it|this|the\s+game|play)\b",
    r"\b(?:game|prototype|concept|it|this)\s+"
    r"(?:is|was|will\s+be|feels?)\s+"
    r"(?:fun|boring|successful|engaging)\b",
)

LARGEST_RISK_SPECIFICITY_TERMS = (
    "board",
    "boards",
    "change",
    "changing",
    "choose",
    "chooses",
    "complete",
    "completes",
    "consequence",
    "consequences",
    "encounter",
    "encounters",
    "explain",
    "explains",
    "feedback",
    "identify",
    "identifies",
    "learn",
    "predict",
    "predicts",
    "read",
    "resolve",
    "rule",
    "rules",
    "turn",
    "turns",
    "understand",
    "understands",
    "use",
    "uses",
)

LARGEST_RISK_CONTEXT_TERMS = (
    "after",
    "before",
    "during",
    "encounter",
    "encounters",
    "first",
    "minutes",
    "player",
    "players",
    "playtest",
    "prototype",
    "scope",
    "turn",
    "turns",
    "within",
)


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


def searchable_concept_promise_text(concept: ConceptCard) -> str:
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

        if _promises_fun_or_commercial_success(
            searchable_concept_promise_text(concept)
        ):
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
    normalized_text = _normalize_contract_text(concept_text.replace("-", " "))
    normalized_text = _remove_negated_concept_outcomes(normalized_text)

    if any(phrase in normalized_text for phrase in PROMISED_CONCEPT_OUTCOME_PHRASES):
        return True

    return any(
        re.search(pattern, normalized_text)
        for pattern in PROMISED_CONCEPT_OUTCOME_PATTERNS
    )


def _remove_negated_concept_outcomes(value: str) -> str:
    cleaned = value
    for pattern in NEGATED_CONCEPT_OUTCOME_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned)
    return _normalize_contract_text(cleaned)


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
    if _uses_generic_experience_outcome(normalized):
        return False

    return any(_contains_word(normalized, term) for term in OBSERVABLE_SIGNAL_TERMS)


def _specific_largest_risk_hypothesis(hypothesis: str) -> bool:
    normalized = _normalize_contract_text(hypothesis)

    if normalized in VAGUE_RISK_HYPOTHESES:
        return False
    if len(normalized.split()) < 6:
        return False
    if _uses_generic_experience_outcome(normalized):
        return False

    has_specificity = any(
        _contains_word(normalized, term)
        for term in LARGEST_RISK_SPECIFICITY_TERMS
    )
    has_context = any(
        _contains_word(normalized, term)
        for term in LARGEST_RISK_CONTEXT_TERMS
    )

    return has_specificity and has_context


def _uses_generic_experience_outcome(value: str) -> bool:
    return any(
        re.search(pattern, value)
        for pattern in GENERIC_EXPERIENCE_OUTCOME_PATTERNS
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
