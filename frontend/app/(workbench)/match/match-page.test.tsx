import { afterEach, describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MatchPage from "@/app/(workbench)/match/page";
import type { OpportunityMatchResult } from "@/lib/types";

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

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
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
    expect(
      screen.getByText("图谱规模较小，新颖度判断偏粗。"),
    ).toBeInTheDocument();
    expect(screen.getByText(/不做在线多人/)).toBeInTheDocument();
  });

  it("shows an empty state when no areas match", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch(200, { profile_id: "p", areas: [], rejected: [], warnings: [] }),
    );
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText(/未匹配到候选/)).toBeInTheDocument(),
    );
  });

  it("shows an error state on a 500", async () => {
    vi.stubGlobal("fetch", mockFetch(500, {}));
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText("加载失败")).toBeInTheDocument(),
    );
  });
});
