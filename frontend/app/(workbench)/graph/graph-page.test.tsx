import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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
});
