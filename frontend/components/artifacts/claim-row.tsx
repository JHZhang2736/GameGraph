import type { DesignClaim } from "@/lib/types";
import { ConfidenceBadge } from "@/components/artifacts/confidence-badge";
import { QualityBadge } from "@/components/artifacts/quality-badge";
import { EvidenceList } from "@/components/artifacts/evidence-list";
import { cn } from "@/lib/utils";

export function ClaimRow({ claim }: { claim: DesignClaim }) {
  const downgraded =
    claim.confidence === "low" ||
    claim.quality_status === "weak_evidence" ||
    claim.quality_status === "conflicting";
  return (
    <div
      className={cn(
        "rounded-lg border p-3",
        downgraded ? "border-amber-200" : "border-border",
      )}
    >
      <div className="mb-2 flex items-center gap-2">
        <span className="font-medium">
          {claim.subject} · {claim.relation} · {claim.object}
        </span>
        <span className="ml-auto flex items-center gap-2">
          <ConfidenceBadge level={claim.confidence} />
          <QualityBadge status={claim.quality_status} />
        </span>
      </div>
      <p className="mb-2 text-sm text-muted-foreground">{claim.explanation}</p>
      <EvidenceList evidence={claim.evidence} />
    </div>
  );
}
