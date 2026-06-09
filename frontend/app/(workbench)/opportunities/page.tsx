"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
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

export default function OpportunitiesPage() {
  const frames = useSyncExternalStore(subscribeFrames, loadFrames, () => []);
  // lazy 初始化时 peek（纯读，不改 storage），使高亮项首帧即展开；清除放到 effect。
  const [lastId] = useState<string | null>(() => peekLastFrameId());

  useEffect(() => {
    clearLastFrameId();
  }, []);

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
      <div className="space-y-4">
        {frames.map((frame) => (
          <OpportunityFrameCard
            key={frame.id}
            frame={frame}
            defaultOpen={frame.id === lastId}
            highlighted={frame.id === lastId}
            onRemove={removeFrame}
          />
        ))}
      </div>
    </div>
  );
}
