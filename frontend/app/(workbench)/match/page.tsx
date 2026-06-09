"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  EmptyState,
  ErrorState,
  PageHeader,
} from "@/components/shell/view-states";
import { OpportunityCandidateCard } from "@/components/opportunity/opportunity-candidate-card";
import { rememberLastFrameId, upsertFrame } from "@/lib/opportunity/frame-history";
import {
  useBuildOpportunityFrame,
  useDeveloperProfile,
  useMatchOpportunities,
} from "@/lib/queries";
import type { OpportunityArea } from "@/lib/types";

export default function MatchPage() {
  const router = useRouter();
  const { data: profile } = useDeveloperProfile();
  const match = useMatchOpportunities();
  const buildFrame = useBuildOpportunityFrame();
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const result = match.data;

  function runMatch() {
    if (profile) match.mutate(profile);
  }

  function generate(area: OpportunityArea) {
    if (!profile) return;
    setGeneratingId(area.id);
    buildFrame.mutate(
      { profile, area },
      {
        onSuccess: (frame) => {
          upsertFrame(frame);
          rememberLastFrameId(frame.id);
          router.push("/opportunities");
        },
        onSettled: () => setGeneratingId(null),
      },
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="机会匹配" description="从你的画像匹配出的创新机会" />

      <div>
        <Button type="button" disabled={!profile || match.isPending} onClick={runMatch}>
          {match.isPending ? "匹配中…" : "匹配机会"}
        </Button>
      </div>

      {match.isError ? <ErrorState onRetry={runMatch} /> : null}
      {buildFrame.isError ? <ErrorState /> : null}

      {result ? (
        <div className="space-y-6">
          {result.warnings.length > 0 ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <ul className="list-disc space-y-1 pl-5">
                {result.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {result.areas.length > 0 ? (
            <section className="grid gap-4 md:grid-cols-2">
              {result.areas.map((area) => (
                <OpportunityCandidateCard
                  key={area.id}
                  area={area}
                  onGenerate={generate}
                  isGenerating={generatingId === area.id}
                />
              ))}
            </section>
          ) : (
            <EmptyState message="未匹配到候选，可能与图谱规模或画像约束有关。" />
          )}

          {result.rejected.length > 0 ? (
            <section className="rounded-lg border border-dashed p-4">
              <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
                被排除的方向
              </h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                {result.rejected.map((r) => (
                  <li key={r.candidate_id}>{r.rejection_reason}</li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
