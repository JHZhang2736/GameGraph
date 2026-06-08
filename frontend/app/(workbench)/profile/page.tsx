"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shell/view-states";
import {
  ProfileInputPanel,
  type ProfileInputState,
} from "@/components/profile/profile-input-panel";
import { ProfileDraftPreview } from "@/components/profile/profile-draft-preview";
import { ProfileMissingFields } from "@/components/profile/profile-missing-fields";
import { ProfileSourceList } from "@/components/profile/profile-source-list";
import { useParseDeveloperProfileInput } from "@/lib/queries";
import type { ProfileParseInput } from "@/lib/types";

const DEFAULT_PROFILE_TEXT =
  "我是 solo 开发者，程序能力强，美术能力弱，想做三个月内能验证的原型。" +
  "我喜欢 Balatro 和 Into the Breach，想要短局、系统性决策和战术预测。" +
  "不要做在线多人，我不想做长篇叙事内容，也不想做大量内容。";

const DEFAULT_INPUT: ProfileInputState = {
  raw_text: DEFAULT_PROFILE_TEXT,
  liked_references: "",
  disliked_references_or_mechanics: "",
  expected_project_scale: "",
};

function splitList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function toParseInput(state: ProfileInputState): ProfileParseInput {
  return {
    raw_text: state.raw_text,
    liked_references: splitList(state.liked_references),
    disliked_references_or_mechanics: splitList(state.disliked_references_or_mechanics),
    expected_project_scale: state.expected_project_scale.trim() || undefined,
  };
}

export default function ProfilePage() {
  const [input, setInput] = useState<ProfileInputState>(DEFAULT_INPUT);
  // `submitted` is the input actually parsed; editing the form does not reparse
  // until the user clicks 解析画像. The default profile parses on first render.
  const [submitted, setSubmitted] = useState<ProfileParseInput>(() =>
    toParseInput(DEFAULT_INPUT),
  );

  const { data: result } = useParseDeveloperProfileInput(submitted);
  const draft = result?.draft;

  return (
    <div className="space-y-6">
      <PageHeader title="开发者画像" description="自由表达、结构化草稿与缺失信息" />

      <div className="grid gap-4 xl:grid-cols-[minmax(320px,0.9fr)_minmax(420px,1.1fr)]">
        <ProfileInputPanel
          value={input}
          onChange={setInput}
          onParse={() => setSubmitted(toParseInput(input))}
        />
        {draft ? (
          <ProfileDraftPreview draft={draft} />
        ) : (
          <section className="rounded-lg border p-4 text-sm text-muted-foreground">
            等待解析画像。
          </section>
        )}
      </div>

      {draft ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <ProfileMissingFields fields={draft.missing_fields} />
          <ProfileSourceList sources={draft.field_sources} />
        </div>
      ) : null}

      <div className="flex justify-end">
        <Button type="button" disabled={!draft?.is_complete}>
          确认画像
        </Button>
      </div>
    </div>
  );
}
