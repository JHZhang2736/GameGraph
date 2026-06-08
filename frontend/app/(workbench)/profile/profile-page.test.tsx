import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProfilePage from "@/app/(workbench)/profile/page";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("ProfilePage", () => {
  it("renders the mixed developer profile workbench", async () => {
    renderWithClient(<ProfilePage />);

    expect(screen.getByText("开发者画像")).toBeInTheDocument();
    expect(screen.getByLabelText("自由描述")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("结构化预览")).toBeInTheDocument();
    });
  });

  it("updates the preview after parsing edited text", async () => {
    const user = userEvent.setup();
    renderWithClient(<ProfilePage />);

    const textarea = screen.getByLabelText("自由描述");
    await user.clear(textarea);
    await user.type(
      textarea,
      "我是 solo 开发者，程序能力强，美术能力弱，想尽快做个原型。我想要短局，不要做在线多人。",
    );
    await user.click(screen.getByRole("button", { name: "解析画像" }));

    await waitFor(() => {
      expect(screen.getByText("缺少关键信息")).toBeInTheDocument();
    });
    expect(screen.getByText("time_budget")).toBeInTheDocument();
  });

  it("highlights hard constraints and enables confirmation when complete", async () => {
    const { container } = renderWithClient(<ProfilePage />);

    await waitFor(() => {
      expect(
        screen.getByText("Do not require online multiplayer."),
      ).toBeInTheDocument();
    });

    const hard = container.querySelector('[data-constraint="hard"]');
    expect(hard).not.toBeNull();
    expect(hard?.textContent).toContain("Do not require online multiplayer.");
    expect(screen.getByRole("button", { name: "确认画像" })).toBeEnabled();
  });
});
