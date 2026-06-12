import { describe, it, expect } from "vitest";
import { edgeColor, edgeSize } from "@/components/graph/edge-style";
import type { GraphEdge } from "@/lib/data";

function edge(partial: Partial<GraphEdge>): GraphEdge {
  return {
    id: "e",
    source: "a",
    target: "b",
    relation: "HAS_MECHANIC",
    ...partial,
  };
}

describe("edgeColor", () => {
  it("returns the default color for every edge", () => {
    expect(edgeColor(edge({}))).toBe("#94a3b8");
  });
});

describe("edgeSize", () => {
  it("returns a fixed size for every edge", () => {
    expect(edgeSize(edge({}))).toBe(2);
  });
});
