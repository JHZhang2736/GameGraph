"use client";

import { useEffect, useMemo, useState } from "react";
import { useGames } from "@/lib/queries";
import { getNeighbors, type GraphData, type GraphEdge, type GraphNode, type NeighborhoodResult } from "@/lib/data";
import { GraphCanvas } from "@/components/graph/graph-canvas";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/shell/view-states";
import { ConfidenceBadge } from "@/components/artifacts/confidence-badge";
import { QualityBadge } from "@/components/artifacts/quality-badge";
import { EvidenceList } from "@/components/artifacts/evidence-list";

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

  if (gamesLoading) return <LoadingState />;
  if (gamesError) return <ErrorState onRetry={() => refetch()} />;
  if (!games || games.length === 0) return <EmptyState message="暂无已入库游戏,先去导入" />;

  return (
    <div>
      <PageHeader title="知识图谱" description="聚焦 + 按需展开;低置信度关系以琥珀色虚线降级展示。" />
      <div className="mb-3 flex items-center gap-2">
        <button type="button" onClick={reroll} className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
          {"🎲 换一个"}
        </button>
        <span className="text-sm text-muted-foreground">{"焦点节点已加载,点节点可展开邻居。"}</span>
      </div>
      {truncated ? (
        <p className="mb-2 rounded-md bg-amber-50 p-2 text-sm text-amber-700">
          {"结果过多,已截断;请缩小范围或加筛选。"}
        </p>
      ) : null}
      {loadError ? (
        <p className="mb-2 rounded-md bg-destructive/10 p-2 text-sm text-destructive">{"加载邻域失败,请重试。"}</p>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <GraphCanvas
          graph={graph}
          onSelectEdge={setSelectedEdge}
          onSelectNode={(id) => focusOn(id, false)}
        />
        <aside className="space-y-3">
          {selected ? (
            <div className="rounded-lg border p-3">
              <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">{"证据路径"}</h2>
              <div className="mb-1 text-sm font-medium">
                {selected.source} {"·"} {selected.relation} {"·"} {selected.target}
              </div>
              <div className="mb-2 flex items-center gap-2">
                {selected.confidence ? <ConfidenceBadge level={selected.confidence} /> : null}
                {selected.quality_status ? <QualityBadge status={selected.quality_status} /> : null}
              </div>
              {selected.claim_id ? (
                <div className="mb-2 text-xs text-muted-foreground">{"来源论断:"}{selected.claim_id}</div>
              ) : null}
              <EvidenceList evidence={selected.evidence} />
            </div>
          ) : (
            <p className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
              {"点击一条关系查看证据路径;点击节点展开其邻居。"}
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}
