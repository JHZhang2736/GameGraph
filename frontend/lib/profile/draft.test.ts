import { describe, expect, it } from "vitest";
import {
  createEmptyDraft,
  promoteDraftToProfile,
  recomputeDraftCompleteness,
} from "@/lib/profile/draft";
import type { DeveloperProfileDraft } from "@/lib/types";

function completeDraft(): DeveloperProfileDraft {
  return {
    id: "profile_draft_current",
    team_size: "solo",
    time_budget: "three month prototype",
    programming_ability: "strong",
    art_ability: "weak",
    audio_ability: "basic",
    content_production_ability: "limited",
    liked_references: ["Balatro"],
    disliked_references_or_mechanics: ["online multiplayer"],
    desired_player_experiences: ["short runs"],
    constraints: [
      { id: "constraint_no_online", type: "hard", statement: "Do not require online multiplayer." },
    ],
    missing_fields: [],
    field_sources: [],
    raw_text: "我是 solo 开发者。",
    is_complete: true,
  };
}

describe("recomputeDraftCompleteness", () => {
  it("keeps a complete draft complete and idempotent", () => {
    const draft = recomputeDraftCompleteness(completeDraft());
    expect(draft.is_complete).toBe(true);
    expect(draft.missing_fields).toHaveLength(0);
  });

  it("flags an emptied blocking field and marks the draft incomplete", () => {
    const draft = recomputeDraftCompleteness({ ...completeDraft(), team_size: null });
    expect(draft.is_complete).toBe(false);
    expect(draft.missing_fields).toContainEqual({
      field: "team_size",
      reason: "Could not infer team_size from developer profile input.",
      blocking: true,
    });
  });

  it("keeps optional fields (references, experiences, constraints) out of blocking", () => {
    const draft = recomputeDraftCompleteness({
      ...completeDraft(),
      liked_references: [],
      desired_player_experiences: [],
      constraints: [],
    });
    expect(draft.is_complete).toBe(true);
    const names = draft.missing_fields.map((field) => field.field);
    expect(names).not.toContain("liked_references");
    expect(names).not.toContain("desired_player_experiences");
    expect(names).not.toContain("constraints");
  });

  it("clears a missing field once the user fills it", () => {
    const incomplete = recomputeDraftCompleteness({ ...completeDraft(), time_budget: null });
    const filled = recomputeDraftCompleteness({ ...incomplete, time_budget: "six week prototype" });
    expect(filled.is_complete).toBe(true);
    expect(filled.missing_fields.map((field) => field.field)).not.toContain("time_budget");
  });

  it("ignores non-blocking fields like audio_ability", () => {
    const draft = recomputeDraftCompleteness({ ...completeDraft(), audio_ability: null });
    expect(draft.is_complete).toBe(true);
    expect(draft.missing_fields.map((field) => field.field)).not.toContain("audio_ability");
  });
});

describe("createEmptyDraft", () => {
  it("starts incomplete with required fields unset and audio defaulted", () => {
    const draft = createEmptyDraft();
    expect(draft.is_complete).toBe(false);
    expect(draft.team_size).toBeNull();
    expect(draft.audio_ability).toBe("basic");
    expect(draft.missing_fields.map((field) => field.field)).toContain("team_size");
  });
});

describe("promoteDraftToProfile", () => {
  it("returns a DeveloperProfile for a complete draft", () => {
    const profile = promoteDraftToProfile(completeDraft());
    expect(profile.id).toBe("profile_draft_current");
    expect(profile.team_size).toBe("solo");
    expect(profile.constraints[0].type).toBe("hard");
    expect("missing_fields" in profile).toBe(false);
  });

  it("rejects an incomplete draft", () => {
    const draft = recomputeDraftCompleteness({ ...completeDraft(), team_size: null });
    expect(() => promoteDraftToProfile(draft)).toThrow("DeveloperProfileDraft is incomplete");
  });
});
