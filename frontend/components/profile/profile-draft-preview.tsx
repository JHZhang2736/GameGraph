"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EditableSelect } from "@/components/profile/editable-select";
import { MultiSelectChips } from "@/components/profile/multi-select-chips";
import {
  DESIRED_EXPERIENCE_OPTIONS,
  SCALAR_FIELD_OPTIONS,
  type ScalarFieldKey,
} from "@/lib/profile/field-options";
import { cn } from "@/lib/utils";
import type {
  ConstraintType,
  DeveloperConstraint,
  DeveloperProfileDraft,
} from "@/lib/types";

interface ScalarField {
  key: ScalarFieldKey;
  label: string;
}

const SCALAR_FIELDS: ScalarField[] = [
  { key: "team_size", label: "团队规模" },
  { key: "time_budget", label: "时间预算" },
  { key: "programming_ability", label: "程序能力" },
  { key: "art_ability", label: "美术能力" },
  { key: "audio_ability", label: "音频能力" },
  { key: "content_production_ability", label: "内容生产能力" },
];

interface ListField {
  key: "liked_references" | "disliked_references_or_mechanics" | "desired_player_experiences";
  label: string;
}

const LIST_FIELDS: ListField[] = [
  { key: "liked_references", label: "喜欢参考（选填）" },
  { key: "disliked_references_or_mechanics", label: "讨厌方向（选填）" },
  { key: "desired_player_experiences", label: "期望体验（选填）" },
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

interface ProfileDraftPreviewProps {
  draft: DeveloperProfileDraft;
  onChange: (draft: DeveloperProfileDraft) => void;
  // 库内机制名，作为「讨厌方向」的可选项；未加载时为空数组（仅自由输入）。
  mechanicOptions?: string[];
}

export function ProfileDraftPreview({
  draft,
  onChange,
  mechanicOptions,
}: ProfileDraftPreviewProps) {
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
              options={SCALAR_FIELD_OPTIONS[field.key]}
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
            <MultiSelectChips
              id={`field-${field.key}`}
              value={draft[field.key]}
              options={
                field.key === "desired_player_experiences"
                  ? DESIRED_EXPERIENCE_OPTIONS
                  : field.key === "disliked_references_or_mechanics"
                    ? mechanicOptions
                    : undefined
              }
              invalid={missing.has(field.key)}
              onChange={(next) => onChange({ ...draft, [field.key]: next })}
            />
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-medium text-muted-foreground">约束与偏好（选填）</h3>
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
