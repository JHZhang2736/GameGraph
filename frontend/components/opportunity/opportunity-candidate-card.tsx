import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  formatNovelty,
  formatTransformation,
  riskPostureMeta,
} from "@/lib/opportunity/format";
import type { OpportunityArea } from "@/lib/types";

export function OpportunityCandidateCard({ area }: { area: OpportunityArea }) {
  const risk = riskPostureMeta(area.risk_posture);
  const targetCount = area.evidence.target_value_game_ids.length;
  const comboCount = area.evidence.combination_game_ids.length;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex rounded-full border px-2 py-0.5 text-xs ${risk.className}`}
          >
            {risk.label}
          </span>
          <span className="inline-flex rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
            {formatNovelty(area.existing_combination_count)}
          </span>
        </div>
        <CardTitle>{formatTransformation(area.transformation)}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="text-muted-foreground">{area.anchor_summary}</p>
        <div>
          <h3 className="text-xs uppercase tracking-wide text-muted-foreground/70">
            适配理由
          </h3>
          <p>{area.fit_reason}</p>
        </div>
        <div>
          <h3 className="text-xs uppercase tracking-wide text-muted-foreground/70">
            风险理由
          </h3>
          <p>{area.risk_reason}</p>
        </div>
        <p className="text-xs text-muted-foreground/70">
          证据:锚点 {area.anchor_game_id} · 目标值佐证 {targetCount} 款
          {comboCount > 0 ? ` · 组合佐证 ${comboCount} 款` : ""}
        </p>
      </CardContent>
    </Card>
  );
}
