import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import GraphPage from "@/app/(workbench)/graph/page";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("GraphPage", () => {
  it("lists relations with a downgraded low-confidence edge", async () => {
    renderWithClient(<GraphPage />);
    await waitFor(() => {
      expect(screen.getAllByText(/symbolic tactical UI/).length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText("弱证据").length).toBeGreaterThan(0);
  });

  it("shows the source claim and evidence path when a relation is selected", async () => {
    const user = userEvent.setup();
    renderWithClient(<GraphPage />);
    await waitFor(() => {
      expect(screen.getAllByText(/Balatro/).length).toBeGreaterThan(0);
    });
    const relationButtons = screen.getAllByRole("button");
    const balatroButton = relationButtons.find((b) =>
      /familiar card rules/.test(b.textContent ?? ""),
    );
    expect(balatroButton).toBeDefined();
    await user.click(balatroButton!);
    expect(screen.getByText("证据路径")).toBeInTheDocument();
    expect(
      screen.getByText(/recognizable poker hand logic/),
    ).toBeInTheDocument();
  });
});
