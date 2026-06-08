import { describe, it, expect } from "vitest";
import { nodeColor } from "@/components/graph/graph-canvas";

describe("nodeColor", () => {
  it("colors games and mechanics differently", () => {
    expect(nodeColor("Game")).not.toBe(nodeColor("Mechanic"));
  });
  it("falls back to a non-empty neutral color for unknown types", () => {
    expect(nodeColor("Genre")).toBeTruthy();
    expect(nodeColor("SomethingElse")).toBeTruthy();
  });
});
