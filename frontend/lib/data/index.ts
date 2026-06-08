import { goldenFlow } from "@/lib/fixtures/golden-flow";
import { parseDeveloperProfileInput as parseLocalDeveloperProfileInput } from "@/lib/profile/parser";
import { promoteDraftToProfile } from "@/lib/profile/draft";
import type {
  ConceptCard,
  ConceptEvaluation,
  DeveloperProfile,
  DeveloperProfileDraft,
  DesignClaim,
  EvidenceRef,
  GameDesignProfile,
  GameSummary,
  GoldenFlow,
  ImportSummary,
  NodeSearchHit,
  OpportunityFrame,
  ProfileParseInput,
  ProfileParseResult,
  PrototypeBrief,
  SeedGame,
} from "@/lib/types";
import type { ImportDocument } from "@/lib/import/schema";

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
  node_type: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  confidence?: GoldenFlow["graph_relations"][number]["confidence"];
  quality_status?: GoldenFlow["graph_relations"][number]["quality_status"];
  claim_id?: string;
  evidence: EvidenceRef[];
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
      if (!nodeMap.has(label)) nodeMap.set(label, { id: label, label, node_type: "Concept" });
    }
    edges.push({
      id: rel.id,
      source: rel.source_node,
      target: rel.target_node,
      relation: rel.relation,
      confidence: rel.confidence,
      quality_status: rel.quality_status,
      claim_id: rel.claim_id,
      evidence: rel.evidence,
    });
  }
  return settle({ nodes: [...nodeMap.values()], edges });
}

export async function getDeveloperProfile(): Promise<DeveloperProfile> {
  return settle(goldenFlow.developer_profile);
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function parseDeveloperProfileInput(
  input: ProfileParseInput,
): Promise<ProfileParseResult> {
  try {
    const response = await fetch(`${API_BASE}/profile/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    if (!response.ok) throw new Error(`profile/parse responded ${response.status}`);
    return (await response.json()) as ProfileParseResult;
  } catch (error) {
    console.warn("profile/parse failed; using local parser", error);
    const local = parseLocalDeveloperProfileInput(input);
    return {
      ...local,
      warnings: ["后端不可用，已使用本地规则解析。", ...local.warnings],
    };
  }
}

// Confirms a complete draft into the authoritative DeveloperProfile. Today this
// runs the local promotion; swap the body for `fetch('/api/profile/confirm')`
// when the backend route lands. Throws if the draft is not complete.
export async function confirmDeveloperProfile(
  draft: DeveloperProfileDraft,
): Promise<DeveloperProfile> {
  return settle(promoteDraftToProfile(draft));
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

export interface NeighborhoodResult {
  focus: GraphNode;
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncated: boolean;
}

export class ImportError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ImportError";
  }
}

export async function listGames(): Promise<GameSummary[]> {
  const res = await fetch(`${API_BASE}/games`);
  if (!res.ok) throw new Error(`GET /games responded ${res.status}`);
  return (await res.json()) as GameSummary[];
}

export async function getGameDocument(id: string): Promise<ImportDocument> {
  const res = await fetch(`${API_BASE}/games/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(`GET /games/${id} responded ${res.status}`);
  return (await res.json()) as ImportDocument;
}

export interface NeighborsParams {
  nodeId: string;
  hops?: number;
  limit?: number;
  relTypes?: string[];
}

export async function getNeighbors(
  params: NeighborsParams,
): Promise<NeighborhoodResult> {
  const query = new URLSearchParams({ node_id: params.nodeId });
  if (params.hops) query.set("hops", String(params.hops));
  if (params.limit) query.set("limit", String(params.limit));
  if (params.relTypes?.length) query.set("rel_types", params.relTypes.join(","));
  const res = await fetch(`${API_BASE}/graph/neighbors?${query.toString()}`);
  if (!res.ok) throw new Error(`GET /graph/neighbors responded ${res.status}`);
  return (await res.json()) as NeighborhoodResult;
}

export async function searchGraphNodes(q: string): Promise<NodeSearchHit[]> {
  const res = await fetch(`${API_BASE}/graph/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error(`GET /graph/search responded ${res.status}`);
  return (await res.json()) as NodeSearchHit[];
}

export async function importGame(doc: ImportDocument): Promise<ImportSummary> {
  const res = await fetch(`${API_BASE}/import/game`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(doc),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ImportError(
      (body as { detail?: string }).detail ?? `import responded ${res.status}`,
      res.status,
    );
  }
  return (await res.json()) as ImportSummary;
}
