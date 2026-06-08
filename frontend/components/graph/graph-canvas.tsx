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

const EDGE_COLOR: Record<string, string> = {
  high: "#16a34a",
  medium: "#71717a",
  low: "#d97706",
};

function isDowngraded(edge: GraphEdge): boolean {
  return (
    edge.confidence === "low" ||
    edge.quality_status === "weak_evidence" ||
    edge.quality_status === "conflicting"
  );
}

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
      graph.edges.map((edge) => {
        const downgraded = isDowngraded(edge);
        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.relation,
          animated: downgraded,
          style: {
            stroke: downgraded ? "#d97706" : edge.confidence ? EDGE_COLOR[edge.confidence] : "#94a3b8",
            strokeDasharray: downgraded ? "5 5" : undefined,
          },
        };
      }),
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
