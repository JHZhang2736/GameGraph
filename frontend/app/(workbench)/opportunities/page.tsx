"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { EmptyState, PageHeader } from "@/components/shell/view-states";
import { OpportunityFrameCard } from "@/components/opportunity/opportunity-frame-card";
import {
  clearLastFrameId,
  loadFrames,
  peekLastFrameId,
  removeFrame,
  subscribeFrames,
} from "@/lib/opportunity/frame-history";
import { saveConcepts } from "@/lib/concept/concept-store";
import { ConceptGenerationError } from "@/lib/data";
import { useGenerateConcepts } from "@/lib/queries";
import type { OpportunityFrame } from "@/lib/types";

function generationErrorMessage(error: unknown): string {
  if (error instanceof ConceptGenerationError) {
    if (error.status === 503) return "需配置 LLM 才能生成概念。";
    if (error.status === 502) return "概念生成失败，可重试。";
  }
  return "加载失败";
}

export default function OpportunitiesPage() {
  const router = useRouter();
  const frames = useSyncExternalStore(subscribeFrames, loadFrames, () => []);
  // lazy 初始化时 peek（纯读，不改 storage），使高亮项首帧即展开；清除放到 effect。
  const [lastId] = useState<string | null>(() => peekLastFrameId());
  const generate = useGenerateConcepts();
  const [generatingId, setGeneratingId] = useState<string | null>(null);

  useEffect(() => {
    clearLastFrameId();
  }, []);

  function generateConcepts(frame: OpportunityFrame) {
    setGeneratingId(frame.id);
    generate.mutate(frame, {
      onSuccess: (cards) => {
        saveConcepts(frame, cards);
        router.push("/concepts");
      },
      onSettled: () => setGeneratingId(null),
    });
  }

  if (frames.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader title="机会框架" description="从机会匹配生成的框架历史" />
        <EmptyState message="还没有机会框架，先去机会匹配选一个方向。" />
        <Link
          href="/match"
          className="text-sm text-primary underline-offset-4 hover:underline"
        >
          去机会匹配 →
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="机会框架" description="从机会匹配生成的框架历史" />
      {generate.isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {generationErrorMessage(generate.error)}
        </div>
      ) : null}
      <div className="space-y-4">
        {frames.map((frame) => (
          <OpportunityFrameCard
            key={frame.id}
            frame={frame}
            defaultOpen={frame.id === lastId}
            highlighted={frame.id === lastId}
            onRemove={removeFrame}
            onGenerateConcepts={generateConcepts}
            isGenerating={generatingId === frame.id}
          />
        ))}
      </div>
    </div>
  );
}
