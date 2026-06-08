"use client";

import Link from "next/link";
import type { ImportSummary } from "@/lib/types";

export function ImportResult({
  summary,
  onImportAnother,
}: {
  summary: ImportSummary;
  onImportAnother: () => void;
}) {
  return (
    <div className="space-y-3 rounded-lg border p-4">
      <p className="font-medium text-green-700">{"✓ 入库成功"}</p>
      <p className="text-sm text-muted-foreground">
        {"写入:"}{summary.mechanics_written}{" 机制 · "}{summary.experiences_written}{" 体验 · "}
        {summary.tags_written}{" 标签 · "}{summary.concepts_written}{" 概念 · "}{summary.claims_written}{" 论断"}
      </p>
      <div className="flex gap-2">
        <Link
          href={`/graph?focus=${encodeURIComponent(summary.game_id)}`}
          className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:opacity-90"
        >
          {"🔍 在图谱中查看"}
        </Link>
        <Link
          href={`/games/${encodeURIComponent(summary.game_id)}`}
          className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent"
        >
          查看游戏档案
        </Link>
        <button
          type="button"
          onClick={onImportAnother}
          className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent"
        >
          再导入一个
        </button>
      </div>
    </div>
  );
}
