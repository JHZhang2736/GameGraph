import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ClaimRow } from "@/components/artifacts/claim-row";
import { ConstraintTag } from "@/components/artifacts/constraint-tag";
import type { DesignClaim } from "@/lib/types";

const claim: DesignClaim = {
  id: "claim_low",
  subject: "symbolic tactical UI",
  relation: "may_reduce",
  object: "animation burden",
  explanation: "Abstract feedback can reduce art load.",
};

describe("artifact components", () => {
  it("renders a claim's subject, relation, object and explanation", () => {
    render(<ClaimRow claim={claim} />);
    expect(
      screen.getByText(/symbolic tactical UI · may_reduce · animation burden/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Abstract feedback can reduce art load."),
    ).toBeInTheDocument();
  });

  it("marks a hard constraint", () => {
    const { container } = render(
      <ConstraintTag
        constraint={{ id: "c1", type: "hard", statement: "No online." }}
      />,
    );
    expect(screen.getByText("No online.")).toBeInTheDocument();
    expect(container.querySelector('[data-constraint="hard"]')).not.toBeNull();
  });
});
