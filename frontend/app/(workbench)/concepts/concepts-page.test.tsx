import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ConceptsPage from "@/app/(workbench)/concepts/page";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("ConceptsPage", () => {
  it("shows the concept with its difference, risks, and evaluation category", async () => {
    renderWithClient(<ConceptsPage />);
    await waitFor(() => {
      expect(screen.getByText("Ruleforge Tactics")).toBeInTheDocument();
    });
    expect(screen.getByText(/与参考作品的差异/)).toBeInTheDocument();
    expect(screen.getByText(/制作风险/)).toBeInTheDocument();
    expect(screen.getByText(/设计风险/)).toBeInTheDocument();
    expect(screen.getByText("平衡型")).toBeInTheDocument();
  });
});
