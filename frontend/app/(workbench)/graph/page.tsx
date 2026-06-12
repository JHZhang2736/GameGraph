"use client";

import { useEffect, useMemo, useState } from "react";
import { useGames } from "@/lib/queries";
import { getNeighbors, type GraphData, type GraphEdge, type GraphNode, type NeighborhoodResult } from "@/lib/data";
import dynamic from "next/dynamic";

// 画布(后续将换成 Sigma)依赖 WebGL/window,禁用 SSR/构建预渲染。
// page 已是 Client Component,故 next/dynamic 的 ssr:false 在此合法
// (见 node_modules/next/dist/docs 的 lazy-loading 指南)。
const GraphCanvas = dynamic(
  () => import("@/components/graph/graph-canvas").then((m) => m.GraphCanvas),
  {
    ssr: false,
    loading: () => (
      <div className="h-full w-full animate-pulse rounded-lg border bg-muted/30" />
    ),
  },
);
import { EmptyState, ErrorState, LoadingState } from "@/components/shell/view-states";
import { GraphLegend } from "@/components/graph/graph-legend";

function mergeNeighborhood(prev: GraphData, next: NeighborhoodResult): GraphData {
  const nodeMap = new Map<string, GraphNode>(prev.nodes.map((n) => [n.id, n]));
  nodeMap.set(next.focus.id, next.focus);
  for (const n of next.nodes) nodeMap.set(n.id, n);
  const edgeMap = new Map<string, GraphEdge>(prev.edges.map((e) => [e.id, e]));
  for (const e of next.edges) edgeMap.set(e.id, e);
  return { nodes: [...nodeMap.values()], edges: [...edgeMap.values()] };
}

export default function GraphPage() {
  const { data: games, isLoading: gamesLoading, isError: gamesError, refetch } = useGames();
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [truncated, setTruncated] = useState(false);
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [hoverNodeId, setHoverNodeId] = useState<string | null>(null);

  async function focusOn(nodeId: string, replace: boolean) {
    try {
      const result = await getNeighbors({ nodeId });
      setLoadError(false);
      setTruncated(result.truncated);
      setGraph((prev) =>
        replace ? mergeNeighborhood({ nodes: [], edges: [] }, result) : mergeNeighborhood(prev, result),
      );
    } catch {
      setLoadError(true);
    }
  }

  useEffect(() => {
    if (!games || games.length === 0) return;
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("focus");
    const focusId = requested ?? games[Math.floor(Math.random() * games.length)].id;
    // focusOn 仅在 await 之后 setState(异步),不会造成同步级联渲染;挂载时按需取焦点邻域本就需在 effect 内发起。
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void focusOn(focusId, true);
  }, [games]);

  function reroll() {
    if (!games || games.length === 0) return;
    void focusOn(games[Math.floor(Math.random() * games.length)].id, true);
  }

  const selected = useMemo(
    () => graph.edges.find((e) => e.id === selectedEdge) ?? null,
    [graph.edges, selectedEdge],
  );

  // 图例只显示当前图里实际出现的节点类型。
  const presentTypes = useMemo(
    () => Array.from(new Set(graph.nodes.map((n) => n.node_type))),
    [graph.nodes],
  );

  // 当前 hover/点击的节点类型,用于在图例里高亮对应项。
  const hoverType = useMemo(
    () =>
      hoverNodeId
        ? (graph.nodes.find((n) => n.id === hoverNodeId)?.node_type ?? null)
        : null,
    [graph.nodes, hoverNodeId],
  );

  if (gamesLoading) return <LoadingState />;
  if (gamesError) return <ErrorState onRetry={() => refetch()} />;
  if (!games || games.length === 0) return <EmptyState message="暂无已入库游戏,先去导入" />;

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h1 className="text-lg font-semibold">{"知识图谱"}</h1>
        <button type="button" onClick={reroll} className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
          {"🎲 换一个"}
        </button>
        <span className="text-sm text-muted-foreground">{"点节点展开邻居,点边查看关系详情。"}</span>
      </div>
      {truncated ? (
        <p className="mb-2 rounded-md bg-amber-50 p-2 text-sm text-amber-700">
          {"结果过多,已截断;请缩小范围或加筛选。"}
        </p>
      ) : null}
      {loadError ? (
        <p className="mb-2 rounded-md bg-destructive/10 p-2 text-sm text-destructive">{"加载邻域失败,请重试。"}</p>
      ) : null}
      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[1fr_320px]">
        <div className="relative min-h-0">
          <GraphCanvas
            graph={graph}
            onSelectEdge={setSelectedEdge}
            onSelectNode={(id) => focusOn(id, false)}
            onHoverNode={setHoverNodeId}
          />
          <GraphLegend
            types={presentTypes}
            highlight={hoverType}
            className="absolute left-3 top-3 z-10"
          />
        </div>
        <aside className="min-h-0 space-y-3 overflow-auto">
          {selected ? (
            <div className="rounded-lg border p-3">
              <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">{"关系"}</h2>
              <div className="mb-1 text-sm font-medium">
                {selected.source} {"·"} {selected.relation} {"·"} {selected.target}
              </div>
              {selected.claim_id ? (
                <div className="text-xs text-muted-foreground">{"来源论断:"}{selected.claim_id}</div>
              ) : null}
            </div>
          ) : (
            <p className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
              {"点击一条关系查看详情;点击节点展开其邻居。"}
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}
