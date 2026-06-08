"use client";

import { useState } from "react";
import { useGraph } from "@/lib/queries";
import { GraphCanvas } from "@/components/graph/graph-canvas";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";
import { ConfidenceBadge } from "@/components/artifacts/confidence-badge";
import { QualityBadge } from "@/components/artifacts/quality-badge";
import { EvidenceList } from "@/components/artifacts/evidence-list";
import { cn } from "@/lib/utils";

export default function GraphPage() {
  const { data, isLoading, isError, refetch } = useGraph();
  const [selected, setSelected] = useState<string | null>(null);

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;
  if (data.edges.length === 0) return <EmptyState message="图谱暂无关系" />;

  const selectedEdge = data.edges.find((edge) => edge.id === selected) ?? null;

  return (
    <div>
      <PageHeader
        title="知识图谱"
        description="由设计论断派生的可查询关系;低置信度关系以琥珀色虚线降级展示。"
      />
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <GraphCanvas graph={data} onSelectEdge={setSelected} />
        <aside className="space-y-3">
          {selectedEdge ? (
            <div className="rounded-lg border p-3">
              <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
                证据路径
              </h2>
              <div className="mb-1 text-sm font-medium">
                {selectedEdge.source} · {selectedEdge.relation} · {selectedEdge.target}
              </div>
              <div className="mb-2 flex items-center gap-2">
                {selectedEdge.confidence ? <ConfidenceBadge level={selectedEdge.confidence} /> : null}
                {selectedEdge.quality_status ? <QualityBadge status={selectedEdge.quality_status} /> : null}
              </div>
              <div className="mb-2 text-xs text-muted-foreground">
                来源论断:{selectedEdge.claim_id}
              </div>
              <EvidenceList evidence={selectedEdge.evidence} />
            </div>
          ) : (
            <p className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
              点击一条关系查看其来源论断与证据路径。
            </p>
          )}
          <div className="space-y-2">
            <h2 className="text-xs uppercase tracking-wide text-muted-foreground/70">
              关系列表
            </h2>
            {data.edges.map((edge) => (
              <button
                key={edge.id}
                type="button"
                onClick={() => setSelected(edge.id)}
                className={cn(
                  "w-full rounded-lg border p-3 text-left text-sm hover:bg-accent",
                  selected === edge.id && "ring-2 ring-primary",
                  (edge.confidence === "low" ||
                    edge.quality_status === "weak_evidence" ||
                    edge.quality_status === "conflicting") &&
                    "border-amber-200",
                )}
              >
                <div className="mb-1 font-medium">
                  {edge.source} · {edge.relation} · {edge.target}
                </div>
                <div className="flex items-center gap-2">
                  {edge.confidence ? <ConfidenceBadge level={edge.confidence} /> : null}
                  {edge.quality_status ? <QualityBadge status={edge.quality_status} /> : null}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  来源论断:{edge.claim_id}
                </div>
              </button>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
