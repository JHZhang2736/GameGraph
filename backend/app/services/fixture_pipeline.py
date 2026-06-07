from __future__ import annotations

import json
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

    return FixturePipelineResult(
        seed_games=seed_games,
        design_claims=design_claims,
        graph_relations=graph_relations,
        developer_profile=developer_profile,
        opportunity_frame=opportunity_frame,
        concept_cards=concept_cards,
        prototype_brief=prototype_brief,
    )
