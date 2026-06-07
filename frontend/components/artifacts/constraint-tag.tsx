import type { DeveloperConstraint, ConstraintType } from "@/lib/types";
import { cn } from "@/lib/utils";

const LABEL: Record<ConstraintType, string> = {
  hard: "硬性约束",
  strong_preference: "强偏好",
  soft_preference: "软偏好",
};

const STYLE: Record<ConstraintType, string> = {
  hard: "border-red-200 bg-red-50 text-red-700",
  strong_preference: "border-amber-200 bg-amber-50 text-amber-700",
  soft_preference: "border-zinc-200 bg-zinc-50 text-zinc-600",
};

export function ConstraintTag({ constraint }: { constraint: DeveloperConstraint }) {
  return (
    <div
      data-constraint={constraint.type}
      className={cn("rounded-md border px-3 py-2 text-sm", STYLE[constraint.type])}
    >
      <span className="mr-2 text-xs font-semibold">{LABEL[constraint.type]}</span>
      {constraint.statement}
    </div>
  );
}
