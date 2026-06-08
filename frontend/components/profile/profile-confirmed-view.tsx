import { ConstraintTag } from "@/components/artifacts/constraint-tag";
import type { DeveloperProfile } from "@/lib/types";

export function ProfileConfirmedView({ profile }: { profile: DeveloperProfile }) {
  const fields: [string, string][] = [
    ["团队规模", profile.team_size],
    ["时间预算", profile.time_budget],
    ["程序能力", profile.programming_ability],
    ["美术能力", profile.art_ability],
    ["音频能力", profile.audio_ability],
    ["内容生产能力", profile.content_production_ability],
  ];

  return (
    <section className="space-y-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4">
      <h2 className="text-sm font-medium text-emerald-800">已确认画像</h2>
      <p className="text-xs text-emerald-700">
        这是提交给机会匹配的正式 DeveloperProfile（已去除草稿审计字段）。
      </p>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
        {fields.map(([label, value]) => (
          <div key={label} className="rounded-md border border-emerald-200 bg-white/60 p-2">
            <div className="text-xs text-emerald-700">{label}</div>
            <div className="text-sm font-medium">{value}</div>
          </div>
        ))}
      </div>
      <div className="space-y-1">
        {profile.constraints.map((constraint) => (
          <ConstraintTag key={constraint.id} constraint={constraint} />
        ))}
      </div>
    </section>
  );
}
