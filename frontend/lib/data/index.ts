import { goldenFlow } from "@/lib/fixtures/golden-flow";
import { parseDeveloperProfileInput as parseLocalDeveloperProfileInput } from "@/lib/profile/parser";
import { promoteDraftToProfile } from "@/lib/profile/draft";
import { loadStoredProfile } from "@/lib/profile/storage";
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
  OpportunityMatchResult,
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

// Returns the developer profile that drives downstream steps. A profile the user
// confirmed and saved in browser storage wins; otherwise we fall back to the
// golden-flow sample so the workbench still demos end-to-end.
export async function getDeveloperProfile(): Promise<DeveloperProfile> {
  return settle(loadStoredProfile() ?? goldenFlow.developer_profile);
}

// 浏览器侧统一打前端同源的 /api 前缀,由 Next 服务端 rewrites 代理到后端
// (见 next.config.ts):docker 部署下走内网 backend:8000,因此无需 CORS、
// 后端也无需对公网暴露。显式设 NEXT_PUBLIC_API_BASE_URL 可改为直连某绝对地址。
function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";
}

export async function parseDeveloperProfileInput(
  input: ProfileParseInput,
): Promise<ProfileParseResult> {
  try {
    const response = await fetch(`${apiBase()}/profile/parse`, {
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

// 6.5 机会匹配。把开发者画像发给后端,拿回一批候选机会区域 + 被拒方向 + 警告。
// 这是一个由按钮触发的动作(非 load-on-mount),配套 hook 用 useMutation。
export async function matchOpportunities(
  profile: DeveloperProfile,
): Promise<OpportunityMatchResult> {
  const res = await fetch(`${apiBase()}/opportunity/match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  if (!res.ok) throw new Error(`POST /opportunity/match responded ${res.status}`);
  return (await res.json()) as OpportunityMatchResult;
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
  const res = await fetch(`${apiBase()}/games`);
  if (!res.ok) throw new Error(`GET /games responded ${res.status}`);
  return (await res.json()) as GameSummary[];
}

export async function getGameDocument(id: string): Promise<ImportDocument> {
  const res = await fetch(`${apiBase()}/games/${encodeURIComponent(id)}`);
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
  const res = await fetch(`${apiBase()}/graph/neighbors?${query.toString()}`);
  if (!res.ok) throw new Error(`GET /graph/neighbors responded ${res.status}`);
  return (await res.json()) as NeighborhoodResult;
}

export async function searchGraphNodes(q: string): Promise<NodeSearchHit[]> {
  const res = await fetch(`${apiBase()}/graph/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error(`GET /graph/search responded ${res.status}`);
  return (await res.json()) as NodeSearchHit[];
}

export async function importGame(doc: ImportDocument): Promise<ImportSummary> {
  const res = await fetch(`${apiBase()}/import/game`, {
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
