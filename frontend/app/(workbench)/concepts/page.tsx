"use client";

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { EmptyState, PageHeader } from "@/components/shell/view-states";
import { ConceptCardView } from "@/components/concept/concept-card";
import { loadLatestConcepts, subscribeConcepts } from "@/lib/concept/concept-store";

export default function ConceptsPage() {
  const latest = useSyncExternalStore(subscribeConcepts, loadLatestConcepts, () => null);

  if (!latest || latest.cards.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader title="概念卡" description="由机会框架生成的具体概念" />
        <EmptyState message="还没有概念，先去机会框架选一个方向生成。" />
        <Link
          href="/opportunities"
          className="text-sm text-primary underline-offset-4 hover:underline"
        >
          去机会框架 →
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="概念卡"
        description={`为「${latest.frame.opportunity_area}」生成的概念`}
      />
      <div className="grid items-start gap-4 md:grid-cols-2 xl:grid-cols-3">
        {latest.cards.map((card) => (
          <ConceptCardView key={card.id} card={card} />
        ))}
      </div>
    </div>
  );
}
