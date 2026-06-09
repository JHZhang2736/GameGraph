import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConceptCardView } from "@/components/concept/concept-card";
import type { ConceptCard } from "@/lib/types";

const CARD: ConceptCard = {
  id: "concept|f|1",
  opportunity_frame_id: "f",
  title: "第一人称护符割草",
  one_sentence_concept: "用护符构筑在第一人称视角扛过兽潮",
  core_fantasy: "孤身靠 build 翻盘",
  core_loop: "探索→拾取→构筑→应对兽潮",
  main_player_decisions: ["先拿哪枚护符"],
  main_mechanics: ["护符定制"],
  reference_sources: ["vampire_survivors"],
  difference_from_references: "搬到第一人称的近身视野",
  fit_reason: "契合 solo 短局",
  production_risks: ["第一人称美术成本"],
  design_risks: ["视角削弱割草爽快"],
  novelty_reason: "第一人称割草稀缺",
  suggested_prototype_scope: "单关卡 + 3 枚护符",
};

describe("ConceptCardView", () => {
  it("renders title, one-sentence, and the full creative fields", () => {
    render(<ConceptCardView card={CARD} />);
    expect(screen.getByText("第一人称护符割草")).toBeInTheDocument();
    expect(screen.getByText(/用护符构筑/)).toBeInTheDocument();
    expect(screen.getByText("孤身靠 build 翻盘")).toBeInTheDocument();
    expect(screen.getByText("探索→拾取→构筑→应对兽潮")).toBeInTheDocument();
    expect(screen.getByText("先拿哪枚护符")).toBeInTheDocument();
    expect(screen.getByText("护符定制")).toBeInTheDocument();
    expect(screen.getByText("vampire_survivors")).toBeInTheDocument();
    expect(screen.getByText(/搬到第一人称/)).toBeInTheDocument();
    expect(screen.getByText("契合 solo 短局")).toBeInTheDocument();
    expect(screen.getByText("第一人称美术成本")).toBeInTheDocument();
    expect(screen.getByText("视角削弱割草爽快")).toBeInTheDocument();
    expect(screen.getByText("第一人称割草稀缺")).toBeInTheDocument();
    expect(screen.getByText("单关卡 + 3 枚护符")).toBeInTheDocument();
  });
});
