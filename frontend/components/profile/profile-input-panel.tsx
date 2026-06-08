"use client";

import { Button } from "@/components/ui/button";

export interface ProfileInputState {
  raw_text: string;
  liked_references: string;
  disliked_references_or_mechanics: string;
  expected_project_scale: string;
}

interface ProfileInputPanelProps {
  value: ProfileInputState;
  onChange: (value: ProfileInputState) => void;
  onParse: () => void;
  rawTextPlaceholder?: string;
}

const inputClass =
  "h-9 w-full rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function ProfileInputPanel({
  value,
  onChange,
  onParse,
  rawTextPlaceholder,
}: ProfileInputPanelProps) {
  return (
    <section className="space-y-3 rounded-lg border p-4">
      <div>
        <h2 className="text-sm font-medium">输入画像</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          用自然语言描述团队、能力、偏好和项目边界。
        </p>
      </div>
      <div className="space-y-1">
        <label
          htmlFor="profile-raw-text"
          className="block text-xs font-medium text-muted-foreground"
        >
          自由描述
        </label>
        <textarea
          id="profile-raw-text"
          className="min-h-40 w-full rounded-md border bg-background p-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          placeholder={rawTextPlaceholder}
          value={value.raw_text}
          onChange={(event) => onChange({ ...value, raw_text: event.target.value })}
        />
      </div>
      <div className="space-y-1">
        <label
          htmlFor="profile-liked"
          className="block text-xs font-medium text-muted-foreground"
        >
          喜欢参考
        </label>
        <input
          id="profile-liked"
          className={inputClass}
          placeholder="用逗号分隔，例如 Balatro, Into the Breach"
          value={value.liked_references}
          onChange={(event) =>
            onChange({ ...value, liked_references: event.target.value })
          }
        />
      </div>
      <div className="space-y-1">
        <label
          htmlFor="profile-disliked"
          className="block text-xs font-medium text-muted-foreground"
        >
          讨厌参考或机制
        </label>
        <input
          id="profile-disliked"
          className={inputClass}
          placeholder="用逗号分隔，例如 online multiplayer"
          value={value.disliked_references_or_mechanics}
          onChange={(event) =>
            onChange({
              ...value,
              disliked_references_or_mechanics: event.target.value,
            })
          }
        />
      </div>
      <div className="space-y-1">
        <label
          htmlFor="profile-scale"
          className="block text-xs font-medium text-muted-foreground"
        >
          项目规模
        </label>
        <input
          id="profile-scale"
          className={inputClass}
          placeholder="例如 six week prototype"
          value={value.expected_project_scale}
          onChange={(event) =>
            onChange({ ...value, expected_project_scale: event.target.value })
          }
        />
      </div>
      <Button type="button" onClick={onParse}>
        解析画像
      </Button>
    </section>
  );
}
