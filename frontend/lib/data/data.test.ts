import { afterEach, describe, it, expect } from "vitest";
import {
  getDeveloperProfile,
  getGoldenFlow,
  getGameProfile,
} from "@/lib/data";
import { saveStoredProfile } from "@/lib/profile/storage";
import type { DeveloperProfile } from "@/lib/types";

describe("getDeveloperProfile", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("falls back to the golden-flow profile when nothing is stored", async () => {
    const profile = await getDeveloperProfile();
    expect(profile.id).toBe("profile_solo_systems");
  });

  it("prefers a profile saved in browser storage", async () => {
    const stored: DeveloperProfile = {
      id: "profile_draft_current",
      team_size: "small team",
      time_budget: "six month project",
      programming_ability: "strong",
      art_ability: "strong",
      audio_ability: "basic",
      content_production_ability: "strong",
      liked_references: [],
      disliked_references_or_mechanics: [],
      desired_player_experiences: [],
      constraints: [],
    };
    saveStoredProfile(stored);
    expect(await getDeveloperProfile()).toEqual(stored);
  });
});

describe("data layer", () => {
  it("returns the whole golden flow", async () => {
    const flow = await getGoldenFlow();
    expect(flow.seed_games).toHaveLength(3);
    expect(flow.design_claims).toHaveLength(4);
    expect(flow.concept_cards[0].id).toBe("concept_ruleforge_tactics");
  });

  it("returns a game profile bundle with its claims", async () => {
    const bundle = await getGameProfile("game_balatro");
    expect(bundle?.game.title).toBe("Balatro");
    expect(bundle?.profile?.game_id).toBe("game_balatro");
    expect(bundle?.claims.some((c) => c.subject === "Balatro")).toBe(true);
  });

});
