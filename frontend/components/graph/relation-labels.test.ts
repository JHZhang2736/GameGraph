import { describe, it, expect } from "vitest";
import { relationLabel } from "@/components/graph/relation-labels";

describe("relationLabel", () => {
  it("maps known structural relations to Chinese", () => {
    expect(relationLabel("HAS_MECHANIC")).toBe("具备机制");
    expect(relationLabel("DELIVERS_EXPERIENCE")).toBe("带来体验");
  });
  it("maps known claim relations to Chinese", () => {
    expect(relationLabel("reinforces")).toBe("强化");
  });
  it("falls back to the original string for unknown relations", () => {
    expect(relationLabel("MYSTERY_REL")).toBe("MYSTERY_REL");
  });
  it("is safe for empty input", () => {
    expect(relationLabel("")).toBe("");
  });
});
