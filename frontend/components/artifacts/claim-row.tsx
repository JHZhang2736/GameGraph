import type { DesignClaim } from "@/lib/types";

export function ClaimRow({ claim }: { claim: DesignClaim }) {
  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="font-medium">
          {claim.subject} · {claim.relation} · {claim.object}
        </span>
      </div>
      <p className="text-sm text-muted-foreground">{claim.explanation}</p>
    </div>
  );
}
