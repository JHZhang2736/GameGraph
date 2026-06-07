import { describe, it, expect } from "vitest";
import { getGoldenFlow, getGameProfile, getGraph } from "@/lib/data";

describe("data layer", () => {
  it("returns the whole golden flow", async () => {
    const flow = await getGoldenFlow();
    expect(flow.seed_games).toHaveLength(3);
    expect(flow.design_claims).toHaveLength(4);
    expect(flow.concept_cards[0].id).toBe("concept_ruleforge_tactics");
  });

  it("returns a game profile bundle with its claims", async () => {
    const bundle = await getGameProfile("game_balatro");
    expect(bundle?.game.title).toBe("Balatro");
    expect(bundle?.profile?.game_id).toBe("game_balatro");
    expect(bundle?.claims.some((c) => c.subject === "Balatro")).toBe(true);
  });

  it("derives graph nodes and edges from relations", async () => {
    const { nodes, edges } = await getGraph();
    expect(edges).toHaveLength(4);
    const nodeIds = new Set(nodes.map((n) => n.id));
    for (const edge of edges) {
      expect(nodeIds.has(edge.source)).toBe(true);
      expect(nodeIds.has(edge.target)).toBe(true);
    }
  });
});
