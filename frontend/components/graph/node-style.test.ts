import { describe, it, expect } from "vitest";
import { nodeColor, nodeSize } from "@/components/graph/node-style";

describe("nodeColor", () => {
  it("colors games and mechanics differently", () => {
    expect(nodeColor("Game")).not.toBe(nodeColor("Mechanic"));
  });
  it("falls back to a non-empty neutral color for unknown types", () => {
    expect(nodeColor("Genre")).toBeTruthy();
    expect(nodeColor("SomethingElse")).toBeTruthy();
  });
});

describe("nodeSize", () => {
  it("grows with degree", () => {
    expect(nodeSize(5)).toBeGreaterThan(nodeSize(1));
  });
  it("clamps to a minimum", () => {
    expect(nodeSize(0)).toBe(6);
  });
  it("clamps to a maximum", () => {
    expect(nodeSize(1000)).toBe(20);
  });
});
