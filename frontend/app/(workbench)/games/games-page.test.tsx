import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import GamesPage from "@/app/(workbench)/games/page";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("GamesPage", () => {
  it("lists seed games once loaded", async () => {
    renderWithClient(<GamesPage />);
    await waitFor(() => {
      expect(screen.getByText("Balatro")).toBeInTheDocument();
    });
    expect(screen.getByText("Into the Breach")).toBeInTheDocument();
    expect(screen.getByText("Baba Is You")).toBeInTheDocument();
  });
});
