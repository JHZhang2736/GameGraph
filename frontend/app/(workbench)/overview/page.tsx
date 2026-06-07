"use client";

import Link from "next/link";
import { useGoldenFlow } from "@/lib/queries";
import { ErrorState, LoadingState, PageHeader } from "@/components/shell/view-states";

const STAGES: { label: string; href: string; count: (f: ReturnType<typeof useGoldenFlow>["data"]) => number }[] =
  [
    { label: "种子游戏", href: "/games", count: (f) => f?.seed_games.length ?? 0 },
    { label: "设计论断", href: "/games", count: (f) => f?.design_claims.length ?? 0 },
    { label: "图谱关系", href: "/graph", count: (f) => f?.graph_relations.length ?? 0 },
    { label: "机会框架", href: "/opportunities", count: (f) => (f?.opportunity_frame ? 1 : 0) },
    { label: "概念卡", href: "/concepts", count: (f) => f?.concept_cards.length ?? 0 },
    { label: "原型简报", href: "/prototype", count: (f) => (f?.prototype_brief ? 1 : 0) },
  ];

export default function OverviewPage() {
  const { data, isLoading, isError, refetch } = useGoldenFlow();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div>
      <PageHeader
        title="总览"
        description="核心流程:种子游戏 → 设计论断 → 图谱 → 开发者画像 → 机会框架 → 概念卡 → 原型简报"
      />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {STAGES.map((stage) => (
          <Link
            key={stage.label}
            href={stage.href}
            className="rounded-lg border p-4 hover:bg-accent"
          >
            <div className="text-2xl font-semibold">{stage.count(data)}</div>
            <div className="text-sm text-muted-foreground">{stage.label}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
