import { describe, it, expect } from "vitest";
import {
  formatTransformation,
  formatNovelty,
  riskPostureMeta,
} from "@/lib/opportunity/format";
import type { Transformation } from "@/lib/types";

describe("formatTransformation", () => {
  it("renders a substitute as dimension:from → to", () => {
    const t: Transformation = {
      type: "substitute",
      dimension: "Perspective",
      from_value: "第三人称",
      to_value: "第一人称",
    };
    expect(formatTransformation(t)).toBe("视角:第三人称 → 第一人称");
  });

  it("renders a combine as 借入<dimension>:<to>", () => {
    const t: Transformation = {
      type: "combine",
      dimension: "Mechanic",
      from_value: null,
      to_value: "多用途道具",
    };
    expect(formatTransformation(t)).toBe("借入机制:多用途道具");
  });

  it("falls back to the raw dimension when unmapped", () => {
    const t: Transformation = {
      type: "combine",
      dimension: "SomethingNew",
      from_value: null,
      to_value: "x",
    };
    expect(formatTransformation(t)).toBe("借入SomethingNew:x");
  });
});

describe("formatNovelty", () => {
  it("calls 0 a brand-new combination", () => {
    expect(formatNovelty(0)).toContain("全新组合");
  });

  it("reports the existing count when nonzero", () => {
    expect(formatNovelty(2)).toContain("图谱 2 款");
  });
});

describe("riskPostureMeta", () => {
  it("maps each posture to a Chinese label", () => {
    expect(riskPostureMeta("safe").label).toBe("稳健");
    expect(riskPostureMeta("balanced").label).toBe("平衡");
    expect(riskPostureMeta("challenging").label).toBe("挑战");
  });
});
