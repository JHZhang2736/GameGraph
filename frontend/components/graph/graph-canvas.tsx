"use client";

import { useEffect, useState } from "react";
import Graph from "graphology";
import {
  SigmaContainer,
  useLoadGraph,
  useRegisterEvents,
  useSetSettings,
  useSigma,
} from "@react-sigma/core";
import { useWorkerLayoutForceAtlas2 } from "@react-sigma/layout-forceatlas2";
import { EdgeCurvedArrowProgram } from "@sigma/edge-curve";
import "@react-sigma/core/lib/style.css";
import type { GraphData } from "@/lib/data";
import { nodeColor, nodeSize } from "@/components/graph/node-style";
import { edgeColor, edgeSize } from "@/components/graph/edge-style";
import { relationLabel } from "@/components/graph/relation-labels";

const DIMMED_NODE = "#e2e8f0";
const DIMMED_EDGE = "#eef2f7";

// 由边列表统计每个节点的连接数,用于节点尺寸。
function degreeMap(graph: GraphData): Map<string, number> {
  const m = new Map<string, number>();
  for (const e of graph.edges) {
    m.set(e.source, (m.get(e.source) ?? 0) + 1);
    m.set(e.target, (m.get(e.target) ?? 0) + 1);
  }
  return m;
}

const SIGMA_SETTINGS = {
  renderEdgeLabels: true,
  defaultEdgeType: "curved",
  edgeProgramClasses: { curved: EdgeCurvedArrowProgram },
  labelDensity: 0.07,
  labelGridCellSize: 60,
  zIndex: true,
};

function GraphController({
  graph,
  onSelectNode,
  onSelectEdge,
}: {
  graph: GraphData;
  onSelectNode?: (id: string) => void;
  onSelectEdge?: (id: string) => void;
}) {
  const sigma = useSigma();
  const loadGraph = useLoadGraph();
  const registerEvents = useRegisterEvents();
  const setSettings = useSetSettings();
  const { start, kill } = useWorkerLayoutForceAtlas2({
    settings: { slowDown: 10 },
  });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // 数据变化时(挂载 / 展开邻居)重建 graphology 图并重跑布局。
  useEffect(() => {
    const g = new Graph({ multi: true, type: "directed" });
    const degrees = degreeMap(graph);
    const count = Math.max(graph.nodes.length, 1);
    graph.nodes.forEach((n, i) => {
      g.addNode(n.id, {
        label: n.label,
        size: nodeSize(degrees.get(n.id) ?? 0),
        color: nodeColor(n.node_type),
        // 环形播种初始坐标,交给 FA2 收敛。
        x: Math.cos((i / count) * 2 * Math.PI),
        y: Math.sin((i / count) * 2 * Math.PI),
      });
    });
    graph.edges.forEach((e) => {
      if (!g.hasNode(e.source) || !g.hasNode(e.target)) return;
      if (g.hasEdge(e.id)) return;
      g.addEdgeWithKey(e.id, e.source, e.target, {
        label: relationLabel(e.relation),
        type: "curved",
        color: edgeColor(e),
        size: edgeSize(e),
      });
    });
    loadGraph(g);
    start();
    return () => kill();
  }, [graph, loadGraph, start, kill]);

  // 注册交互:点击展开 / 看证据,hover 记录,拖拽。
  useEffect(() => {
    let dragged: string | null = null;
    registerEvents({
      clickNode: (e) => onSelectNode?.(e.node),
      clickEdge: (e) => onSelectEdge?.(e.edge),
      enterNode: (e) => setHoveredNode(e.node),
      leaveNode: () => setHoveredNode(null),
      downNode: (e) => {
        dragged = e.node;
        sigma.getGraph().setNodeAttribute(dragged, "highlighted", true);
      },
      mousemovebody: (e) => {
        if (!dragged) return;
        const pos = sigma.viewportToGraph(e);
        sigma.getGraph().setNodeAttribute(dragged, "x", pos.x);
        sigma.getGraph().setNodeAttribute(dragged, "y", pos.y);
        e.preventSigmaDefault();
        e.original.preventDefault();
        e.original.stopPropagation();
      },
      mouseup: () => {
        if (dragged) sigma.getGraph().removeNodeAttribute(dragged, "highlighted");
        dragged = null;
      },
    });
  }, [registerEvents, sigma, onSelectNode, onSelectEdge]);

  // hover 高亮:淡化非邻居节点;默认隐藏边标签,仅在 hover 焦点的相连边上显示。
  useEffect(() => {
    setSettings({
      nodeReducer: (node, data) => {
        if (!hoveredNode) return data;
        const g = sigma.getGraph();
        if (node === hoveredNode || g.areNeighbors(hoveredNode, node)) return data;
        return { ...data, color: DIMMED_NODE, label: "" };
      },
      edgeReducer: (edge, data) => {
        const g = sigma.getGraph();
        if (!hoveredNode) return { ...data, label: "" };
        const [s, t] = g.extremities(edge);
        if (s === hoveredNode || t === hoveredNode) return data;
        return { ...data, color: DIMMED_EDGE, label: "" };
      },
    });
  }, [hoveredNode, setSettings, sigma]);

  return null;
}

export function GraphCanvas({
  graph,
  onSelectEdge,
  onSelectNode,
}: {
  graph: GraphData;
  onSelectEdge?: (edgeId: string) => void;
  onSelectNode?: (nodeId: string) => void;
}) {
  return (
    <div className="h-[560px] rounded-lg border">
      <SigmaContainer
        style={{ height: "100%", width: "100%" }}
        settings={SIGMA_SETTINGS}
      >
        <GraphController
          graph={graph}
          onSelectNode={onSelectNode}
          onSelectEdge={onSelectEdge}
        />
      </SigmaContainer>
    </div>
  );
}
