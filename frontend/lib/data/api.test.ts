import { describe, it, expect, vi, afterEach } from "vitest";
import {
  listGames,
  getNeighbors,
  searchGraphNodes,
  importGame,
  ImportError,
} from "@/lib/data";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
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
});
