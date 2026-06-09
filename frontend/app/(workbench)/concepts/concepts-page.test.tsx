import { afterEach, describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ConceptsPage from "@/app/(workbench)/concepts/page";
import { saveConcepts } from "@/lib/concept/concept-store";
import type { ConceptCard, OpportunityFrame } from "@/lib/types";

function frame(area = "第一人称生存割草"): OpportunityFrame {
  return {
    id: "frame|opp|a|sub|Perspective|第一人称",
    developer_profile_id: "p",
    opportunity_area: area,
    source_game_ids: ["a"],
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

function card(id: string, title: string): ConceptCard {
  return {
    id,
    opportunity_frame_id: "frame|opp|a|sub|Perspective|第一人称",
    title,
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

describe("ConceptsPage", () => {
  it("shows an empty state with a link to opportunities when there is no concept set", () => {
    render(<ConceptsPage />);
    expect(screen.getByText(/还没有概念/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /去机会框架/ })).toBeInTheDocument();
  });

  it("renders the generated cards and the frame context header", () => {
    saveConcepts(frame("第一人称生存割草"), [
      card("c1", "概念一"),
      card("c2", "概念二"),
      card("c3", "概念三"),
    ]);
    render(<ConceptsPage />);
    expect(screen.getByText("概念一")).toBeInTheDocument();
    expect(screen.getByText("概念二")).toBeInTheDocument();
    expect(screen.getByText("概念三")).toBeInTheDocument();
    expect(screen.getByText(/第一人称生存割草/)).toBeInTheDocument();
  });
});
