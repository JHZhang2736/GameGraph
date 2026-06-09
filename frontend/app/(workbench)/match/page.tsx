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
import { loadBoard, saveBoard, clearBoard } from "@/lib/opportunity/board-storage";
import type { OpportunityArea, RejectedOpportunity } from "@/lib/types";

export default function MatchPage() {
  const router = useRouter();
  const { data: profile } = useDeveloperProfile();
  const match = useMatchOpportunities();
  const buildFrame = useBuildOpportunityFrame();
  const [generatingId, setGeneratingId] = useState<string | null>(null);

  // Accumulating discovery board state
  const [areas, setAreas] = useState<OpportunityArea[]>([]);
  const [seenIds, setSeenIds] = useState<string[]>([]);
  const [latestRejected, setLatestRejected] = useState<RejectedOpportunity[]>([]);
  const [latestWarnings, setLatestWarnings] = useState<string[]>([]);
  const [lastProfileId, setLastProfileId] = useState<string | null>(null);

  // Render-time restore: when the profile changes (or first appears), load the
  // persisted board from storage. This mirrors the profile page's render-time-sync
  // pattern (adjusting state during render when an external value changes is the
  // supported way to react to such changes).
  if (profile && profile.id !== lastProfileId) {
    setLastProfileId(profile.id);
    const board = loadBoard(profile.id);
    setAreas(board.areas);
    setSeenIds(board.seen_ids);
    setLatestRejected([]);
    setLatestWarnings([]);
  }

  function runMatch() {
    if (!profile) return;
    match.mutate(
      { profile, seenIds },
      {
        onSuccess: (result) => {
          const newAreas = result.areas.filter((a) => !areas.some((x) => x.id === a.id));
          const merged = [...areas, ...newAreas];
          const nextSeen = Array.from(
            new Set([
              ...seenIds,
              ...result.areas.map((a) => a.id),
              ...result.rejected.map((r) => r.candidate_id),
            ]),
          );
          setAreas(merged);
          setSeenIds(nextSeen);
          setLatestRejected(result.rejected);
          setLatestWarnings(result.warnings);
          saveBoard(profile.id, { areas: merged, seen_ids: nextSeen });
        },
      },
    );
  }

  function clearAll() {
    if (!profile) return;
    clearBoard(profile.id);
    setAreas([]);
    setSeenIds([]);
    setLatestRejected([]);
    setLatestWarnings([]);
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

      <div className="flex gap-2">
        <Button type="button" disabled={!profile || match.isPending} onClick={runMatch}>
          {match.isPending ? "匹配中…" : areas.length === 0 ? "匹配机会" : "再来一批"}
        </Button>
        {areas.length > 0 ? (
          <Button variant="outline" type="button" onClick={clearAll}>
            清空看板
          </Button>
        ) : null}
      </div>

      {match.isError ? <ErrorState onRetry={runMatch} /> : null}
      {buildFrame.isError ? <ErrorState /> : null}

      <div className="space-y-6">
        {latestWarnings.length > 0 ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            <ul className="list-disc space-y-1 pl-5">
              {latestWarnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {areas.length > 0 ? (
          <section className="grid gap-4 md:grid-cols-2">
            {areas.map((area) => (
              <OpportunityCandidateCard
                key={area.id}
                area={area}
                onGenerate={generate}
                isGenerating={generatingId === area.id}
              />
            ))}
          </section>
        ) : match.isSuccess ? (
          <EmptyState message="未匹配到候选，可能与图谱规模或画像约束有关。" />
        ) : null}

        {latestRejected.length > 0 ? (
          <section className="rounded-lg border border-dashed p-4">
            <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
              被排除的方向
            </h2>
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {latestRejected.map((r) => (
                <li key={r.candidate_id}>{r.rejection_reason}</li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </div>
  );
}
