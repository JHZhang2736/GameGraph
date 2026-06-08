import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProfilePage from "@/app/(workbench)/profile/page";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("ProfilePage", () => {
  it("highlights the hard constraint", async () => {
    const { container } = renderWithClient(<ProfilePage />);
    await waitFor(() => {
      expect(screen.getByText("开发者画像")).toBeInTheDocument();
    });
    const hard = container.querySelector('[data-constraint="hard"]');
    expect(hard).not.toBeNull();
    expect(hard?.textContent).toContain("Do not require online multiplayer.");
  });
});
