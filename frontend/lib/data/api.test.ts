import { describe, it, expect, vi, afterEach } from "vitest";
import {
  listGames,
  getNeighbors,
  searchGraphNodes,
  importGame,
  ImportError,
  matchOpportunities,
  generateConcepts,
} from "@/lib/data";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function sseFetch(frames: string, status = 200) {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(frames));
      controller.close();
    },
  });
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    body,
  } as unknown as Response);
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("backend data layer", () => {
  it("listGames maps the summaries", async () => {
    vi.stubGlobal("fetch", mockFetch(200, [{ id: "game_hk", title: "Hollow Knight" }]));
    const games = await listGames();
    expect(games[0].id).toBe("game_hk");
  });

  it("getNeighbors passes node_id and rel_types query", async () => {
    const fetchMock = mockFetch(200, { focus: { id: "game_hk" }, nodes: [], edges: [], truncated: false });
    vi.stubGlobal("fetch", fetchMock);
    await getNeighbors({ nodeId: "game_hk", relTypes: ["HAS_MECHANIC"] });
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain("node_id=game_hk");
    expect(calledUrl).toContain("rel_types=HAS_MECHANIC");
  });

  it("searchGraphNodes returns hits", async () => {
    vi.stubGlobal("fetch", mockFetch(200, [{ id: "game_hk", label: "Hollow Knight", node_type: "Game" }]));
    const hits = await searchGraphNodes("hollow");
    expect(hits[0].node_type).toBe("Game");
  });

  it("importGame throws ImportError with backend detail on 409", async () => {
    vi.stubGlobal("fetch", mockFetch(409, { detail: "profile.game_id must match candidate.id" }));
    await expect(importGame({} as never)).rejects.toBeInstanceOf(ImportError);
  });

  it("matchOpportunities posts the profile and parses the result", async () => {
    const result = { profile_id: "dev_profile_1", areas: [], rejected: [], warnings: ["图谱规模较小。"] };
    const fetchMock = sseFetch(`event: result\ndata: ${JSON.stringify(result)}\n\n`);
    vi.stubGlobal("fetch", fetchMock);
    const parsed = await matchOpportunities({ id: "dev_profile_1" } as never, ["opp|seen|1"]);
    expect(parsed.warnings).toEqual(["图谱规模较小。"]);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/opportunity/match");
    expect((init as RequestInit).method).toBe("POST");
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.seen_ids).toEqual(["opp|seen|1"]);
    expect(body.profile).toEqual({ id: "dev_profile_1" });
  });

  it("matchOpportunities throws on a 500", async () => {
    vi.stubGlobal("fetch", sseFetch("", 500));
    await expect(matchOpportunities({ id: "x" } as never, [])).rejects.toThrow();
  });

  it("generateConcepts parses the SSE result", async () => {
    const cards = [{ id: "concept|f|1", title: "A" }];
    vi.stubGlobal("fetch", sseFetch(`event: result\ndata: ${JSON.stringify(cards)}\n\n`));
    const out = await generateConcepts({ id: "f" } as never);
    expect(out[0].id).toBe("concept|f|1");
  });

  it("generateConcepts throws ConceptGenerationError(503) when unconfigured", async () => {
    vi.stubGlobal("fetch", sseFetch("", 503));
    await expect(generateConcepts({ id: "f" } as never)).rejects.toMatchObject({
      name: "ConceptGenerationError",
      status: 503,
    });
  });

  it("generateConcepts maps an error event to ConceptGenerationError(502)", async () => {
    vi.stubGlobal(
      "fetch",
      sseFetch('event: error\ndata: {"detail":"LLM 失败","code":502}\n\n'),
    );
    await expect(generateConcepts({ id: "f" } as never)).rejects.toMatchObject({
      name: "ConceptGenerationError",
      status: 502,
    });
  });
});
