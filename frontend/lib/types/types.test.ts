import { describe, it, expect } from "vitest";
import {
  CONFIDENCE_LEVELS,
  QUALITY_STATUSES,
  CONSTRAINT_TYPES,
  EVALUATION_CATEGORIES,
} from "@/lib/types";

describe("shared type constants", () => {
  it("exposes confidence levels", () => {
    expect(CONFIDENCE_LEVELS).toEqual(["low", "medium", "high"]);
  });

  it("exposes quality statuses", () => {
    expect(QUALITY_STATUSES).toEqual([
      "draft",
      "reviewed",
      "weak_evidence",
      "conflicting",
    ]);
  });

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
});
