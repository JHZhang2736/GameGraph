import { afterEach, describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MatchPage from "@/app/(workbench)/match/page";
import { goldenFlow } from "@/lib/fixtures/golden-flow";
import type { OpportunityFrame, OpportunityMatchResult } from "@/lib/types";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pushMock }) }));

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

const RESULT: OpportunityMatchResult = {
  profile_id: "dev_profile_1",
  areas: [
    {
      id: "opp|vampire_survivors|sub|Perspective|第一人称",
      anchor_game_id: "vampire_survivors",
      anchor_summary: "吸血鬼幸存者:弹幕生存 roguelite",
      transformation: {
        type: "substitute",
        dimension: "Perspective",
        from_value: "第三人称",
        to_value: "第一人称",
      },
      existing_combination_count: 0,
      evidence: {
        anchor_game_id: "vampire_survivors",
        target_value_game_ids: ["doom"],
        combination_game_ids: [],
      },
      risk_posture: "balanced",
      fit_reason: "契合短周期偏好。",
      risk_reason: "弹幕密度需调校。",
    },
  ],
  rejected: [
    {
      candidate_id: "opp|x|comb|Mechanic|在线匹配",
      rejection_reason: "与画像硬约束『不做在线多人』冲突。",
    },
  ],
  warnings: ["图谱规模较小，新颖度判断偏粗。"],
};

const FRAME: OpportunityFrame = {
  id: "frame|opp|vampire_survivors|sub|Perspective|第一人称",
  developer_profile_id: "dev_profile_1",
  opportunity_area: "第一人称弹幕生存",
  source_game_ids: ["doom"],
  related_mechanics: [],
  related_player_experiences: [],
  related_constraints: [],
  related_innovation_patterns: [],
  recommended_transformations: ["主变形"],
  forbidden_directions: ["禁止"],
  evidence_path: ["rel"],
  fit_reason: "f",
  risk_reason: "r",
};

afterEach(() => {
  vi.restoreAllMocks();
  pushMock.mockClear();
  localStorage.clear();
  sessionStorage.clear();
});

async function clickMatch() {
  const user = userEvent.setup();
  const button = await screen.findByRole("button", { name: "匹配机会" });
  await waitFor(() => expect(button).not.toBeDisabled());
  await user.click(button);
}

describe("MatchPage", () => {
  it("renders candidates, warnings and rejected reasons after matching", async () => {
    vi.stubGlobal("fetch", mockFetch(200, RESULT));
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument(),
    );
    expect(screen.getByText("平衡")).toBeInTheDocument();
    expect(screen.getByText("图谱规模较小，新颖度判断偏粗。")).toBeInTheDocument();
    expect(screen.getByText(/不做在线多人/)).toBeInTheDocument();
  });

  it("shows an empty state when no areas match", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch(200, { profile_id: "p", areas: [], rejected: [], warnings: [] }),
    );
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() => expect(screen.getByText(/未匹配到候选/)).toBeInTheDocument());
  });

  it("shows an error state on a 500", async () => {
    vi.stubGlobal("fetch", mockFetch(500, {}));
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() => expect(screen.getByText("加载失败")).toBeInTheDocument());
  });

  it("generates a frame, stores it in history, and navigates to /opportunities", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => RESULT })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => FRAME });
    vi.stubGlobal("fetch", fetchMock);
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "生成机会框架" }));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/opportunities"));
    const stored = JSON.parse(localStorage.getItem("gamegraph.opportunity-frames")!);
    expect(stored[0].id).toBe(FRAME.id);
    expect(sessionStorage.getItem("gamegraph.last-frame-id")).toBe(FRAME.id);
  });

  it("appends results into a persisted board", async () => {
    vi.stubGlobal("fetch", mockFetch(200, RESULT));
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument(),
    );
    // Key derived from the same fixture the page reads (getDeveloperProfile falls
    // back to goldenFlow.developer_profile when nothing is stored), so we don't
    // hardcode the id nor scan Object.keys(localStorage).
    const boardKey = `gamegraph.opportunity-board.${goldenFlow.developer_profile.id}`;
    const board = JSON.parse(localStorage.getItem(boardKey)!);
    expect(board.areas).toHaveLength(1);
    expect(board.seen_ids).toContain("opp|vampire_survivors|sub|Perspective|第一人称");
    expect(board.seen_ids).toContain("opp|x|comb|Mechanic|在线匹配");
  });

  it("restores the board on remount (survives refresh)", async () => {
    vi.stubGlobal("fetch", mockFetch(200, RESULT));
    const first = renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument(),
    );
    first.unmount();
    renderWithClient(<MatchPage />);
    await waitFor(() =>
      expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument(),
    );
  });

  it("clears the board", async () => {
    vi.stubGlobal("fetch", mockFetch(200, RESULT));
    const user = userEvent.setup();
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "清空看板" }));
    await waitFor(() =>
      expect(screen.queryByText("视角:第三人称 → 第一人称")).not.toBeInTheDocument(),
    );
  });
});
