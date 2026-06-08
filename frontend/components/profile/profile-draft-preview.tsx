"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EditableSelect } from "@/components/profile/editable-select";
import { cn } from "@/lib/utils";
import type {
  ConstraintType,
  DeveloperConstraint,
  DeveloperProfileDraft,
} from "@/lib/types";

interface ScalarField {
  key:
    | "team_size"
    | "time_budget"
    | "programming_ability"
    | "art_ability"
    | "audio_ability"
    | "content_production_ability";
  label: string;
  options: string[];
}

const SCALAR_FIELDS: ScalarField[] = [
  { key: "team_size", label: "团队规模", options: ["solo", "small team"] },
  {
    key: "time_budget",
    label: "时间预算",
    options: ["three month prototype", "six week prototype", "part-time prototype"],
  },
  { key: "programming_ability", label: "程序能力", options: ["strong", "basic", "weak"] },
  { key: "art_ability", label: "美术能力", options: ["strong", "basic", "weak"] },
  { key: "audio_ability", label: "音频能力", options: ["strong", "basic", "weak"] },
  {
    key: "content_production_ability",
    label: "内容生产能力",
    options: ["full", "limited"],
  },
];

interface ListField {
  key: "liked_references" | "disliked_references_or_mechanics" | "desired_player_experiences";
  label: string;
}

const LIST_FIELDS: ListField[] = [
  { key: "liked_references", label: "喜欢参考" },
  { key: "disliked_references_or_mechanics", label: "讨厌方向" },
  { key: "desired_player_experiences", label: "期望体验" },
];

const CONSTRAINT_LABEL: Record<ConstraintType, string> = {
  hard: "硬性约束",
  strong_preference: "强偏好",
  soft_preference: "软偏好",
};

const CONSTRAINT_STYLE: Record<ConstraintType, string> = {
  hard: "border-red-200 bg-red-50",
  strong_preference: "border-amber-200 bg-amber-50",
  soft_preference: "border-zinc-200 bg-zinc-50",
};

function splitList(value: string): string[] {
  return value
    .split(/[,，、]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

interface ProfileDraftPreviewProps {
  draft: DeveloperProfileDraft;
  onChange: (draft: DeveloperProfileDraft) => void;
}

export function ProfileDraftPreview({ draft, onChange }: ProfileDraftPreviewProps) {
  const missing = new Set(draft.missing_fields.map((field) => field.field));

  function setConstraints(constraints: DeveloperConstraint[]) {
    onChange({ ...draft, constraints });
  }

  return (
    <section className="space-y-4 rounded-lg border p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium">结构化预览</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            可直接编辑每个字段；完整画像才能进入机会匹配。
          </p>
        </div>
        <Badge variant={draft.is_complete ? "secondary" : "destructive"}>
          {draft.is_complete ? "完整" : "缺少关键信息"}
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {SCALAR_FIELDS.map((field) => (
          <div key={field.key} className="space-y-1">
            <label
              htmlFor={`field-${field.key}`}
              className="block text-xs text-muted-foreground"
            >
              {field.label}
            </label>
            <EditableSelect
              id={`field-${field.key}`}
              value={draft[field.key]}
              options={field.options}
              invalid={missing.has(field.key)}
              onChange={(value) => onChange({ ...draft, [field.key]: value })}
            />
          </div>
        ))}
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {LIST_FIELDS.map((field) => (
          <div key={field.key} className="space-y-1">
            <label
              htmlFor={`field-${field.key}`}
              className="block text-xs text-muted-foreground"
            >
              {field.label}
            </label>
            <input
              id={`field-${field.key}`}
              className={cn(
                "h-9 w-full rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring",
                missing.has(field.key) && "border-red-300",
              )}
              placeholder="用逗号分隔"
              value={draft[field.key].join(", ")}
              onChange={(event) =>
                onChange({ ...draft, [field.key]: splitList(event.target.value) })
              }
            />
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-medium text-muted-foreground">约束与偏好</h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              setConstraints([
                ...draft.constraints,
                {
                  id: `constraint_custom_${draft.constraints.length}_${Date.now()}`,
                  type: "hard",
                  statement: "",
                },
              ])
            }
          >
            添加约束
          </Button>
        </div>
        {draft.constraints.length ? (
          draft.constraints.map((constraint, index) => (
            <div
              key={constraint.id}
              data-constraint={constraint.type}
              className={cn(
                "flex flex-wrap items-center gap-2 rounded-md border p-2",
                CONSTRAINT_STYLE[constraint.type],
              )}
            >
              <select
                aria-label={`约束类型 ${index + 1}`}
                className="h-8 rounded-md border bg-background px-2 text-xs outline-none"
                value={constraint.type}
                onChange={(event) =>
                  setConstraints(
                    draft.constraints.map((item, itemIndex) =>
                      itemIndex === index
                        ? { ...item, type: event.target.value as ConstraintType }
                        : item,
                    ),
                  )
                }
              >
                {(Object.keys(CONSTRAINT_LABEL) as ConstraintType[]).map((type) => (
                  <option key={type} value={type}>
                    {CONSTRAINT_LABEL[type]}
                  </option>
                ))}
              </select>
              <input
                aria-label={`约束内容 ${index + 1}`}
                className="h-8 min-w-48 flex-1 rounded-md border bg-background px-2 text-sm outline-none"
                value={constraint.statement}
                onChange={(event) =>
                  setConstraints(
                    draft.constraints.map((item, itemIndex) =>
                      itemIndex === index
                        ? { ...item, statement: event.target.value }
                        : item,
                    ),
                  )
                }
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() =>
                  setConstraints(draft.constraints.filter((_, i) => i !== index))
                }
              >
                删除
              </Button>
            </div>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">尚未识别到约束，可添加一条。</p>
        )}
      </div>
    </section>
  );
}
