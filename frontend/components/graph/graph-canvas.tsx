"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { GraphData, GraphEdge } from "@/lib/data";

const EDGE_COLOR: Record<GraphEdge["confidence"], string> = {
  high: "#16a34a",
  medium: "#71717a",
  low: "#d97706",
};

export function GraphCanvas({
  graph,
  onSelectEdge,
}: {
  graph: GraphData;
  onSelectEdge?: (edgeId: string) => void;
}) {
  const nodes = useMemo<Node[]>(
    () =>
      graph.nodes.map((node, index) => ({
        id: node.id,
        position: { x: (index % 2) * 320, y: index * 90 },
        data: { label: node.label },
        style: { fontSize: 12, width: 220 },
      })),
    [graph.nodes],
  );

  const edges = useMemo<Edge[]>(
    () =>
      graph.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.relation,
        animated: edge.confidence === "low",
        style: {
          stroke: EDGE_COLOR[edge.confidence],
          strokeDasharray: edge.confidence === "low" ? "5 5" : undefined,
        },
      })),
    [graph.edges],
  );

  return (
    <div className="h-[520px] rounded-lg border">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        onEdgeClick={(_, edge) => onSelectEdge?.(edge.id)}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
