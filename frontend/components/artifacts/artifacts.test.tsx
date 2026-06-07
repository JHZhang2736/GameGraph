import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceBadge } from "@/components/artifacts/confidence-badge";
import { QualityBadge } from "@/components/artifacts/quality-badge";
import { ClaimRow } from "@/components/artifacts/claim-row";
import { ConstraintTag } from "@/components/artifacts/constraint-tag";
import { EvidenceList } from "@/components/artifacts/evidence-list";
import type { DesignClaim } from "@/lib/types";

const lowClaim: DesignClaim = {
  id: "claim_low",
  subject: "symbolic tactical UI",
  relation: "may_reduce",
  object: "animation burden",
  explanation: "Abstract feedback can reduce art load.",
  evidence: [
    {
      title: "Curator hypothesis",
      quote_or_summary: "Expected to be cheaper than animation-heavy combat.",
      notes: "Weak evidence.",
    },
  ],
  confidence: "low",
  quality_status: "weak_evidence",
};

describe("artifact components", () => {
  it("labels confidence level", () => {
    render(<ConfidenceBadge level="high" />);
    expect(screen.getByText(/置信度 高/)).toBeInTheDocument();
  });

  it("flags weak evidence as a downgraded quality status", () => {
    const { container } = render(<QualityBadge status="weak_evidence" />);
    expect(screen.getByText("弱证据")).toBeInTheDocument();
    expect(container.querySelector('[data-downgraded="true"]')).not.toBeNull();
  });

  it("does not downgrade a reviewed status", () => {
    const { container } = render(<QualityBadge status="reviewed" />);
    expect(container.querySelector('[data-downgraded="true"]')).toBeNull();
  });

  it("renders a low-confidence claim with both downgrade signals", () => {
    render(<ClaimRow claim={lowClaim} />);
    expect(screen.getByText(/置信度 低/)).toBeInTheDocument();
    expect(screen.getByText("弱证据")).toBeInTheDocument();
    expect(screen.getByText(/Curator hypothesis/)).toBeInTheDocument();
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

  it("links the evidence title when a url is present", () => {
    render(
      <EvidenceList
        evidence={[{ title: "Steam page", url: "https://example.com/x", notes: "n" }]}
      />,
    );
    const link = screen.getByRole("link", { name: "Steam page" });
    expect(link).toHaveAttribute("href", "https://example.com/x");
  });
});
