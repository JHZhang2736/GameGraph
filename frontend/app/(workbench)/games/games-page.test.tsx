import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import GamesPage from "@/app/(workbench)/games/page";

vi.mock("@/lib/queries", async (orig) => {
  const actual = await orig<typeof import("@/lib/queries")>();
  return {
    ...actual,
    useGames: () => ({
      data: [
        { id: "game_hk", title: "Hollow Knight", short_description: "metroidvania" },
      ],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    }),
  };
});

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("GamesPage", () => {
  it("lists imported games and shows an import entry", async () => {
    renderWithClient(<GamesPage />);
    await waitFor(() => expect(screen.getByText("Hollow Knight")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /导入游戏/ })).toBeInTheDocument();
  });
});
