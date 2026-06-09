import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppSidebar } from "@/components/shell/app-sidebar";

describe("AppSidebar", () => {
  it("renders both nav groups and their items", () => {
    render(<AppSidebar />);
    expect(screen.getByText("资料库")).toBeInTheDocument();
    expect(screen.getByText("创意流程")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "机会框架" })).toHaveAttribute(
      "href",
      "/opportunities",
    );
    expect(screen.getByRole("link", { name: "机会匹配" })).toHaveAttribute(
      "href",
      "/match",
    );
    expect(screen.getByRole("link", { name: "总览" })).toBeInTheDocument();
  });
});
