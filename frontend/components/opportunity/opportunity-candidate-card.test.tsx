import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OpportunityCandidateCard } from "@/components/opportunity/opportunity-candidate-card";
import type { OpportunityArea } from "@/lib/types";

const AREA: OpportunityArea = {
  id: "opp|vampire_survivors|sub|Perspective|第一人称",
  anchor_game_id: "vampire_survivors",
  anchor_summary: "吸血鬼幸存者:自动攻击的弹幕生存 roguelite",
  transformation: {
    type: "substitute",
    dimension: "Perspective",
    from_value: "第三人称",
    to_value: "第一人称",
  },
  existing_combination_count: 0,
  evidence: {
    anchor_game_id: "vampire_survivors",
    target_value_game_ids: ["doom", "ultrakill"],
    combination_game_ids: [],
  },
  risk_posture: "balanced",
  fit_reason: "契合短周期、强系统性的偏好。",
  risk_reason: "第一人称弹幕密度需要重新调校。",
};

describe("OpportunityCandidateCard", () => {
  it("renders the transformation, novelty, risk label, summary and reasons", () => {
    render(<OpportunityCandidateCard area={AREA} />);
    expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument();
    expect(screen.getByText("全新组合")).toBeInTheDocument();
    expect(screen.getByText("平衡")).toBeInTheDocument();
    expect(
      screen.getByText("吸血鬼幸存者:自动攻击的弹幕生存 roguelite"),
    ).toBeInTheDocument();
    expect(screen.getByText("契合短周期、强系统性的偏好。")).toBeInTheDocument();
    expect(screen.getByText("第一人称弹幕密度需要重新调校。")).toBeInTheDocument();
  });
});
