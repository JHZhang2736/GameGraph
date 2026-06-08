import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ImportPage from "@/app/(workbench)/games/import/page";

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ImportPage />
    </QueryClientProvider>,
  );
}

describe("ImportPage validation", () => {
  it("shows a field error for invalid JSON document", async () => {
    renderPage();
    const textarea = screen.getByPlaceholderText(/粘贴/);
    fireEvent.change(textarea, { target: { value: '{"candidate":{}}' } });
    fireEvent.click(screen.getByRole("button", { name: /校验/ }));
    await waitFor(() =>
      expect(screen.getByText(/校验未通过/)).toBeInTheDocument(),
    );
  });

  it("rejects non-JSON text", async () => {
    renderPage();
    const textarea = screen.getByPlaceholderText(/粘贴/);
    fireEvent.change(textarea, { target: { value: "not json" } });
    fireEvent.click(screen.getByRole("button", { name: /校验/ }));
    await waitFor(() => expect(screen.getByText(/无法解析 JSON/)).toBeInTheDocument());
  });
});
