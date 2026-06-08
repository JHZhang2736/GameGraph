import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import PrototypePage from "@/app/(workbench)/prototype/page";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("PrototypePage", () => {
  it("shows both success and failure signals", async () => {
    renderWithClient(<PrototypePage />);
    await waitFor(() => {
      expect(screen.getByText("成功信号")).toBeInTheDocument();
    });
    expect(screen.getByText("失败信号")).toBeInTheDocument();
    expect(
      screen.getByText(/player can explain a rule consequence/),
    ).toBeInTheDocument();
    expect(screen.getByText(/player says outcomes feel arbitrary/)).toBeInTheDocument();
  });
});
