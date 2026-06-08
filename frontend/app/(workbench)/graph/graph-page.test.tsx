import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const neighborsMock = vi.fn();

vi.mock("@/lib/queries", async (orig) => {
  const actual = await orig<typeof import("@/lib/queries")>();
  return {
    ...actual,
    useGames: () => ({
      data: [{ id: "game_hk", title: "Hollow Knight", short_description: "mv", confidence: "high", quality_status: "reviewed" }],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    }),
  };
});

vi.mock("@/lib/data", async (orig) => {
  const actual = await orig<typeof import("@/lib/data")>();
  return { ...actual, getNeighbors: (...args: unknown[]) => neighborsMock(...args) };
});

// 画布依赖 WebGL,在 jsdom 不可渲染;页面测试只关心页面逻辑,故 stub 掉画布。
vi.mock("@/components/graph/graph-canvas", () => ({
  GraphCanvas: () => null,
}));

import GraphPage from "@/app/(workbench)/graph/page";

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><GraphPage /></QueryClientProvider>);
}

beforeEach(() => {
  neighborsMock.mockReset();
  neighborsMock.mockResolvedValue({
    focus: { id: "game_hk", label: "Hollow Knight", node_type: "Game" },
    nodes: [{ id: "platforming", label: "platforming", node_type: "Mechanic" }],
    edges: [{ id: "e1", source: "game_hk", target: "platforming", relation: "HAS_MECHANIC", evidence: [] }],
    truncated: false,
  });
});

describe("GraphPage", () => {
  it("loads a random focus on mount and renders its relation", async () => {
    renderPage();
    await waitFor(() => expect(neighborsMock).toHaveBeenCalled());
    expect((neighborsMock.mock.calls[0][0] as { nodeId: string }).nodeId).toBe("game_hk");
  });

  it("shows a truncation warning when truncated is true", async () => {
    neighborsMock.mockResolvedValue({
      focus: { id: "game_hk", label: "Hollow Knight", node_type: "Game" },
      nodes: [], edges: [], truncated: true,
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/结果过多/)).toBeInTheDocument());
  });
});
