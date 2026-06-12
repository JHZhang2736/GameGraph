import { describe, it, expect } from "vitest";
import {
  CONSTRAINT_TYPES,
  EVALUATION_CATEGORIES,
  TRANSFORMATION_TYPES,
  RISK_POSTURES,
} from "@/lib/types";

describe("shared type constants", () => {
  it("exposes constraint types", () => {
    expect(CONSTRAINT_TYPES).toEqual([
      "hard",
      "strong_preference",
      "soft_preference",
    ]);
  });

  it("exposes evaluation categories", () => {
    expect(EVALUATION_CATEGORIES).toEqual(["safe", "balanced", "challenging"]);
  });

  it("exposes transformation types", () => {
    expect(TRANSFORMATION_TYPES).toEqual(["substitute", "combine"]);
  });

  it("exposes risk postures", () => {
    expect(RISK_POSTURES).toEqual(["safe", "balanced", "challenging"]);
  });
});
