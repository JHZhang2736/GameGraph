import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProfilePage from "@/app/(workbench)/profile/page";

type User = ReturnType<typeof userEvent.setup>;

const EXAMPLE_TEXT =
  "我是 solo 开发者，程序能力强，美术能力弱，想做三个月内能验证的原型。" +
  "我喜欢 Balatro 和 Into the Breach，想要短局、系统性决策和战术预测。" +
  "不要做在线多人，我不想做长篇叙事内容，也不想做大量内容。";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

async function fillAndParse(user: User, text: string = EXAMPLE_TEXT) {
  const textarea = screen.getByLabelText("自由描述");
  await user.click(textarea);
  await user.paste(text);
  await user.click(screen.getByRole("button", { name: "解析画像" }));
}

describe("ProfilePage", () => {
  it("does not parse until the user asks", async () => {
    renderWithClient(<ProfilePage />);

    expect(screen.getByText("开发者画像")).toBeInTheDocument();
    expect(screen.getByLabelText("自由描述")).toBeInTheDocument();
    // No auto-parse on load: the preview placeholder shows, not the preview.
    expect(screen.getByText(/等待解析画像/)).toBeInTheDocument();
    expect(screen.queryByText("结构化预览")).not.toBeInTheDocument();
  });

  it("renders the structured preview only after parsing", async () => {
    const user = userEvent.setup();
    renderWithClient(<ProfilePage />);

    await fillAndParse(user);

    await waitFor(() => {
      expect(screen.getByText("结构化预览")).toBeInTheDocument();
    });
  });

  it("surfaces missing fields in the preview after parsing vague input", async () => {
    const user = userEvent.setup();
    renderWithClient(<ProfilePage />);

    await fillAndParse(
      user,
      "我是 solo 开发者，程序能力强，美术能力弱，想尽快做个原型。我想要短局，不要做在线多人。",
    );

    await waitFor(() => {
      expect(screen.getByText("缺少关键信息")).toBeInTheDocument();
    });
    // Time budget could not be inferred from "尽快"; its select sits at 缺失.
    expect((screen.getByLabelText("时间预算") as HTMLSelectElement).value).toBe("");
  });

  it("highlights hard constraints and enables confirmation when complete", async () => {
    const user = userEvent.setup();
    const { container } = renderWithClient(<ProfilePage />);

    await fillAndParse(user);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "确认画像" })).toBeEnabled();
    });
    expect(container.querySelector('[data-constraint="hard"]')).not.toBeNull();
  });

  it("disables confirmation when a blocking field is cleared", async () => {
    const user = userEvent.setup();
    renderWithClient(<ProfilePage />);

    await fillAndParse(user);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "确认画像" })).toBeEnabled();
    });

    await user.selectOptions(screen.getByLabelText("团队规模"), "");

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "确认画像" })).toBeDisabled();
    });
    expect(screen.getByText("缺少关键信息")).toBeInTheDocument();
  });

  it("lets the user edit a field via the dropdown", async () => {
    const user = userEvent.setup();
    renderWithClient(<ProfilePage />);

    await fillAndParse(user);
    await waitFor(() => {
      expect(screen.getByLabelText("程序能力")).toBeInTheDocument();
    });

    const programming = screen.getByLabelText("程序能力") as HTMLSelectElement;
    expect(programming.value).toBe("strong");
    await user.selectOptions(programming, "weak");
    expect(programming.value).toBe("weak");
  });

  it("confirms a complete draft into a DeveloperProfile", async () => {
    const user = userEvent.setup();
    renderWithClient(<ProfilePage />);

    await fillAndParse(user);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "确认画像" })).toBeEnabled();
    });
    await user.click(screen.getByRole("button", { name: "确认画像" }));

    await waitFor(() => {
      expect(screen.getByText("已确认画像")).toBeInTheDocument();
    });
  });
});
