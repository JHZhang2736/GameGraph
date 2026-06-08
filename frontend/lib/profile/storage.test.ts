import { afterEach, describe, expect, it } from "vitest";
import {
  STORED_PROFILE_KEY,
  clearStoredProfile,
  loadStoredProfile,
  saveStoredProfile,
} from "@/lib/profile/storage";
import type { DeveloperProfile } from "@/lib/types";

function sampleProfile(): DeveloperProfile {
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
  };
}

describe("developer profile storage", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("round-trips a saved profile", () => {
    const profile = sampleProfile();
    saveStoredProfile(profile);
    expect(loadStoredProfile()).toEqual(profile);
  });

  it("returns null when nothing is stored", () => {
    expect(loadStoredProfile()).toBeNull();
  });

  it("returns null when the stored value is invalid JSON", () => {
    localStorage.setItem(STORED_PROFILE_KEY, "{not json");
    expect(loadStoredProfile()).toBeNull();
  });

  it("clears a stored profile", () => {
    saveStoredProfile(sampleProfile());
    clearStoredProfile();
    expect(loadStoredProfile()).toBeNull();
  });
});
