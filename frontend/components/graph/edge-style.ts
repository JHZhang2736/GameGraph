import type { GraphEdge } from "@/lib/data";

const DEFAULT_EDGE_COLOR = "#94a3b8";

export function edgeColor(_edge: GraphEdge): string {
  return DEFAULT_EDGE_COLOR;
}

export function edgeSize(_edge: GraphEdge): number {
  return 2;
}
