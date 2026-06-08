import { describe, expect, it } from "vitest";
import { parseDeveloperProfileInput } from "@/lib/profile/parser";

const defaultText =
  "我是 solo 开发者，程序能力强，美术能力弱，想做三个月内能验证的原型。" +
  "我喜欢 Balatro 和 Into the Breach，想要短局、系统性决策和战术预测。" +
  "不要做在线多人，我不想做长篇叙事内容，也不想做大量内容。";

describe("parseDeveloperProfileInput", () => {
  it("returns a complete draft for the default profile text", () => {
    const result = parseDeveloperProfileInput({ raw_text: defaultText });

    expect(result.draft.is_complete).toBe(true);
    expect(result.draft.team_size).toBe("solo");
    expect(result.draft.time_budget).toBe("three month prototype");
    expect(result.draft.programming_ability).toBe("strong");
    expect(result.draft.art_ability).toBe("weak");
    expect(result.draft.audio_ability).toBe("basic");
    expect(result.draft.content_production_ability).toBe("limited");
    expect(result.draft.liked_references).toEqual(["Balatro", "Into the Breach"]);
    expect(result.draft.desired_player_experiences).toEqual([
      "short runs",
      "systemic decisions",
      "tactical prediction",
    ]);
  });

  it("separates hard and strong-preference constraints", () => {
    const result = parseDeveloperProfileInput({ raw_text: defaultText });

    const byStatement = Object.fromEntries(
      result.draft.constraints.map((item) => [item.statement, item.type]),
    );
    expect(byStatement["Do not require online multiplayer."]).toBe("hard");
    expect(byStatement["Avoid long scripted narrative."]).toBe("strong_preference");
    expect(byStatement["Prefer concepts with limited content production."]).toBe(
      "strong_preference",
    );
  });

  it("marks vague time budget as a blocking missing field", () => {
    const result = parseDeveloperProfileInput({
      raw_text:
        "我是 solo 开发者，程序能力强，美术能力弱，想尽快做个原型。" +
        "我喜欢 Balatro，想要短局和系统性决策，不要做在线多人，也不想做大量内容。",
    });

    expect(result.draft.is_complete).toBe(false);
    expect(result.draft.time_budget).toBeNull();
    expect(result.draft.missing_fields).toContainEqual({
      field: "time_budget",
      reason: "Could not infer time_budget from developer profile input.",
      blocking: true,
    });
  });

  it("keeps liked games out of hard constraints and optional fields out of blocking", () => {
    const result = parseDeveloperProfileInput({
      raw_text: "我是 solo，程序能力强，美术弱，三个月原型。我喜欢 Balatro。",
    });

    const hard = result.draft.constraints.filter((item) => item.type === "hard");
    expect(hard).toHaveLength(0);

    const missing = result.draft.missing_fields.map((item) => item.field);
    // Optional fields never block completeness...
    expect(missing).not.toContain("desired_player_experiences");
    expect(missing).not.toContain("liked_references");
    // ...but a required field that was not stated still does.
    expect(missing).toContain("content_production_ability");
    expect(result.draft.is_complete).toBe(false);
  });

  it("uses explicit references before inferred references", () => {
    const result = parseDeveloperProfileInput({
      raw_text: defaultText,
      liked_references: ["Baba Is You"],
      disliked_references_or_mechanics: ["precision platforming"],
      expected_project_scale: "six week prototype",
    });

    expect(result.draft.liked_references).toEqual(["Baba Is You"]);
    expect(result.draft.disliked_references_or_mechanics).toEqual([
      "precision platforming",
    ]);
    expect(result.draft.time_budget).toBe("six week prototype");
    expect(
      result.draft.field_sources.find((item) => item.field === "liked_references")
        ?.source_kind,
    ).toBe("explicit_field");
  });

  it("attaches a source to every key parsed field", () => {
    const result = parseDeveloperProfileInput({ raw_text: defaultText });

    const sourced = new Set(result.draft.field_sources.map((item) => item.field));
    for (const field of [
      "team_size",
      "time_budget",
      "programming_ability",
      "art_ability",
      "content_production_ability",
      "liked_references",
      "desired_player_experiences",
      "constraints",
    ]) {
      expect(sourced.has(field)).toBe(true);
    }
  });
});
