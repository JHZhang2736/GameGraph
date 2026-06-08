import { afterEach, describe, it, expect } from "vitest";
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
  afterEach(() => {
    localStorage.clear();
  });

  it("shows an empty editable preview without parsing on load", async () => {
    renderWithClient(<ProfilePage />);

    expect(screen.getByText("开发者画像")).toBeInTheDocument();
    expect(screen.getByLabelText("自由描述")).toBeInTheDocument();
    // The structured preview is available immediately, but nothing is parsed:
    // required fields sit at 缺失 and confirmation is gated.
    expect(screen.getByText("结构化预览")).toBeInTheDocument();
    expect(screen.getByText("缺少关键信息")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "确认画像" })).toBeDisabled();
    expect((screen.getByLabelText("团队规模") as HTMLSelectElement).value).toBe("");
  });

  it("lets the user complete the profile by selecting fields, no free text", async () => {
    const user = userEvent.setup();
    renderWithClient(<ProfilePage />);

    // Pick canonical values directly from the Chinese dropdowns.
    await user.selectOptions(screen.getByLabelText("团队规模"), "solo");
    await user.selectOptions(screen.getByLabelText("时间预算"), "three month prototype");
    await user.selectOptions(screen.getByLabelText("程序能力"), "strong");
    await user.selectOptions(screen.getByLabelText("美术能力"), "weak");
    await user.selectOptions(screen.getByLabelText("内容生产能力"), "limited");

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "确认画像" })).toBeEnabled();
    });
  });

  it("renders Chinese option labels in the dropdowns", async () => {
    renderWithClient(<ProfilePage />);

    const teamSize = screen.getByLabelText("团队规模") as HTMLSelectElement;
    const labels = Array.from(teamSize.options).map((option) => option.text);
    expect(labels).toContain("独立开发者（单人）");
    expect(labels).toContain("小团队");
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
    // Wait for the parse to populate the field (the preview renders immediately,
    // so we must wait on the value, not just the element).
    await waitFor(() => {
      expect((screen.getByLabelText("程序能力") as HTMLSelectElement).value).toBe(
        "strong",
      );
    });

    const programming = screen.getByLabelText("程序能力") as HTMLSelectElement;
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

  it("restores a confirmed profile from storage when the page is re-entered", async () => {
    const user = userEvent.setup();
    const first = renderWithClient(<ProfilePage />);

    await fillAndParse(user);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "确认画像" })).toBeEnabled();
    });
    await user.click(screen.getByRole("button", { name: "确认画像" }));
    await waitFor(() => {
      expect(screen.getByText("已确认画像")).toBeInTheDocument();
    });

    // Leave and re-enter the page with a fresh component + query client. The
    // confirmed profile must come back from storage without any re-parsing.
    first.unmount();
    renderWithClient(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("已确认画像")).toBeInTheDocument();
    });
    // The editable draft is re-seeded from the stored profile so it stays editable.
    expect((screen.getByLabelText("团队规模") as HTMLSelectElement).value).toBe("solo");
  });
});
