// Shared enums (mirror backend app/schemas/common.py).
export const CONSTRAINT_TYPES = [
  "hard",
  "strong_preference",
  "soft_preference",
] as const;
export type ConstraintType = (typeof CONSTRAINT_TYPES)[number];

// Core artifacts (mirror backend app/schemas/artifacts.py).
export interface SeedGame {
  id: string;
  title: string;
  short_description: string;
  selection_reason: string;
}

export interface DesignClaim {
  id: string;
  subject: string;
  relation: string;
  object: string;
  explanation: string;
}

export interface GraphRelation {
  id: string;
  source_node: string;
  relation: string;
  target_node: string;
  claim_id: string;
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
  warnings?: string[];
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

// 图谱查询 DTO（镜像后端 app/schemas/graph.py）
export type GraphNodeType =
  | "Game"
  | "Mechanic"
  | "PlayerAction"
  | "PlayerDecision"
  | "Experience"
  | "Concept"
  | "ReferenceTag"
  | "Genre"
  | "ArtStyle"
  | "AudioStyle"
  | "Perspective"
  | "Theme"
  | "NarrativeStyle"
  | "GameFeel"
  | "TeamModel"
  | "ProductionConstraint"
  | "InnovationPattern"
  | "ReferencePattern"
  | "Risk"
  | "ReplayabilitySource";

export interface GameSummary {
  id: string;
  title: string;
  short_description: string;
}

export interface NodeSearchHit {
  id: string;
  label: string;
  node_type: string;
}

export interface ImportSummary {
  game_id: string;
  mechanics_written: number;
  experiences_written: number;
  tags_written: number;
  concepts_written: number;
  claims_written: number;
}

// 6.5 机会匹配(opportunity matching)。镜像后端 app/schemas/opportunity.py。
export const TRANSFORMATION_TYPES = ["substitute", "combine"] as const;
export type TransformationType = (typeof TRANSFORMATION_TYPES)[number];

export interface Transformation {
  type: TransformationType;
  // 替代: "Perspective" | "ArtStyle" | "Genre";组合: "Mechanic"
  dimension: string;
  from_value: string | null; // 替代必有;组合为 null
  to_value: string;
}

export interface OpportunityEvidence {
  anchor_game_id: string;
  target_value_game_ids: string[];
  combination_game_ids: string[];
}

export interface CandidateOpportunityArea {
  id: string;
  anchor_game_id: string;
  anchor_summary: string;
  transformation: Transformation;
  existing_combination_count: number; // 图谱中已有相同组合的游戏数;越小越新颖
  evidence: OpportunityEvidence;
}

// 6.5 机会区域的风险分档,镜像后端 opportunity.py 的 RiskPosture 枚举。与
// EVALUATION_CATEGORIES(6.7 概念评估分档)当前字面值相同纯属巧合——二者是各自
// 后端模块的独立枚举,任一改动都不应牵连另一,故刻意分开、不要合并复用。
export const RISK_POSTURES = ["safe", "balanced", "challenging"] as const;
export type RiskPosture = (typeof RISK_POSTURES)[number];

export interface OpportunityArea extends CandidateOpportunityArea {
  risk_posture: RiskPosture;
  fit_reason: string;
  risk_reason: string;
}

export interface RejectedOpportunity {
  candidate_id: string;
  rejection_reason: string;
}

export interface OpportunityMatchResult {
  profile_id: string;
  areas: OpportunityArea[];
  rejected: RejectedOpportunity[];
  warnings: string[];
}
