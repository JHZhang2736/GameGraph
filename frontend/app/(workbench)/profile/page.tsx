"use client";

import { useDeveloperProfile } from "@/lib/queries";
import {
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";
import { ConstraintTag } from "@/components/artifacts/constraint-tag";

export default function ProfilePage() {
  const { data, isLoading, isError, refetch } = useDeveloperProfile();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;

  const fields: [string, string][] = [
    ["团队规模", data.team_size],
    ["时间预算", data.time_budget],
    ["程序能力", data.programming_ability],
    ["美术能力", data.art_ability],
    ["音频能力", data.audio_ability],
    ["内容生产能力", data.content_production_ability],
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="开发者画像" description="能力、约束与偏好" />

      <section className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {fields.map(([label, value]) => (
          <div key={label} className="rounded-lg border p-3">
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className="text-sm font-medium">{value}</div>
          </div>
        ))}
      </section>

      <section>
        <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
          约束与偏好
        </h2>
        <div className="space-y-2">
          {data.constraints.map((constraint) => (
            <ConstraintTag key={constraint.id} constraint={constraint} />
          ))}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div>
          <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
            喜欢的参考
          </h2>
          <p className="text-sm">{data.liked_references.join("、")}</p>
        </div>
        <div>
          <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
            讨厌的参考或机制
          </h2>
          <p className="text-sm">{data.disliked_references_or_mechanics.join("、")}</p>
        </div>
        <div className="md:col-span-2">
          <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
            期望的玩家体验
          </h2>
          <p className="text-sm">{data.desired_player_experiences.join("、")}</p>
        </div>
      </section>
    </div>
  );
}
