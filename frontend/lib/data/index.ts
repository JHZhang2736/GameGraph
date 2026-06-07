import { goldenFlow } from "@/lib/fixtures/golden-flow";
import type {
  ConceptCard,
  ConceptEvaluation,
  DeveloperProfile,
  DesignClaim,
  GameDesignProfile,
  GoldenFlow,
  OpportunityFrame,
  PrototypeBrief,
  SeedGame,
} from "@/lib/types";

// Simulate a network round-trip so loading/error states are real.
// Swap these bodies for `fetch(...)` when the backend API lands; signatures stay.
const LATENCY_MS = 120;

function settle<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), LATENCY_MS));
}

export async function getGoldenFlow(): Promise<GoldenFlow> {
  return settle(goldenFlow);
}

export async function getSeedGames(): Promise<SeedGame[]> {
  return settle(goldenFlow.seed_games);
}

export interface GameProfileBundle {
  game: SeedGame;
  profile: GameDesignProfile | null;
  claims: DesignClaim[];
}

export async function getGameProfile(id: string): Promise<GameProfileBundle | null> {
  const game = goldenFlow.seed_games.find((g) => g.id === id);
  if (!game) return settle(null);
  const profile = goldenFlow.game_design_profiles.find((p) => p.game_id === id) ?? null;
  const claims = goldenFlow.design_claims.filter((c) => c.subject === game.title);
  return settle({ game, profile, claims });
}

export interface GraphNode {
  id: string;
  label: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  confidence: GoldenFlow["graph_relations"][number]["confidence"];
  quality_status: GoldenFlow["graph_relations"][number]["quality_status"];
  claim_id: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export async function getGraph(): Promise<GraphData> {
  const nodeMap = new Map<string, GraphNode>();
  const edges: GraphEdge[] = [];
  for (const rel of goldenFlow.graph_relations) {
    for (const label of [rel.source_node, rel.target_node]) {
      if (!nodeMap.has(label)) nodeMap.set(label, { id: label, label });
    }
    edges.push({
      id: rel.id,
      source: rel.source_node,
      target: rel.target_node,
      relation: rel.relation,
      confidence: rel.confidence,
      quality_status: rel.quality_status,
      claim_id: rel.claim_id,
    });
  }
  return settle({ nodes: [...nodeMap.values()], edges });
}

export async function getDeveloperProfile(): Promise<DeveloperProfile> {
  return settle(goldenFlow.developer_profile);
}

export async function getOpportunityFrame(): Promise<OpportunityFrame> {
  return settle(goldenFlow.opportunity_frame);
}

export interface ConceptsBundle {
  cards: ConceptCard[];
  evaluations: ConceptEvaluation[];
}

export async function getConcepts(): Promise<ConceptsBundle> {
  return settle({
    cards: goldenFlow.concept_cards,
    evaluations: goldenFlow.concept_evaluations,
  });
}

export async function getPrototypeBrief(): Promise<PrototypeBrief> {
  return settle(goldenFlow.prototype_brief);
}
