import type { ConfidenceLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

const LABEL: Record<ConfidenceLevel, string> = {
  high: "置信度 高",
  medium: "置信度 中",
  low: "置信度 低",
};

const STYLE: Record<ConfidenceLevel, string> = {
  high: "bg-green-100 text-green-700",
  medium: "bg-zinc-100 text-zinc-700",
  low: "bg-amber-100 text-amber-700",
};

export function ConfidenceBadge({ level }: { level: ConfidenceLevel }) {
  return (
    <span
      data-confidence={level}
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-xs font-semibold",
        STYLE[level],
      )}
    >
      {LABEL[level]}
    </span>
  );
}
