import { ConstraintTag } from "@/components/artifacts/constraint-tag";
import { Badge } from "@/components/ui/badge";
import type { DeveloperProfileDraft } from "@/lib/types";

function valueOrMissing(value: string | null) {
  return value ?? "缺失";
}

export function ProfileDraftPreview({ draft }: { draft: DeveloperProfileDraft }) {
  const fields: [string, string | null][] = [
    ["团队规模", draft.team_size],
    ["时间预算", draft.time_budget],
    ["程序能力", draft.programming_ability],
    ["美术能力", draft.art_ability],
    ["音频能力", draft.audio_ability],
    ["内容生产能力", draft.content_production_ability],
  ];

  return (
    <section className="space-y-4 rounded-lg border p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium">结构化预览</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            完整画像才能进入机会匹配。
          </p>
        </div>
        <Badge variant={draft.is_complete ? "secondary" : "destructive"}>
          {draft.is_complete ? "完整" : "缺少关键信息"}
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {fields.map(([label, value]) => (
          <div key={label} className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className="text-sm font-medium">{valueOrMissing(value)}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <ListBlock title="喜欢参考" values={draft.liked_references} />
        <ListBlock title="讨厌方向" values={draft.disliked_references_or_mechanics} />
        <ListBlock title="期望体验" values={draft.desired_player_experiences} />
      </div>

      <div className="space-y-2">
        <h3 className="text-xs font-medium text-muted-foreground">约束与偏好</h3>
        {draft.constraints.length ? (
          draft.constraints.map((constraint) => (
            <ConstraintTag key={constraint.id} constraint={constraint} />
          ))
        ) : (
          <p className="text-sm text-muted-foreground">尚未识别到约束。</p>
        )}
      </div>
    </section>
  );
}

function ListBlock({ title, values }: { title: string; values: string[] }) {
  return (
    <div className="rounded-md border p-3">
      <div className="text-xs text-muted-foreground">{title}</div>
      <div className="mt-1 text-sm font-medium">
        {values.length ? values.join("、") : "未提供"}
      </div>
    </div>
  );
}
