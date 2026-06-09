import type { GraphEdge } from "@/lib/data";

// 低置信度或弱/冲突证据 → 降级展示(琥珀 + 更细线,不用虚线)。
export function isDowngraded(edge: GraphEdge): boolean {
  return (
    edge.confidence === "low" ||
    edge.quality_status === "weak_evidence" ||
    edge.quality_status === "conflicting"
  );
}

const DOWNGRADED_COLOR = "#d97706"; // amber
const CONFIDENCE_COLOR: Record<string, string> = {
  high: "#16a34a",
  medium: "#71717a",
};
const DEFAULT_EDGE_COLOR = "#94a3b8";

export function edgeColor(edge: GraphEdge): string {
  if (isDowngraded(edge)) return DOWNGRADED_COLOR;
  if (edge.confidence && CONFIDENCE_COLOR[edge.confidence]) {
    return CONFIDENCE_COLOR[edge.confidence];
  }
  return DEFAULT_EDGE_COLOR;
}

export function edgeSize(edge: GraphEdge): number {
  return isDowngraded(edge) ? 1 : 2.5;
}
