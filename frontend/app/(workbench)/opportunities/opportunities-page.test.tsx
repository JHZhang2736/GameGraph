import { afterEach, describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import OpportunitiesPage from "@/app/(workbench)/opportunities/page";
import { rememberLastFrameId, upsertFrame } from "@/lib/opportunity/frame-history";
import type { ConceptCard, OpportunityFrame } from "@/lib/types";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pushMock }) }));

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

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

function card(id: string): ConceptCard {
  return {
    id,
    opportunity_frame_id: "frame|a",
    title: "概念",
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
  vi.restoreAllMocks();
  pushMock.mockClear();
  localStorage.clear();
  sessionStorage.clear();
});

describe("OpportunitiesPage", () => {
  it("shows an empty state with a link to match when there is no history", () => {
    renderWithClient(<OpportunitiesPage />);
    expect(screen.getByText(/还没有机会框架/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /去机会匹配/ })).toBeInTheDocument();
  });

  it("renders frames from history newest-first", () => {
    upsertFrame(frame("frame|a", "区域A"));
    upsertFrame(frame("frame|b", "区域B"));
    renderWithClient(<OpportunitiesPage />);
    expect(screen.getByText("区域A")).toBeInTheDocument();
    expect(screen.getByText("区域B")).toBeInTheDocument();
  });

  it("auto-expands the just-generated frame", async () => {
    upsertFrame(frame("frame|a", "区域A"));
    rememberLastFrameId("frame|a");
    renderWithClient(<OpportunitiesPage />);
    expect(await screen.findByText("禁止方向")).toBeInTheDocument();
  });

  it("generates concepts, stores them, and navigates to /concepts", async () => {
    const user = userEvent.setup();
    upsertFrame(frame("frame|a", "区域A"));
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => [card("c1"), card("c2"), card("c3")],
      }),
    );
    renderWithClient(<OpportunitiesPage />);
    await user.click(screen.getByRole("button", { name: "生成概念" }));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/concepts"));
    const stored = JSON.parse(localStorage.getItem("gamegraph.latest-concepts")!);
    expect(stored.frame.id).toBe("frame|a");
    expect(stored.cards.map((c: ConceptCard) => c.id)).toEqual(["c1", "c2", "c3"]);
  });

  it("shows the 503 message and does not navigate when LLM is unconfigured", async () => {
    const user = userEvent.setup();
    upsertFrame(frame("frame|a", "区域A"));
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({}) }),
    );
    renderWithClient(<OpportunitiesPage />);
    await user.click(screen.getByRole("button", { name: "生成概念" }));
    await waitFor(() =>
      expect(screen.getByText(/需配置 LLM/)).toBeInTheDocument(),
    );
    expect(pushMock).not.toHaveBeenCalled();
  });
});
