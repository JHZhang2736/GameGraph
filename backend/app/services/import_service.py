from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from app.schemas.common import EvidenceRef, StrictBaseModel
from app.schemas.import_document import GameImportDocument
from app.services.fixture_pipeline import ContractViolation


_EVIDENCE_LIST_ADAPTER = TypeAdapter(list[EvidenceRef])

# profile 列表字段 -> (边类型, 目标节点 label)
PROFILE_LIST_EDGES: dict[str, tuple[str, str]] = {
    "main_mechanics": ("HAS_MECHANIC", "Mechanic"),
    "main_player_actions": ("TAKES_ACTION", "PlayerAction"),
    "main_player_decisions": ("MAKES_DECISION", "PlayerDecision"),
    "main_player_experiences": ("DELIVERS_EXPERIENCE", "Experience"),
    "production_constraints": ("CONSTRAINED_BY", "ProductionConstraint"),
    "innovation_patterns": ("USES_INNOVATION", "InnovationPattern"),
    "reusable_reference_patterns": ("REUSABLE_PATTERN", "ReferencePattern"),
    "non_replicable_risks": ("NON_REPLICABLE_RISK", "Risk"),
    "replayability_sources": ("HAS_REPLAYABILITY_SOURCE", "ReplayabilitySource"),
}


class NodeMerge(StrictBaseModel):
    label: str
    key: dict[str, str]
    properties: dict[str, str]


class EdgeMerge(StrictBaseModel):
    rel_type: str
    from_label: str
    from_key: dict[str, str]
    to_label: str
    to_key: dict[str, str]
    properties: dict[str, str]


class GraphWritePlan(StrictBaseModel):
    game_id: str
    nodes: list[NodeMerge]
    edges: list[EdgeMerge]


class ImportSummary(StrictBaseModel):
    game_id: str
    mechanics_written: int
    experiences_written: int
    tags_written: int
    concepts_written: int
    claims_written: int


def check_import_contracts(document: GameImportDocument) -> None:
    if document.profile.game_id != document.candidate.id:
        raise ContractViolation("profile.game_id must match candidate.id")


def validate_import_document(raw: dict[str, Any]) -> GameImportDocument:
    document = GameImportDocument.model_validate(raw)
    check_import_contracts(document)
    return document


def _evidence_json(evidence: list[EvidenceRef]) -> str:
    return _EVIDENCE_LIST_ADAPTER.dump_json(evidence).decode("utf-8")


def _game_node(document: GameImportDocument) -> NodeMerge:
    candidate = document.candidate
    profile = document.profile
    properties = {
        "title": candidate.title,
        "short_description": candidate.short_description,
        "selection_reason": candidate.selection_reason,
        "one_sentence_summary": profile.one_sentence_summary,
        "core_loop": profile.core_loop,
        "progression_model": profile.progression_model,
        "failure_model": profile.failure_model,
        "content_structure": profile.content_structure,
        "confidence": profile.confidence.value,
        "quality_status": profile.quality_status.value,
        "source_refs_json": _evidence_json(candidate.source_refs),
        "evidence_json": _evidence_json(profile.evidence),
        "document_json": document.model_dump_json(),
    }
    return NodeMerge(label="Game", key={"id": candidate.id}, properties=properties)


def _profile_list_edges(document: GameImportDocument) -> list[EdgeMerge]:
    edges: list[EdgeMerge] = []
    game_key = {"id": document.candidate.id}
    for field_name, (rel_type, label) in PROFILE_LIST_EDGES.items():
        for name in getattr(document.profile, field_name):
            edges.append(
                EdgeMerge(
                    rel_type=rel_type,
                    from_label="Game",
                    from_key=game_key,
                    to_label=label,
                    to_key={"name": name},
                    properties={},
                )
            )
    return edges


def _tag_edges(document: GameImportDocument) -> list[EdgeMerge]:
    game_key = {"id": document.candidate.id}
    edges: list[EdgeMerge] = []
    for tag in document.profile.reference_value_tags:
        edges.append(
            EdgeMerge(
                rel_type="TAGGED",
                from_label="Game",
                from_key=game_key,
                to_label="ReferenceTag",
                to_key={"name": tag.tag},
                properties={
                    "confidence": tag.confidence.value,
                    "quality_status": tag.quality_status.value,
                    "evidence_json": _evidence_json(tag.evidence),
                },
            )
        )
    return edges


def _claim_edges(document: GameImportDocument) -> list[EdgeMerge]:
    game_key = {"id": document.candidate.id}
    edges: list[EdgeMerge] = []
    for claim in document.claims:
        edges.append(
            EdgeMerge(
                rel_type="CLAIM",
                from_label="Game",
                from_key=game_key,
                to_label="Concept",
                to_key={"name": claim.object},
                properties={
                    "claim_id": claim.id,
                    "relation": claim.relation,
                    "explanation": claim.explanation,
                    "evidence_json": _evidence_json(claim.evidence),
                    "confidence": claim.confidence.value,
                    "quality_status": claim.quality_status.value,
                },
            )
        )
    return edges


def build_graph_write_plan(document: GameImportDocument) -> GraphWritePlan:
    edges = [
        *_profile_list_edges(document),
        *_tag_edges(document),
        *_claim_edges(document),
    ]
    return GraphWritePlan(
        game_id=document.candidate.id,
        nodes=[_game_node(document)],
        edges=edges,
    )


def summarize(document: GameImportDocument) -> ImportSummary:
    return ImportSummary(
        game_id=document.candidate.id,
        mechanics_written=len(document.profile.main_mechanics),
        experiences_written=len(document.profile.main_player_experiences),
        tags_written=len(document.profile.reference_value_tags),
        concepts_written=len({claim.object for claim in document.claims}),
        claims_written=len(document.claims),
    )
