import { afterEach, describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import OpportunitiesPage from "@/app/(workbench)/opportunities/page";
import { rememberLastFrameId, upsertFrame } from "@/lib/opportunity/frame-history";
import type { OpportunityFrame } from "@/lib/types";

function frame(id: string, area: string): OpportunityFrame {
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

afterEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe("OpportunitiesPage", () => {
  it("shows an empty state with a link to match when there is no history", () => {
    render(<OpportunitiesPage />);
    expect(screen.getByText(/还没有机会框架/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /去机会匹配/ })).toBeInTheDocument();
  });

  it("renders frames from history newest-first", () => {
    upsertFrame(frame("frame|a", "区域A"));
    upsertFrame(frame("frame|b", "区域B"));
    render(<OpportunitiesPage />);
    expect(screen.getByText("区域A")).toBeInTheDocument();
    expect(screen.getByText("区域B")).toBeInTheDocument();
  });

  it("auto-expands the just-generated frame", async () => {
    upsertFrame(frame("frame|a", "区域A"));
    rememberLastFrameId("frame|a");
    render(<OpportunitiesPage />);
    expect(await screen.findByText("禁止方向")).toBeInTheDocument();
  });
});
