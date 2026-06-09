import type { RiskPosture, Transformation } from "@/lib/types";

const DIMENSION_LABELS: Record<string, string> = {
  Perspective: "视角",
  ArtStyle: "美术风格",
  Genre: "类型",
  Mechanic: "机制",
};

// 替代: "视角:第三人称 → 第一人称";组合: "借入机制:多用途道具"
export function formatTransformation(t: Transformation): string {
  const dim = DIMENSION_LABELS[t.dimension] ?? t.dimension;
  if (t.type === "substitute") {
    return `${dim}:${t.from_value ?? "?"} → ${t.to_value}`;
  }
  return `借入${dim}:${t.to_value}`;
}

// 越小越新颖。后端 rank 已过滤到 <=2,但对任意 n 容错。
export function formatNovelty(existingCombinationCount: number): string {
  return existingCombinationCount === 0
    ? "全新组合"
    : `稀有组合(图谱 ${existingCombinationCount} 款)`;
}

export interface RiskMeta {
  label: string;
  className: string;
}

export function riskPostureMeta(posture: RiskPosture): RiskMeta {
  switch (posture) {
    case "safe":
      return { label: "稳健", className: "border-green-300 bg-green-50 text-green-700" };
    case "balanced":
      return { label: "平衡", className: "border-amber-300 bg-amber-50 text-amber-700" };
    case "challenging":
      return { label: "挑战", className: "border-red-300 bg-red-50 text-red-700" };
  }
}
