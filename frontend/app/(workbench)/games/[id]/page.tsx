"use client";

import { use } from "react";
import { useGameProfile } from "@/lib/queries";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";
import { ClaimRow } from "@/components/artifacts/claim-row";
import { ConfidenceBadge } from "@/components/artifacts/confidence-badge";
import { QualityBadge } from "@/components/artifacts/quality-badge";

export default function GameProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data, isLoading, isError, refetch } = useGameProfile(id);

  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState onRetry={() => refetch()} />;
  if (!data) return <EmptyState message="未找到该游戏" />;

  const { game, profile, claims } = data;

  return (
    <div className="space-y-6">
      <div>
        <PageHeader title={game.title} description={game.short_description} />
        {profile ? (
          <div className="flex flex-wrap items-center gap-2">
            {profile.reference_value_tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground"
              >
                {tag}
              </span>
            ))}
            <span className="ml-2 flex items-center gap-2">
              <ConfidenceBadge level={profile.confidence} />
              <QualityBadge status={profile.quality_status} />
            </span>
          </div>
        ) : null}
      </div>

      {profile ? (
        <section className="rounded-lg border p-4">
          <p className="mb-3 text-sm">{profile.one_sentence_summary}</p>
          <dl className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
            <div>
              <dt className="text-muted-foreground">核心循环</dt>
              <dd>{profile.core_loop}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">主要机制</dt>
              <dd>{profile.main_mechanics.join("、")}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">主要体验</dt>
              <dd>{profile.main_experiences.join("、")}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">不可复制风险</dt>
              <dd>{profile.hard_to_copy_risks.join("、")}</dd>
            </div>
          </dl>
        </section>
      ) : (
        <EmptyState message="该游戏暂无设计档案" />
      )}

      <section>
        <h2 className="mb-3 text-xs uppercase tracking-wide text-muted-foreground/70">
          设计论断
        </h2>
        {claims.length === 0 ? (
          <EmptyState message="暂无设计论断" />
        ) : (
          <div className="space-y-3">
            {claims.map((claim) => (
              <ClaimRow key={claim.id} claim={claim} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
