import { describe, it, expect } from "vitest";
import { isDowngraded, edgeColor, edgeSize } from "@/components/graph/edge-style";
import type { GraphEdge } from "@/lib/data";

function edge(partial: Partial<GraphEdge>): GraphEdge {
  return {
    id: "e",
    source: "a",
    target: "b",
    relation: "HAS_MECHANIC",
    evidence: [],
    ...partial,
  };
}

describe("isDowngraded", () => {
  it("is true for low confidence", () => {
    expect(isDowngraded(edge({ confidence: "low" }))).toBe(true);
  });
  it("is true for weak or conflicting evidence", () => {
    expect(isDowngraded(edge({ quality_status: "weak_evidence" }))).toBe(true);
    expect(isDowngraded(edge({ quality_status: "conflicting" }))).toBe(true);
  });
  it("is false for high confidence with no quality issues", () => {
    expect(isDowngraded(edge({ confidence: "high" }))).toBe(false);
  });
});

describe("edgeColor", () => {
  it("uses amber for downgraded edges", () => {
    expect(edgeColor(edge({ confidence: "low" }))).toBe("#d97706");
  });
  it("uses green for high confidence", () => {
    expect(edgeColor(edge({ confidence: "high" }))).toBe("#16a34a");
  });
  it("differs between downgraded and high confidence", () => {
    expect(edgeColor(edge({ confidence: "low" }))).not.toBe(
      edgeColor(edge({ confidence: "high" })),
    );
  });
});

describe("edgeSize", () => {
  it("makes downgraded edges thinner than normal edges", () => {
    expect(edgeSize(edge({ confidence: "low" }))).toBeLessThan(
      edgeSize(edge({ confidence: "high" })),
    );
  });
});
