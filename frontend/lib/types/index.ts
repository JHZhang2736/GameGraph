// Shared enums (mirror backend app/schemas/common.py).
export const CONFIDENCE_LEVELS = ["low", "medium", "high"] as const;
export type ConfidenceLevel = (typeof CONFIDENCE_LEVELS)[number];

export const QUALITY_STATUSES = [
  "draft",
  "reviewed",
  "weak_evidence",
  "conflicting",
] as const;
export type QualityStatus = (typeof QUALITY_STATUSES)[number];

export const CONSTRAINT_TYPES = [
  "hard",
  "strong_preference",
  "soft_preference",
] as const;
export type ConstraintType = (typeof CONSTRAINT_TYPES)[number];

export interface EvidenceRef {
  title: string;
  url?: string;
  quote_or_summary?: string;
  notes: string;
}

// Core artifacts (mirror backend app/schemas/artifacts.py).
export interface SeedGame {
  id: string;
  title: string;
  source_refs: EvidenceRef[];
  short_description: string;
  selection_reason: string;
}

export interface DesignClaim {
  id: string;
  subject: string;
  relation: string;
  object: string;
  explanation: string;
  evidence: EvidenceRef[];
  confidence: ConfidenceLevel;
  quality_status: QualityStatus;
}

export interface GraphRelation {
  id: string;
  source_node: string;
  relation: string;
  target_node: string;
  claim_id: string;
  evidence: EvidenceRef[];
  confidence: ConfidenceLevel;
  quality_status: QualityStatus;
}

export interface DeveloperConstraint {
  id: string;
  type: ConstraintType;
  statement: string;
}

export interface DeveloperProfile {
  id: string;
  team_size: string;
  time_budget: string;
  programming_ability: string;
  art_ability: string;
  audio_ability: string;
  content_production_ability: string;
  liked_references: string[];
  disliked_references_or_mechanics: string[];
  desired_player_experiences: string[];
  constraints: DeveloperConstraint[];
}

// Developer profile workbench (6.4). Mirrors backend
// app/schemas/developer_profile.py and the deterministic parser.
export type ProfileFieldSourceKind = "raw_text" | "explicit_field";

export interface ProfileParseInput {
  raw_text: string;
  liked_references?: string[];
  disliked_references_or_mechanics?: string[];
  expected_project_scale?: string;
}

export interface ProfileFieldSource {
  field: string;
  source_text: string;
  source_kind: ProfileFieldSourceKind;
  confidence: ConfidenceLevel;
}

export interface MissingProfileField {
  field: string;
  reason: string;
  blocking: boolean;
}

export interface DeveloperProfileDraft {
  id: string;
  team_size: string | null;
  time_budget: string | null;
  programming_ability: string | null;
  art_ability: string | null;
  audio_ability: string | null;
  content_production_ability: string | null;
  liked_references: string[];
  disliked_references_or_mechanics: string[];
  desired_player_experiences: string[];
  constraints: DeveloperConstraint[];
  missing_fields: MissingProfileField[];
  field_sources: ProfileFieldSource[];
  raw_text: string;
  is_complete: boolean;
}

export interface ProfileParseResult {
  draft: DeveloperProfileDraft;
  warnings: string[];
}

export interface OpportunityFrame {
  id: string;
  developer_profile_id: string;
  opportunity_area: string;
  source_game_ids: string[];
  related_mechanics: string[];
  related_player_experiences: string[];
  related_constraints: string[];
  related_innovation_patterns: string[];
  recommended_transformations: string[];
  forbidden_directions: string[];
  evidence_path: string[];
  fit_reason: string;
  risk_reason: string;
}

export interface ConceptCard {
  id: string;
  opportunity_frame_id: string;
  title: string;
  one_sentence_concept: string;
  core_fantasy: string;
  core_loop: string;
  main_player_decisions: string[];
  main_mechanics: string[];
  reference_sources: string[];
  difference_from_references: string;
  fit_reason: string;
  production_risks: string[];
  design_risks: string[];
  novelty_reason: string;
  suggested_prototype_scope: string;
}

export interface PrototypeBrief {
  id: string;
  concept_card_id: string;
  largest_risk_hypothesis: string;
  minimum_prototype_scope: string;
  target_playtest_duration: string;
  success_signals: string[];
  failure_signals: string[];
  do_not_build_yet: string[];
}

// Frontend-only artifacts. The backend fixture contract does not yet implement
// full GameDesignProfile / ConceptEvaluation; these shapes drive the read-only
// views and will be aligned with the backend schema once it lands.
export interface GameDesignProfile {
  id: string;
  game_id: string;
  one_sentence_summary: string;
  core_loop: string;
  main_player_actions: string[];
  main_player_decisions: string[];
  main_experiences: string[];
  main_mechanics: string[];
  reference_value_tags: string[];
  hard_to_copy_risks: string[];
  evidence: EvidenceRef[];
  confidence: ConfidenceLevel;
  quality_status: QualityStatus;
}

export const EVALUATION_CATEGORIES = [
  "safe",
  "balanced",
  "challenging",
] as const;
export type EvaluationCategory = (typeof EVALUATION_CATEGORIES)[number];

export interface ConceptEvaluation {
  id: string;
  concept_card_id: string;
  fit_score: number;
  feasibility_score: number;
  novelty_score: number;
  risk_score: number;
  evidence_quality_score: number;
  category: EvaluationCategory;
  notes: string;
}

// Whole-flow shape, equivalent to backend FixturePipelineResult.
export interface GoldenFlow {
  seed_games: SeedGame[];
  design_claims: DesignClaim[];
  graph_relations: GraphRelation[];
  developer_profile: DeveloperProfile;
  opportunity_frame: OpportunityFrame;
  concept_cards: ConceptCard[];
  prototype_brief: PrototypeBrief;
  game_design_profiles: GameDesignProfile[];
  concept_evaluations: ConceptEvaluation[];
}
