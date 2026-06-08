import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import OpportunitiesPage from "@/app/(workbench)/opportunities/page";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("OpportunitiesPage", () => {
  it("shows the opportunity area and forbidden directions", async () => {
    renderWithClient(<OpportunitiesPage />);
    await waitFor(() => {
      expect(
        screen.getByText(/Low-art, short-run tactical rule manipulation/),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("禁止方向")).toBeInTheDocument();
    expect(screen.getByText("online multiplayer")).toBeInTheDocument();
  });
});
