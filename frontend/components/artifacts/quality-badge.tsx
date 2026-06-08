import type { QualityStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const LABEL: Record<QualityStatus, string> = {
  draft: "草稿",
  reviewed: "已评审",
  weak_evidence: "弱证据",
  conflicting: "证据冲突",
};

// weak_evidence and conflicting must be visibly downgraded.
const DOWNGRADED: Record<QualityStatus, boolean> = {
  draft: false,
  reviewed: false,
  weak_evidence: true,
  conflicting: true,
};

export function QualityBadge({ status }: { status: QualityStatus }) {
  const downgraded = DOWNGRADED[status];
  return (
    <span
      data-quality={status}
      data-downgraded={downgraded ? "true" : undefined}
      className={cn(
        "inline-flex rounded-full border px-2 py-0.5 text-xs",
        downgraded
          ? "border-amber-200 bg-amber-50 text-amber-700"
          : "border-zinc-200 bg-zinc-50 text-zinc-600",
      )}
    >
      {LABEL[status]}
    </span>
  );
}
