import { afterEach, describe, it, expect } from "vitest";
import {
  LATEST_CONCEPTS_KEY,
  clearConcepts,
  loadLatestConcepts,
  saveConcepts,
} from "@/lib/concept/concept-store";
import type { ConceptCard, OpportunityFrame } from "@/lib/types";

function frame(id: string, area = "区域"): OpportunityFrame {
  return {
    id,
    developer_profile_id: "p",
    opportunity_area: area,
    source_game_ids: [],
    related_mechanics: [],
    related_player_experiences: [],
    related_constraints: [],
    related_innovation_patterns: [],
    recommended_transformations: ["主变形"],
    forbidden_directions: ["禁止"],
    evidence_path: [],
    fit_reason: "f",
    risk_reason: "r",
  };
}

function card(id: string): ConceptCard {
  return {
    id,
    opportunity_frame_id: "frame|a",
    title: "标题",
    one_sentence_concept: "一句话",
    core_fantasy: "幻想",
    core_loop: "循环",
    main_player_decisions: ["决策"],
    main_mechanics: ["机制"],
    reference_sources: ["a"],
    difference_from_references: "差异",
    fit_reason: "适配",
    production_risks: ["制作风险"],
    design_risks: ["设计风险"],
    novelty_reason: "新颖",
    suggested_prototype_scope: "原型范围",
  };
}

afterEach(() => {
  localStorage.clear();
});

describe("concept-store", () => {
  it("starts null", () => {
    expect(loadLatestConcepts()).toBeNull();
  });

  it("saves and loads the latest set", () => {
    saveConcepts(frame("frame|a", "区域A"), [card("c1"), card("c2"), card("c3")]);
    const latest = loadLatestConcepts();
    expect(latest?.frame.opportunity_area).toBe("区域A");
    expect(latest?.cards.map((c) => c.id)).toEqual(["c1", "c2", "c3"]);
  });

  it("overwrites the previous set (latest-only)", () => {
    saveConcepts(frame("frame|a"), [card("c1")]);
    saveConcepts(frame("frame|b", "新"), [card("c9")]);
    const latest = loadLatestConcepts();
    expect(latest?.frame.id).toBe("frame|b");
    expect(latest?.cards.map((c) => c.id)).toEqual(["c9"]);
  });

  it("returns a stable reference when storage is unchanged", () => {
    saveConcepts(frame("frame|a"), [card("c1")]);
    expect(loadLatestConcepts()).toBe(loadLatestConcepts());
  });

  it("clears the set", () => {
    saveConcepts(frame("frame|a"), [card("c1")]);
    clearConcepts();
    expect(loadLatestConcepts()).toBeNull();
  });

  it("ignores corrupt storage", () => {
    localStorage.setItem(LATEST_CONCEPTS_KEY, "{not json");
    expect(loadLatestConcepts()).toBeNull();
  });
});
