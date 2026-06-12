import { useState } from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MultiSelectChips } from "@/components/profile/multi-select-chips";

function Harness({
  initial = [],
  options,
}: {
  initial?: string[];
  options?: string[];
}) {
  const [value, setValue] = useState<string[]>(initial);
  return (
    <MultiSelectChips id="exp" value={value} onChange={setValue} options={options} />
  );
}

describe("MultiSelectChips", () => {
  it("adds a value picked from the options dropdown", async () => {
    const user = userEvent.setup();
    render(<Harness options={["欢乐混乱", "战斗精通"]} />);

    await user.selectOptions(screen.getByLabelText("exp-add"), "欢乐混乱");

    expect(screen.getByText("欢乐混乱")).toBeInTheDocument();
    // 已选项不再出现在「添加…」下拉里
    expect(
      screen.queryByRole("option", { name: "欢乐混乱" }),
    ).not.toBeInTheDocument();
  });

  it("adds a free-text value on Enter (for fields without a fixed vocab)", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    const input = screen.getByPlaceholderText("输入后回车添加");
    await user.type(input, "在线多人{Enter}");

    expect(screen.getByText("在线多人")).toBeInTheDocument();
    expect((input as HTMLInputElement).value).toBe("");
  });

  it("removes a chip via its × button", async () => {
    const user = userEvent.setup();
    render(<Harness initial={["欢乐混乱"]} />);

    await user.click(screen.getByRole("button", { name: "移除 欢乐混乱" }));

    expect(screen.queryByText("欢乐混乱")).not.toBeInTheDocument();
  });

  it("does not add duplicates", async () => {
    const user = userEvent.setup();
    render(<Harness initial={["欢乐混乱"]} />);

    const input = screen.getByPlaceholderText("输入后回车添加");
    await user.type(input, "欢乐混乱{Enter}");

    expect(screen.getAllByText("欢乐混乱")).toHaveLength(1);
  });
});
