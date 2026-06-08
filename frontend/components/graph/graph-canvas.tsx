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

const NODE_COLORS: Record<string, string> = {
  Game: "#4f46e5",
  Mechanic: "#818cf8",
  PlayerAction: "#818cf8",
  PlayerDecision: "#818cf8",
  Experience: "#14b8a6",
  Concept: "#f87171",
  ReferenceTag: "#f59e0b",
};

const DEFAULT_NODE_COLOR = "#94a3b8";

export function nodeColor(nodeType: string): string {
  return NODE_COLORS[nodeType] ?? DEFAULT_NODE_COLOR;
}

function isDowngraded(edge: GraphEdge): boolean {
  return (
    edge.confidence === "low" ||
    edge.quality_status === "weak_evidence" ||
    edge.quality_status === "conflicting"
  );
}

const EDGE_COLOR: Record<string, string> = {
  high: "#16a34a",
  medium: "#71717a",
  low: "#d97706",
};

export function GraphCanvas({
  graph,
  onSelectEdge,
  onSelectNode,
}: {
  graph: GraphData;
  onSelectEdge?: (edgeId: string) => void;
  onSelectNode?: (nodeId: string) => void;
}) {
  const nodes = useMemo<Node[]>(
    () =>
      graph.nodes.map((node, index) => ({
        id: node.id,
        position: {
          x: 250 + Math.cos((index / Math.max(graph.nodes.length, 1)) * 2 * Math.PI) * 220,
          y: 250 + Math.sin((index / Math.max(graph.nodes.length, 1)) * 2 * Math.PI) * 220,
        },
        data: { label: node.label },
        style: {
          fontSize: 12,
          width: 160,
          border: `2px solid ${nodeColor(node.node_type)}`,
        },
      })),
    [graph.nodes],
  );

  const edges = useMemo<Edge[]>(
    () =>
      graph.edges.map((edge) => {
        const downgraded = isDowngraded(edge);
        const stroke = downgraded
          ? "#d97706"
          : edge.confidence
            ? EDGE_COLOR[edge.confidence]
            : "#94a3b8";
        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.relation,
          animated: downgraded,
          style: { stroke, strokeDasharray: downgraded ? "5 5" : undefined },
        };
      }),
    [graph.edges],
  );

  return (
    <div className="h-[560px] rounded-lg border">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        onEdgeClick={(_, edge) => onSelectEdge?.(edge.id)}
        onNodeClick={(_, node) => onSelectNode?.(node.id)}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
