"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { OpportunityFrame } from "@/lib/types";

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

export function OpportunityFrameCard({
  frame,
  defaultOpen = false,
  highlighted = false,
  onRemove,
}: {
  frame: OpportunityFrame;
  defaultOpen?: boolean;
  highlighted?: boolean;
  onRemove?: (id: string) => void;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [primary, ...secondary] = frame.recommended_transformations;

  return (
    <section
      className={`rounded-lg border ${
        highlighted ? "border-primary ring-1 ring-primary/30" : ""
      }`}
    >
      <header className="flex items-center gap-3 p-4">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          className="flex flex-1 items-center gap-3 text-left"
        >
          <span className="text-xs text-muted-foreground/70">{open ? "▾" : "▸"}</span>
          <span className="flex-1 font-medium">{frame.opportunity_area}</span>
          {primary ? (
            <span className="rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground">
              {primary}
            </span>
          ) : null}
        </button>
        {onRemove ? (
          <Button type="button" variant="ghost" size="xs" onClick={() => onRemove(frame.id)}>
            移除
          </Button>
        ) : null}
      </header>

      {open ? (
        <div className="space-y-6 border-t p-4">
          {frame.warnings && frame.warnings.length > 0 ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <ul className="list-disc space-y-1 pl-5">
                {frame.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h3 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
                相关机制
              </h3>
              <Chips items={frame.related_mechanics} />
            </div>
            <div>
              <h3 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
                相关玩家体验
              </h3>
              <Chips items={frame.related_player_experiences} />
            </div>
          </div>

          <div>
            <h3 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
              推荐变形
            </h3>
            <ul className="space-y-1 text-sm">
              {primary ? (
                <li>
                  <span className="mr-2 rounded-full border border-primary px-2 py-0.5 text-xs text-primary">
                    主变形
                  </span>
                  {primary}
                </li>
              ) : null}
              {secondary.map((t) => (
                <li key={t}>
                  <span className="mr-2 rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
                    次变形
                  </span>
                  {t}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-lg border border-red-200 bg-red-50 p-3">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-red-700">
              禁止方向
            </h3>
            <ul className="list-disc pl-5 text-sm text-red-700">
              {frame.forbidden_directions.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <h3 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
                来源游戏
              </h3>
              <Chips items={frame.source_game_ids} />
            </div>
            <div>
              <h3 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
                相关制作约束
              </h3>
              <Chips items={frame.related_constraints} />
            </div>
            <div>
              <h3 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
                相关创新模式
              </h3>
              <Chips items={frame.related_innovation_patterns} />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h3 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
                适配理由
              </h3>
              <p className="text-sm text-muted-foreground">{frame.fit_reason}</p>
            </div>
            <div>
              <h3 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
                风险理由
              </h3>
              <p className="text-sm text-muted-foreground">{frame.risk_reason}</p>
            </div>
          </div>

          <div>
            <h3 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
              证据路径
            </h3>
            <Chips items={frame.evidence_path} />
          </div>
        </div>
      ) : null}
    </section>
  );
}
