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
import { cn } from "@/lib/utils";

export default function GraphPage() {
  const { data, isLoading, isError, refetch } = useGraph();
  const [selected, setSelected] = useState<string | null>(null);

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;
  if (data.edges.length === 0) return <EmptyState message="图谱暂无关系" />;

  return (
    <div>
      <PageHeader
        title="知识图谱"
        description="由设计论断派生的可查询关系;低置信度关系以琥珀色虚线降级展示。"
      />
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <GraphCanvas graph={data} onSelectEdge={setSelected} />
        <aside className="space-y-2">
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
                  edge.quality_status === "weak_evidence") &&
                  "border-amber-200",
              )}
            >
              <div className="mb-1 font-medium">
                {edge.source} · {edge.relation} · {edge.target}
              </div>
              <div className="flex items-center gap-2">
                <ConfidenceBadge level={edge.confidence} />
                <QualityBadge status={edge.quality_status} />
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                来源论断:{edge.claim_id}
              </div>
            </button>
          ))}
        </aside>
      </div>
    </div>
  );
}
