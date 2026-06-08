from __future__ import annotations

from pydantic import Field

from app.schemas.common import (
    ConfidenceLevel,
    ConstraintType,
    EvidenceRef,
    NonEmptyStr,
    QualityStatus,
    StrictBaseModel,
)


class DeveloperConstraint(StrictBaseModel):
    id: str = Field(min_length=1)
    type: ConstraintType
    statement: str = Field(min_length=1)


class SeedGame(StrictBaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_refs: list[EvidenceRef] = Field(min_length=1)
    short_description: str = Field(min_length=1)
    selection_reason: str = Field(min_length=1)


class DesignClaim(StrictBaseModel):
    id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    object: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)
    confidence: ConfidenceLevel
    quality_status: QualityStatus


class GraphRelation(StrictBaseModel):
    id: str = Field(min_length=1)
    source_node: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    target_node: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)
    confidence: ConfidenceLevel
    quality_status: QualityStatus


class DeveloperProfile(StrictBaseModel):
    id: str = Field(min_length=1)
    team_size: str = Field(min_length=1)
    time_budget: str = Field(min_length=1)
    programming_ability: str = Field(min_length=1)
    art_ability: str = Field(min_length=1)
    audio_ability: str = Field(min_length=1)
    content_production_ability: str = Field(min_length=1)
    liked_references: list[NonEmptyStr] = Field(min_length=1)
    disliked_references_or_mechanics: list[NonEmptyStr]
    desired_player_experiences: list[NonEmptyStr] = Field(min_length=1)
    constraints: list[DeveloperConstraint] = Field(min_length=1)


class OpportunityFrame(StrictBaseModel):
    id: str = Field(min_length=1)
    developer_profile_id: str = Field(min_length=1)
    opportunity_area: str = Field(min_length=1)
    source_game_ids: list[NonEmptyStr] = Field(min_length=1)
    related_mechanics: list[NonEmptyStr] = Field(min_length=1)
    related_player_experiences: list[NonEmptyStr] = Field(min_length=1)
    related_constraints: list[NonEmptyStr] = Field(min_length=1)
    related_innovation_patterns: list[NonEmptyStr] = Field(min_length=1)
    recommended_transformations: list[NonEmptyStr] = Field(min_length=1)
    forbidden_directions: list[NonEmptyStr] = Field(min_length=1)
    evidence_path: list[NonEmptyStr] = Field(min_length=1)
    fit_reason: str = Field(min_length=1)
    risk_reason: str = Field(min_length=1)


class ConceptCard(StrictBaseModel):
    id: str = Field(min_length=1)
    opportunity_frame_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    one_sentence_concept: str = Field(min_length=1)
    core_fantasy: str = Field(min_length=1)
    core_loop: str = Field(min_length=1)
    main_player_decisions: list[NonEmptyStr] = Field(min_length=1)
    main_mechanics: list[NonEmptyStr] = Field(min_length=1)
    reference_sources: list[NonEmptyStr] = Field(min_length=1)
    difference_from_references: str = Field(min_length=1)
    fit_reason: str = Field(min_length=1)
    production_risks: list[NonEmptyStr] = Field(min_length=1)
    design_risks: list[NonEmptyStr] = Field(min_length=1)
    novelty_reason: str = Field(min_length=1)
    suggested_prototype_scope: str = Field(min_length=1)


class PrototypeBrief(StrictBaseModel):
    id: str = Field(min_length=1)
    concept_card_id: str = Field(min_length=1)
    largest_risk_hypothesis: str = Field(min_length=1)
    minimum_prototype_scope: str = Field(min_length=1)
    target_playtest_duration: str = Field(min_length=1)
    success_signals: list[NonEmptyStr] = Field(min_length=1)
    failure_signals: list[NonEmptyStr] = Field(min_length=1)
    do_not_build_yet: list[NonEmptyStr] = Field(min_length=1)


class ReferenceValueTag(StrictBaseModel):
    tag: str = Field(min_length=1)
    confidence: ConfidenceLevel
    quality_status: QualityStatus
    evidence: list[EvidenceRef] = Field(default_factory=list)


class GameDesignProfile(StrictBaseModel):
    game_id: str = Field(min_length=1)
    one_sentence_summary: str = Field(min_length=1)
    core_loop: str = Field(min_length=1)
    progression_model: str = Field(min_length=1)
    failure_model: str = Field(min_length=1)
    content_structure: str = Field(min_length=1)
    main_player_actions: list[NonEmptyStr] = Field(min_length=1)
    main_player_decisions: list[NonEmptyStr] = Field(min_length=1)
    main_player_experiences: list[NonEmptyStr] = Field(min_length=1)
    main_mechanics: list[NonEmptyStr] = Field(min_length=1)
    replayability_sources: list[NonEmptyStr] = Field(min_length=1)
    production_constraints: list[NonEmptyStr] = Field(min_length=1)
    innovation_patterns: list[NonEmptyStr] = Field(min_length=1)
    reusable_reference_patterns: list[NonEmptyStr] = Field(min_length=1)
    non_replicable_risks: list[NonEmptyStr] = Field(min_length=1)
    reference_value_tags: list[ReferenceValueTag] = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)
    confidence: ConfidenceLevel
    quality_status: QualityStatus
