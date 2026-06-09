import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OpportunityFrameCard } from "@/components/opportunity/opportunity-frame-card";
import type { OpportunityFrame } from "@/lib/types";

const FRAME: OpportunityFrame = {
  id: "frame|opp|a",
  developer_profile_id: "p",
  opportunity_area: "低美术短周期的规则操控",
  source_game_ids: ["baba_is_you"],
  related_mechanics: ["规则改写"],
  related_player_experiences: ["顿悟时刻"],
  related_constraints: ["内容产能有限"],
  related_innovation_patterns: ["规则即玩法"],
  recommended_transformations: ["把规则改写压成 5 分钟关卡", "引入合作视角"],
  forbidden_directions: ["online multiplayer"],
  evidence_path: ["relation-1"],
  fit_reason: "契合低美术预算。",
  risk_reason: "关卡设计成本高。",
  warnings: ["图谱规模偏小。"],
};

describe("OpportunityFrameCard", () => {
  it("shows the area title and primary transformation when collapsed", () => {
    render(<OpportunityFrameCard frame={FRAME} />);
    expect(screen.getByText("低美术短周期的规则操控")).toBeInTheDocument();
    expect(screen.getByText("把规则改写压成 5 分钟关卡")).toBeInTheDocument();
    expect(screen.queryByText("禁止方向")).not.toBeInTheDocument();
  });

  it("reveals full detail with primary/secondary split when expanded", () => {
    render(<OpportunityFrameCard frame={FRAME} defaultOpen />);
    expect(screen.getByText("禁止方向")).toBeInTheDocument();
    expect(screen.getByText("主变形")).toBeInTheDocument();
    expect(screen.getByText("次变形")).toBeInTheDocument();
    expect(screen.getByText("引入合作视角")).toBeInTheDocument();
    expect(screen.getByText("图谱规模偏小。")).toBeInTheDocument();
  });
});
