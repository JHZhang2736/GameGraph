"use client";

import { useOpportunityFrame } from "@/lib/queries";
import {
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";

function Chips({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span
          key={item}
          className="rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

export default function OpportunitiesPage() {
  const { data, isLoading, isError, refetch } = useOpportunityFrame();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div className="space-y-6">
      <PageHeader title="机会框架" description={data.opportunity_area} />

      <section className="grid gap-4 md:grid-cols-2">
        <div>
          <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
            相关机制
          </h2>
          <Chips items={data.related_mechanics} />
        </div>
        <div>
          <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
            相关玩家体验
          </h2>
          <Chips items={data.related_player_experiences} />
        </div>
        <div>
          <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
            推荐变形
          </h2>
          <ul className="list-disc pl-5 text-sm">
            {data.recommended_transformations.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50 p-3">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-red-700">
            禁止方向
          </h2>
          <ul className="list-disc pl-5 text-sm text-red-700">
            {data.forbidden_directions.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div>
          <h2 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
            适配理由
          </h2>
          <p className="text-sm text-muted-foreground">{data.fit_reason}</p>
        </div>
        <div>
          <h2 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
            风险理由
          </h2>
          <p className="text-sm text-muted-foreground">{data.risk_reason}</p>
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
          证据路径
        </h2>
        <Chips items={data.evidence_path} />
      </section>
    </div>
  );
}
