"use client";

import { useState, useSyncExternalStore } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shell/view-states";
import {
  ProfileInputPanel,
  type ProfileInputState,
} from "@/components/profile/profile-input-panel";
import { ProfileDraftPreview } from "@/components/profile/profile-draft-preview";
import { ProfileConfirmedView } from "@/components/profile/profile-confirmed-view";
import { useMechanics, useParseDeveloperProfileInput } from "@/lib/queries";
import { confirmDeveloperProfile } from "@/lib/data";
import {
  createDraftFromProfile,
  createEmptyDraft,
  recomputeDraftCompleteness,
} from "@/lib/profile/draft";
import {
  loadStoredProfile,
  saveStoredProfile,
  subscribeStoredProfile,
} from "@/lib/profile/storage";
import type {
  DeveloperProfile,
  DeveloperProfileDraft,
  ProfileParseInput,
  ProfileParseResult,
} from "@/lib/types";

// Shown as a gray placeholder hint so users see how to phrase their input. The
// field starts empty; nothing is parsed until the user clicks 解析画像.
const EXAMPLE_PROFILE_TEXT =
  "我是 solo 开发者，程序能力强，美术能力弱，想做三个月内能验证的原型。" +
  "我喜欢 Balatro 和 Into the Breach，想要短局、系统性决策和战术预测。" +
  "不要做在线多人，我不想做长篇叙事内容，也不想做大量内容。";

const EMPTY_INPUT: ProfileInputState = {
  raw_text: "",
  liked_references: "",
  disliked_references_or_mechanics: "",
  expected_project_scale: "",
};

function splitList(value: string) {
  return value
    .split(/[,，、]/)
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
  const [input, setInput] = useState<ProfileInputState>(EMPTY_INPUT);
  // `submitted` is the input actually parsed. It starts null so nothing parses
  // on first load; clicking 解析画像 seeds it. Editing the form does not reparse
  // until the next click.
  const [submitted, setSubmitted] = useState<ProfileParseInput | null>(null);
  const { data: result } = useParseDeveloperProfileInput(submitted);
  // 库内机制名，作为「讨厌方向」多选的可选项（加载失败/未就绪则只能自由输入）。
  const { data: mechanics } = useMechanics();

  // The editable draft starts as a blank profile so the right side is usable
  // without any free-text input, then gets re-seeded whenever a parse returns.
  // Re-seeding during render (not in an effect) is the supported way to reset
  // state when the parse result changes.
  const [seed, setSeed] = useState<ProfileParseResult | undefined>(result);
  const [draft, setDraft] = useState<DeveloperProfileDraft>(() => createEmptyDraft());
  const [confirmed, setConfirmed] = useState<DeveloperProfile | null>(null);
  const queryClient = useQueryClient();

  // The profile confirmed in a previous visit, read from browser storage.
  // useSyncExternalStore returns null during SSR/hydration (third arg) and the
  // stored profile afterward, so restoring it never causes a hydration mismatch.
  const storedProfile = useSyncExternalStore(
    subscribeStoredProfile,
    loadStoredProfile,
    () => null,
  );
  const [restoredProfile, setRestoredProfile] = useState<DeveloperProfile | null>(null);

  // Re-seed the confirmed view and editable draft from storage the first time a
  // stored profile appears (mount, or a confirm in another tab). Adjusting state
  // during render is the supported way to react to a changing external value.
  if (storedProfile && storedProfile !== restoredProfile) {
    setRestoredProfile(storedProfile);
    setConfirmed(storedProfile);
    setDraft(createDraftFromProfile(storedProfile));
  }

  if (result && result !== seed) {
    setSeed(result);
    setDraft(result.draft);
    setConfirmed(null);
  }

  function updateDraft(next: DeveloperProfileDraft) {
    setDraft(recomputeDraftCompleteness(next));
    setConfirmed(null);
  }

  async function handleConfirm() {
    const profile = await confirmDeveloperProfile(draft);
    saveStoredProfile(profile);
    setConfirmed(profile);
    // Let downstream steps that read getDeveloperProfile pick up the new profile.
    void queryClient.invalidateQueries({ queryKey: ["developer-profile"] });
  }

  return (
    <div className="space-y-6">
      <PageHeader title="开发者画像" description="自由表达与结构化草稿" />

      <div className="grid gap-4 xl:grid-cols-[minmax(320px,0.9fr)_minmax(420px,1.1fr)]">
        <ProfileInputPanel
          value={input}
          onChange={setInput}
          onParse={() => setSubmitted(toParseInput(input))}
          rawTextPlaceholder={EXAMPLE_PROFILE_TEXT}
        />
        <ProfileDraftPreview
          draft={draft}
          onChange={updateDraft}
          mechanicOptions={mechanics}
        />
      </div>

      {confirmed ? <ProfileConfirmedView profile={confirmed} /> : null}

      <div className="flex justify-end">
        <Button
          type="button"
          disabled={!draft.is_complete}
          onClick={() => void handleConfirm()}
        >
          确认画像
        </Button>
      </div>
    </div>
  );
}
