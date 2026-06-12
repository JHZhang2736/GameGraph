"use client";

import type { ImportDocument } from "@/lib/import/schema";
import { ClaimRow } from "@/components/artifacts/claim-row";

function Chips({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="mb-2">
      <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">{label}</div>
      <div className="flex flex-wrap gap-1">
        {items.map((item, i) => (
          <span key={`${item}-${i}`} className="rounded border bg-muted px-2 py-0.5 text-xs">{item}</span>
        ))}
      </div>
    </div>
  );
}

export function ImportPreview({
  document,
  onBack,
  onConfirm,
  pending,
}: {
  document: ImportDocument;
  onBack: () => void;
  onConfirm: () => void;
  pending: boolean;
}) {
  const { candidate, profile, claims } = document;
  return (
    <div className="space-y-4">
      <div className="rounded-lg border p-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">{candidate.title}</h2>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">{profile.one_sentence_summary}</p>
        <p className="mt-1 text-xs text-muted-foreground">{"核心钩子:"}{profile.core_hook}{" · 核心循环:"}{profile.core_loop}</p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <Chips label="主要机制" items={profile.main_mechanics} />
        <Chips label="主要体验" items={profile.main_player_experiences} />
        <Chips label="主要动作" items={profile.main_player_actions} />
        <Chips label="主要决策" items={profile.main_player_decisions} />
      </div>

      <Chips label="参考价值标签" items={profile.reference_value_tags} />

      <div>
        <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">设计论断</div>
        <div className="space-y-2">
          {claims.map((claim) => (
            <ClaimRow key={claim.id} claim={claim} />
          ))}
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <button type="button" onClick={onBack} className="rounded-md border px-4 py-1.5 text-sm hover:bg-accent">
          返回修改
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={pending}
          className="rounded-md bg-primary px-4 py-1.5 text-sm text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {pending ? "入库中…" : "确认入库"}
        </button>
      </div>
    </div>
  );
}
