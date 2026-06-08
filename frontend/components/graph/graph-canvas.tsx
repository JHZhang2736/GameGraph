"use client";

import { useEffect, useState } from "react";
import Graph, { MultiDirectedGraph } from "graphology";
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
  const { start, stop } = useWorkerLayoutForceAtlas2({
    settings: { slowDown: 10 },
  });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // 数据变化时(挂载 / 展开邻居)重建 graphology 图。useLoadGraph 会清空并
  // 重新导入到 sigma 持有的同一个图实例,故 FA2 worker 始终挂在活动图上。
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
  }, [graph, loadGraph]);

  // 力导向布局:数据变化(含展开)后重新跑一段时间收敛再自动停下,避免无限
  // 运行抢占拖拽。用 stop(可暂停可重启)而非 kill(永久销毁 worker);worker
  // 的销毁交由 hook 自身在卸载时处理。start/stop 在 layout 就绪后会改变身份,
  // 从而触发本 effect 重新运行并真正启动布局。
  useEffect(() => {
    start();
    const timer = window.setTimeout(() => stop(), 2000);
    return () => {
      window.clearTimeout(timer);
      stop();
    };
  }, [graph, start, stop]);

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
        const g = sigma.getGraph();
        // hoveredNode 可能指向已被重建图移除的旧节点(展开/换焦点时 leaveNode
        // 未触发),此时按"无 hover"处理,避免 areNeighbors 抛 NotFoundGraphError。
        if (!hoveredNode || !g.hasNode(hoveredNode)) return data;
        if (node === hoveredNode || g.areNeighbors(hoveredNode, node)) return data;
        return { ...data, color: DIMMED_NODE, label: "" };
      },
      edgeReducer: (edge, data) => {
        const g = sigma.getGraph();
        if (!hoveredNode || !g.hasNode(hoveredNode)) return { ...data, label: "" };
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
        graph={MultiDirectedGraph}
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
