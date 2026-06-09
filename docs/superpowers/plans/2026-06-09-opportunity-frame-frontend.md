# 6.6 机会框架前端 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `/match` 选中的机会区域经 `POST /opportunity/frame` 展开为机会框架，并在 `/opportunities` 以「框架历史」手风琴列表呈现（最新生成 + 历史保留）。

**Architecture:** 方案 A2——在 `/match` 候选卡就地生成框架，成功后把结果落 localStorage 历史并跳转；`/opportunities` 退化为纯历史读取页。状态用 `localStorage`（框架历史）+ `sessionStorage`（一次性「刚生成」标记），仿 `lib/profile/storage.ts` 的 `useSyncExternalStore` 写法。

**Tech Stack:** Next.js 16（App Router，`next/navigation` 的 `useRouter`）/ React `useSyncExternalStore` / TanStack Query `useMutation` / vitest + Testing Library + userEvent。

**环境注意：**
- 所有命令在 `frontend/` 目录下执行（`cd D:/Files/GameGraph/.claude/worktrees/opportunity-frame-frontend/frontend`）。
- 跑测试**必须加 `--pool=threads`**：默认 `forks` pool 在本 Windows 环境 teardown 崩溃（基线既有噪声，非真失败）。
- 写 Next 代码前按 `frontend/AGENTS.md` 参阅 `node_modules/next/dist/docs/`。`useRouter` 已确认来自 `next/navigation`，事件处理里用 `router.push("/opportunities")`。

---

## File Structure

**新增**
- `frontend/lib/opportunity/frame-history.ts` — 框架历史 store（localStorage + sessionStorage，`useSyncExternalStore` 兼容）。
- `frontend/lib/opportunity/frame-history.test.ts`
- `frontend/components/opportunity/opportunity-frame-card.tsx` — 手风琴框架卡（折叠摘要 / 展开完整布局）。
- `frontend/components/opportunity/opportunity-frame-card.test.tsx`
- `frontend/lib/data/build-frame.test.ts` — `buildOpportunityFrame` 数据层测试。

**改动**
- `frontend/lib/types/index.ts` — `OpportunityFrame` 补 `warnings?: string[]`。
- `frontend/lib/data/index.ts` — 加 `buildOpportunityFrame`；删 `getOpportunityFrame`（Task 5）。
- `frontend/lib/queries/index.ts` — 加 `useBuildOpportunityFrame`；删 `useOpportunityFrame`（Task 5）。
- `frontend/components/opportunity/opportunity-candidate-card.tsx`（+ 其测试）— 加「生成机会框架」按钮。
- `frontend/app/(workbench)/match/page.tsx`（+ 其测试）— 生成框架 + 落历史 + 跳转。
- `frontend/app/(workbench)/opportunities/page.tsx`（+ 其测试）— 重写为历史读取页。

**任务依赖顺序**：Task 1 → 2 → 3 →（4 依赖 1,2）→（5 依赖 1,3）。每个任务提交后整套测试应保持绿色。

---

## Task 1: 框架历史 store

**Files:**
- Create: `frontend/lib/opportunity/frame-history.ts`
- Test: `frontend/lib/opportunity/frame-history.test.ts`

- [ ] **Step 1: 写失败测试**

`frontend/lib/opportunity/frame-history.test.ts`:

```ts
import { afterEach, describe, it, expect } from "vitest";
import {
  FRAMES_KEY,
  clearLastFrameId,
  loadFrames,
  peekLastFrameId,
  removeFrame,
  rememberLastFrameId,
  upsertFrame,
} from "@/lib/opportunity/frame-history";
import type { OpportunityFrame } from "@/lib/types";

function frame(id: string, area = "区域"): OpportunityFrame {
  return {
    id,
    developer_profile_id: "p",
    opportunity_area: area,
    source_game_ids: [],
    related_mechanics: [],
    related_player_experiences: [],
    related_constraints: [],
    related_innovation_patterns: [],
    recommended_transformations: ["主变形"],
    forbidden_directions: ["禁止"],
    evidence_path: [],
    fit_reason: "f",
    risk_reason: "r",
  };
}

afterEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe("frame-history", () => {
  it("starts empty", () => {
    expect(loadFrames()).toEqual([]);
  });

  it("upserts new frames newest-first", () => {
    upsertFrame(frame("frame|a"));
    upsertFrame(frame("frame|b"));
    expect(loadFrames().map((f) => f.id)).toEqual(["frame|b", "frame|a"]);
  });

  it("dedupes by id and moves the touched frame to the front", () => {
    upsertFrame(frame("frame|a", "旧"));
    upsertFrame(frame("frame|b"));
    upsertFrame(frame("frame|a", "新"));
    const frames = loadFrames();
    expect(frames.map((f) => f.id)).toEqual(["frame|a", "frame|b"]);
    expect(frames[0].opportunity_area).toBe("新");
  });

  it("removes a frame by id", () => {
    upsertFrame(frame("frame|a"));
    upsertFrame(frame("frame|b"));
    removeFrame("frame|a");
    expect(loadFrames().map((f) => f.id)).toEqual(["frame|b"]);
  });

  it("peekLastFrameId reads without clearing; clearLastFrameId removes it", () => {
    rememberLastFrameId("frame|a");
    expect(peekLastFrameId()).toBe("frame|a");
    expect(peekLastFrameId()).toBe("frame|a");
    clearLastFrameId();
    expect(peekLastFrameId()).toBeNull();
  });

  it("ignores corrupt storage", () => {
    localStorage.setItem(FRAMES_KEY, "{not json");
    expect(loadFrames()).toEqual([]);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npx vitest run --pool=threads lib/opportunity/frame-history.test.ts`
Expected: FAIL — `Failed to resolve import "@/lib/opportunity/frame-history"`.

- [ ] **Step 3: 实现**

`frontend/lib/opportunity/frame-history.ts`:

```ts
// 浏览器侧的机会框架历史。仿 lib/profile/storage.ts 的 useSyncExternalStore 写法：
// 用 raw 字符串作 key 缓存解析快照，使 loadFrames() 在数据未变时返回稳定引用，
// 避免 useSyncExternalStore 无限重渲染。写操作额外通知本地订阅者，以便同标签页
// 内的 upsert/remove 也能即时触发 React 重渲染（storage 事件只跨标签页触发）。
import type { OpportunityFrame } from "@/lib/types";

export const FRAMES_KEY = "gamegraph.opportunity-frames";
export const LAST_FRAME_ID_KEY = "gamegraph.last-frame-id";

function parseFrames(raw: string | null): OpportunityFrame[] {
  if (!raw) return [];
  try {
    const value = JSON.parse(raw);
    return Array.isArray(value) ? (value as OpportunityFrame[]) : [];
  } catch {
    return [];
  }
}

let snapshotRaw: string | null = null;
let snapshotFrames: OpportunityFrame[] = [];

const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((listener) => listener());
}

// 最新在前。无 window（SSR）或解析失败 → []。
export function loadFrames(): OpportunityFrame[] {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(FRAMES_KEY);
  if (raw !== snapshotRaw) {
    snapshotRaw = raw;
    snapshotFrames = parseFrames(raw);
  }
  return snapshotFrames;
}

export function subscribeFrames(onChange: () => void): () => void {
  listeners.add(onChange);
  let removeStorage = () => {};
  if (typeof window !== "undefined") {
    const handler = (event: StorageEvent) => {
      if (event.key === null || event.key === FRAMES_KEY) onChange();
    };
    window.addEventListener("storage", handler);
    removeStorage = () => window.removeEventListener("storage", handler);
  }
  return () => {
    listeners.delete(onChange);
    removeStorage();
  };
}

function writeFrames(frames: OpportunityFrame[]): void {
  window.localStorage.setItem(FRAMES_KEY, JSON.stringify(frames));
  emit();
}

// 按 frame.id 去重，并把被写入的框架置顶（最新在前）。
export function upsertFrame(frame: OpportunityFrame): void {
  if (typeof window === "undefined") return;
  const rest = loadFrames().filter((f) => f.id !== frame.id);
  writeFrames([frame, ...rest]);
}

export function removeFrame(id: string): void {
  if (typeof window === "undefined") return;
  writeFrames(loadFrames().filter((f) => f.id !== id));
}

export function rememberLastFrameId(id: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(LAST_FRAME_ID_KEY, id);
}

// 读取「刚生成」标记（不清除），供渲染期 lazy 初始化安全调用。
export function peekLastFrameId(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(LAST_FRAME_ID_KEY);
}

// 清除「刚生成」标记（在 effect 里调用，幂等）。
export function clearLastFrameId(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(LAST_FRAME_ID_KEY);
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `npx vitest run --pool=threads lib/opportunity/frame-history.test.ts`
Expected: PASS（6 tests）。

- [ ] **Step 5: 提交**

```bash
git add frontend/lib/opportunity/frame-history.ts frontend/lib/opportunity/frame-history.test.ts
git commit -m "feat(frontend): opportunity frame history store"
```

---

## Task 2: 类型对齐 + 数据层 + query hook

**Files:**
- Modify: `frontend/lib/types/index.ts`（`OpportunityFrame` 补 `warnings?`）
- Modify: `frontend/lib/data/index.ts`（加 `buildOpportunityFrame`）
- Modify: `frontend/lib/queries/index.ts`（加 `useBuildOpportunityFrame`）
- Test: `frontend/lib/data/build-frame.test.ts`

- [ ] **Step 1: 写失败测试**

`frontend/lib/data/build-frame.test.ts`:

```ts
import { afterEach, describe, it, expect, vi } from "vitest";
import { buildOpportunityFrame } from "@/lib/data";
import type { DeveloperProfile, OpportunityArea, OpportunityFrame } from "@/lib/types";

const PROFILE: DeveloperProfile = {
  id: "p",
  team_size: "solo",
  time_budget: "三个月",
  programming_ability: "强",
  art_ability: "弱",
  audio_ability: "弱",
  content_production_ability: "有限",
  liked_references: [],
  disliked_references_or_mechanics: [],
  desired_player_experiences: [],
  constraints: [],
};

const AREA: OpportunityArea = {
  id: "opp|a|sub|Perspective|第一人称",
  anchor_game_id: "a",
  anchor_summary: "s",
  transformation: {
    type: "substitute",
    dimension: "Perspective",
    from_value: "第三人称",
    to_value: "第一人称",
  },
  existing_combination_count: 0,
  evidence: { anchor_game_id: "a", target_value_game_ids: ["b"], combination_game_ids: [] },
  risk_posture: "balanced",
  fit_reason: "f",
  risk_reason: "r",
};

const FRAME: OpportunityFrame = {
  id: "frame|opp|a|sub|Perspective|第一人称",
  developer_profile_id: "p",
  opportunity_area: "区域",
  source_game_ids: ["a"],
  related_mechanics: [],
  related_player_experiences: [],
  related_constraints: [],
  related_innovation_patterns: [],
  recommended_transformations: ["主变形"],
  forbidden_directions: ["禁止"],
  evidence_path: ["rel"],
  fit_reason: "f",
  risk_reason: "r",
  warnings: ["注意"],
};

afterEach(() => vi.restoreAllMocks());

describe("buildOpportunityFrame", () => {
  it("POSTs profile+area to /api/opportunity/frame and returns the frame", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => FRAME });
    vi.stubGlobal("fetch", fetchMock);

    const result = await buildOpportunityFrame(PROFILE, AREA);

    expect(result.id).toBe(FRAME.id);
    expect(result.warnings).toEqual(["注意"]);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/opportunity/frame");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ profile: PROFILE, area: AREA });
  });

  it("throws on a non-2xx response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) }),
    );
    await expect(buildOpportunityFrame(PROFILE, AREA)).rejects.toThrow(/500/);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npx vitest run --pool=threads lib/data/build-frame.test.ts`
Expected: FAIL — `buildOpportunityFrame` is not exported / not a function。

- [ ] **Step 3a: 给类型加 warnings**

`frontend/lib/types/index.ts`，在 `OpportunityFrame` 接口里 `risk_reason: string;` 后新增一行：

```ts
  risk_reason: string;
  warnings?: string[];
```

- [ ] **Step 3b: 加数据层函数**

`frontend/lib/data/index.ts`：在顶部类型 import 列表里加入 `OpportunityArea`（与现有 `OpportunityFrame` / `OpportunityMatchResult` 同列），然后在 `matchOpportunities` 函数之后新增：

```ts
// 6.6 机会框架。把开发者画像 + 选中的机会区域发给后端，拿回一个机会框架。
// 同样是按钮触发的动作，配套 hook 用 useMutation。
export async function buildOpportunityFrame(
  profile: DeveloperProfile,
  area: OpportunityArea,
): Promise<OpportunityFrame> {
  const res = await fetch(`${apiBase()}/opportunity/frame`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile, area }),
  });
  if (!res.ok) throw new Error(`POST /opportunity/frame responded ${res.status}`);
  return (await res.json()) as OpportunityFrame;
}
```

- [ ] **Step 3c: 加 query hook**

`frontend/lib/queries/index.ts`：在 `@/lib/data` 的 import 里加入 `buildOpportunityFrame`；在 `@/lib/types` 的 import 里加入 `OpportunityArea`（与现有 `DeveloperProfile` 同列）。在文件末尾 `useMatchOpportunities` 之后新增：

```ts
export function useBuildOpportunityFrame() {
  return useMutation({
    mutationFn: ({ profile, area }: { profile: DeveloperProfile; area: OpportunityArea }) =>
      buildOpportunityFrame(profile, area),
  });
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `npx vitest run --pool=threads lib/data/build-frame.test.ts`
Expected: PASS（2 tests）。

- [ ] **Step 5: 提交**

```bash
git add frontend/lib/types/index.ts frontend/lib/data/index.ts frontend/lib/queries/index.ts frontend/lib/data/build-frame.test.ts
git commit -m "feat(frontend): buildOpportunityFrame data fn + warnings type"
```

---

## Task 3: 机会框架卡组件（手风琴）

**Files:**
- Create: `frontend/components/opportunity/opportunity-frame-card.tsx`
- Test: `frontend/components/opportunity/opportunity-frame-card.test.tsx`

- [ ] **Step 1: 写失败测试**

`frontend/components/opportunity/opportunity-frame-card.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OpportunityFrameCard } from "@/components/opportunity/opportunity-frame-card";
import type { OpportunityFrame } from "@/lib/types";

const FRAME: OpportunityFrame = {
  id: "frame|opp|a",
  developer_profile_id: "p",
  opportunity_area: "低美术短周期的规则操控",
  source_game_ids: ["baba_is_you"],
  related_mechanics: ["规则改写"],
  related_player_experiences: ["顿悟时刻"],
  related_constraints: ["内容产能有限"],
  related_innovation_patterns: ["规则即玩法"],
  recommended_transformations: ["把规则改写压成 5 分钟关卡", "引入合作视角"],
  forbidden_directions: ["online multiplayer"],
  evidence_path: ["relation-1"],
  fit_reason: "契合低美术预算。",
  risk_reason: "关卡设计成本高。",
  warnings: ["图谱规模偏小。"],
};

describe("OpportunityFrameCard", () => {
  it("shows the area title and primary transformation when collapsed", () => {
    render(<OpportunityFrameCard frame={FRAME} />);
    expect(screen.getByText("低美术短周期的规则操控")).toBeInTheDocument();
    expect(screen.getByText("把规则改写压成 5 分钟关卡")).toBeInTheDocument();
    expect(screen.queryByText("禁止方向")).not.toBeInTheDocument();
  });

  it("reveals full detail with primary/secondary split when expanded", () => {
    render(<OpportunityFrameCard frame={FRAME} defaultOpen />);
    expect(screen.getByText("禁止方向")).toBeInTheDocument();
    expect(screen.getByText("主变形")).toBeInTheDocument();
    expect(screen.getByText("次变形")).toBeInTheDocument();
    expect(screen.getByText("引入合作视角")).toBeInTheDocument();
    expect(screen.getByText("图谱规模偏小。")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npx vitest run --pool=threads components/opportunity/opportunity-frame-card.test.tsx`
Expected: FAIL — `Failed to resolve import ".../opportunity-frame-card"`。

- [ ] **Step 3: 实现**

`frontend/components/opportunity/opportunity-frame-card.tsx`:

```tsx
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `npx vitest run --pool=threads components/opportunity/opportunity-frame-card.test.tsx`
Expected: PASS（2 tests）。

- [ ] **Step 5: 提交**

```bash
git add frontend/components/opportunity/opportunity-frame-card.tsx frontend/components/opportunity/opportunity-frame-card.test.tsx
git commit -m "feat(frontend): collapsible opportunity frame card"
```

---

## Task 4: 候选卡「生成」按钮 + match 页接线

**依赖：** Task 1（frame-history）、Task 2（useBuildOpportunityFrame）。

**Files:**
- Modify: `frontend/components/opportunity/opportunity-candidate-card.tsx`
- Modify: `frontend/components/opportunity/opportunity-candidate-card.test.tsx`
- Modify: `frontend/app/(workbench)/match/page.tsx`
- Modify: `frontend/app/(workbench)/match/match-page.test.tsx`

- [ ] **Step 1: 写失败测试（候选卡）**

把 `frontend/components/opportunity/opportunity-candidate-card.test.tsx` 整个替换为：

```tsx
import { afterEach, describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OpportunityCandidateCard } from "@/components/opportunity/opportunity-candidate-card";
import type { OpportunityArea } from "@/lib/types";

const AREA: OpportunityArea = {
  id: "opp|vampire_survivors|sub|Perspective|第一人称",
  anchor_game_id: "vampire_survivors",
  anchor_summary: "吸血鬼幸存者:自动攻击的弹幕生存 roguelite",
  transformation: {
    type: "substitute",
    dimension: "Perspective",
    from_value: "第三人称",
    to_value: "第一人称",
  },
  existing_combination_count: 0,
  evidence: {
    anchor_game_id: "vampire_survivors",
    target_value_game_ids: ["doom", "ultrakill"],
    combination_game_ids: [],
  },
  risk_posture: "balanced",
  fit_reason: "契合短周期、强系统性的偏好。",
  risk_reason: "第一人称弹幕密度需要重新调校。",
};

afterEach(() => vi.restoreAllMocks());

describe("OpportunityCandidateCard", () => {
  it("renders the transformation, novelty, risk label, summary and reasons", () => {
    render(<OpportunityCandidateCard area={AREA} onGenerate={() => {}} />);
    expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument();
    expect(screen.getByText("全新组合")).toBeInTheDocument();
    expect(screen.getByText("平衡")).toBeInTheDocument();
    expect(
      screen.getByText("吸血鬼幸存者:自动攻击的弹幕生存 roguelite"),
    ).toBeInTheDocument();
    expect(screen.getByText("契合短周期、强系统性的偏好。")).toBeInTheDocument();
    expect(screen.getByText("第一人称弹幕密度需要重新调校。")).toBeInTheDocument();
  });

  it("calls onGenerate with the area when the generate button is clicked", async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn();
    render(<OpportunityCandidateCard area={AREA} onGenerate={onGenerate} />);
    await user.click(screen.getByRole("button", { name: "生成机会框架" }));
    expect(onGenerate).toHaveBeenCalledWith(AREA);
  });

  it("disables the button and shows progress while generating", () => {
    render(<OpportunityCandidateCard area={AREA} onGenerate={() => {}} isGenerating />);
    expect(screen.getByRole("button", { name: "生成中…" })).toBeDisabled();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npx vitest run --pool=threads components/opportunity/opportunity-candidate-card.test.tsx`
Expected: FAIL — 找不到「生成机会框架」按钮。

- [ ] **Step 3: 实现候选卡改动**

`frontend/components/opportunity/opportunity-candidate-card.tsx`：在顶部 import 加 `import { Button } from "@/components/ui/button";`；改函数签名与新增按钮：

签名改为：

```tsx
export function OpportunityCandidateCard({
  area,
  onGenerate,
  isGenerating = false,
}: {
  area: OpportunityArea;
  onGenerate: (area: OpportunityArea) => void;
  isGenerating?: boolean;
}) {
```

在 `CardContent` 末尾、证据 `<p>…</p>` 之后新增按钮：

```tsx
        <p className="text-xs text-muted-foreground/70">
          证据:锚点 {area.anchor_game_id} · 目标值佐证 {targetCount} 款
          {comboCount > 0 ? ` · 组合佐证 ${comboCount} 款` : ""}
        </p>
        <Button type="button" onClick={() => onGenerate(area)} disabled={isGenerating}>
          {isGenerating ? "生成中…" : "生成机会框架"}
        </Button>
```

- [ ] **Step 4: 跑测试确认通过（候选卡）**

Run: `npx vitest run --pool=threads components/opportunity/opportunity-candidate-card.test.tsx`
Expected: PASS（3 tests）。

- [ ] **Step 5: 写失败测试（match 页）**

把 `frontend/app/(workbench)/match/match-page.test.tsx` 整个替换为：

```tsx
import { afterEach, describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MatchPage from "@/app/(workbench)/match/page";
import type { OpportunityFrame, OpportunityMatchResult } from "@/lib/types";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pushMock }) }));

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

const RESULT: OpportunityMatchResult = {
  profile_id: "dev_profile_1",
  areas: [
    {
      id: "opp|vampire_survivors|sub|Perspective|第一人称",
      anchor_game_id: "vampire_survivors",
      anchor_summary: "吸血鬼幸存者:弹幕生存 roguelite",
      transformation: {
        type: "substitute",
        dimension: "Perspective",
        from_value: "第三人称",
        to_value: "第一人称",
      },
      existing_combination_count: 0,
      evidence: {
        anchor_game_id: "vampire_survivors",
        target_value_game_ids: ["doom"],
        combination_game_ids: [],
      },
      risk_posture: "balanced",
      fit_reason: "契合短周期偏好。",
      risk_reason: "弹幕密度需调校。",
    },
  ],
  rejected: [
    {
      candidate_id: "opp|x|comb|Mechanic|在线匹配",
      rejection_reason: "与画像硬约束『不做在线多人』冲突。",
    },
  ],
  warnings: ["图谱规模较小，新颖度判断偏粗。"],
};

const FRAME: OpportunityFrame = {
  id: "frame|opp|vampire_survivors|sub|Perspective|第一人称",
  developer_profile_id: "dev_profile_1",
  opportunity_area: "第一人称弹幕生存",
  source_game_ids: ["doom"],
  related_mechanics: [],
  related_player_experiences: [],
  related_constraints: [],
  related_innovation_patterns: [],
  recommended_transformations: ["主变形"],
  forbidden_directions: ["禁止"],
  evidence_path: ["rel"],
  fit_reason: "f",
  risk_reason: "r",
};

afterEach(() => {
  vi.restoreAllMocks();
  pushMock.mockClear();
  localStorage.clear();
  sessionStorage.clear();
});

async function clickMatch() {
  const user = userEvent.setup();
  const button = await screen.findByRole("button", { name: "匹配机会" });
  await waitFor(() => expect(button).not.toBeDisabled());
  await user.click(button);
}

describe("MatchPage", () => {
  it("renders candidates, warnings and rejected reasons after matching", async () => {
    vi.stubGlobal("fetch", mockFetch(200, RESULT));
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument(),
    );
    expect(screen.getByText("平衡")).toBeInTheDocument();
    expect(screen.getByText("图谱规模较小，新颖度判断偏粗。")).toBeInTheDocument();
    expect(screen.getByText(/不做在线多人/)).toBeInTheDocument();
  });

  it("shows an empty state when no areas match", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch(200, { profile_id: "p", areas: [], rejected: [], warnings: [] }),
    );
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() => expect(screen.getByText(/未匹配到候选/)).toBeInTheDocument());
  });

  it("shows an error state on a 500", async () => {
    vi.stubGlobal("fetch", mockFetch(500, {}));
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() => expect(screen.getByText("加载失败")).toBeInTheDocument());
  });

  it("generates a frame, stores it in history, and navigates to /opportunities", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => RESULT })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => FRAME });
    vi.stubGlobal("fetch", fetchMock);
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "生成机会框架" }));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/opportunities"));
    const stored = JSON.parse(localStorage.getItem("gamegraph.opportunity-frames")!);
    expect(stored[0].id).toBe(FRAME.id);
    expect(sessionStorage.getItem("gamegraph.last-frame-id")).toBe(FRAME.id);
  });
});
```

- [ ] **Step 6: 跑测试确认失败**

Run: `npx vitest run --pool=threads "app/(workbench)/match/match-page.test.tsx"`
Expected: FAIL — 找不到「生成机会框架」按钮 / `pushMock` 未被调用。

- [ ] **Step 7: 实现 match 页改动**

把 `frontend/app/(workbench)/match/page.tsx` 整个替换为：

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  EmptyState,
  ErrorState,
  PageHeader,
} from "@/components/shell/view-states";
import { OpportunityCandidateCard } from "@/components/opportunity/opportunity-candidate-card";
import { rememberLastFrameId, upsertFrame } from "@/lib/opportunity/frame-history";
import {
  useBuildOpportunityFrame,
  useDeveloperProfile,
  useMatchOpportunities,
} from "@/lib/queries";
import type { OpportunityArea } from "@/lib/types";

export default function MatchPage() {
  const router = useRouter();
  const { data: profile } = useDeveloperProfile();
  const match = useMatchOpportunities();
  const buildFrame = useBuildOpportunityFrame();
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const result = match.data;

  function runMatch() {
    if (profile) match.mutate(profile);
  }

  function generate(area: OpportunityArea) {
    if (!profile) return;
    setGeneratingId(area.id);
    buildFrame.mutate(
      { profile, area },
      {
        onSuccess: (frame) => {
          upsertFrame(frame);
          rememberLastFrameId(frame.id);
          router.push("/opportunities");
        },
        onSettled: () => setGeneratingId(null),
      },
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="机会匹配" description="从你的画像匹配出的创新机会" />

      <div>
        <Button type="button" disabled={!profile || match.isPending} onClick={runMatch}>
          {match.isPending ? "匹配中…" : "匹配机会"}
        </Button>
      </div>

      {match.isError ? <ErrorState onRetry={runMatch} /> : null}
      {buildFrame.isError ? <ErrorState /> : null}

      {result ? (
        <div className="space-y-6">
          {result.warnings.length > 0 ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <ul className="list-disc space-y-1 pl-5">
                {result.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {result.areas.length > 0 ? (
            <section className="grid gap-4 md:grid-cols-2">
              {result.areas.map((area) => (
                <OpportunityCandidateCard
                  key={area.id}
                  area={area}
                  onGenerate={generate}
                  isGenerating={generatingId === area.id}
                />
              ))}
            </section>
          ) : (
            <EmptyState message="未匹配到候选，可能与图谱规模或画像约束有关。" />
          )}

          {result.rejected.length > 0 ? (
            <section className="rounded-lg border border-dashed p-4">
              <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
                被排除的方向
              </h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                {result.rejected.map((r) => (
                  <li key={r.candidate_id}>{r.rejection_reason}</li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 8: 跑测试确认通过（match 页）**

Run: `npx vitest run --pool=threads "app/(workbench)/match/match-page.test.tsx" components/opportunity/opportunity-candidate-card.test.tsx`
Expected: PASS（候选卡 3 + match 页 4 = 7 tests）。

- [ ] **Step 9: 提交**

```bash
git add "frontend/components/opportunity/opportunity-candidate-card.tsx" "frontend/components/opportunity/opportunity-candidate-card.test.tsx" "frontend/app/(workbench)/match/page.tsx" "frontend/app/(workbench)/match/match-page.test.tsx"
git commit -m "feat(frontend): generate frame from match candidate and navigate"
```

---

## Task 5: 重写 /opportunities 为历史读取页 + 删除旧 mock

**依赖：** Task 1（frame-history）、Task 3（OpportunityFrameCard）。

**Files:**
- Modify: `frontend/app/(workbench)/opportunities/page.tsx`
- Modify: `frontend/app/(workbench)/opportunities/opportunities-page.test.tsx`
- Modify: `frontend/lib/data/index.ts`（删 `getOpportunityFrame`）
- Modify: `frontend/lib/queries/index.ts`（删 `useOpportunityFrame` 及其 import）

- [ ] **Step 1: 写失败测试**

把 `frontend/app/(workbench)/opportunities/opportunities-page.test.tsx` 整个替换为：

```tsx
import { afterEach, describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import OpportunitiesPage from "@/app/(workbench)/opportunities/page";
import { rememberLastFrameId, upsertFrame } from "@/lib/opportunity/frame-history";
import type { OpportunityFrame } from "@/lib/types";

function frame(id: string, area: string): OpportunityFrame {
  return {
    id,
    developer_profile_id: "p",
    opportunity_area: area,
    source_game_ids: [],
    related_mechanics: [],
    related_player_experiences: [],
    related_constraints: [],
    related_innovation_patterns: [],
    recommended_transformations: ["主变形"],
    forbidden_directions: ["禁止"],
    evidence_path: [],
    fit_reason: "f",
    risk_reason: "r",
  };
}

afterEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe("OpportunitiesPage", () => {
  it("shows an empty state with a link to match when there is no history", () => {
    render(<OpportunitiesPage />);
    expect(screen.getByText(/还没有机会框架/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /去机会匹配/ })).toBeInTheDocument();
  });

  it("renders frames from history newest-first", () => {
    upsertFrame(frame("frame|a", "区域A"));
    upsertFrame(frame("frame|b", "区域B"));
    render(<OpportunitiesPage />);
    expect(screen.getByText("区域A")).toBeInTheDocument();
    expect(screen.getByText("区域B")).toBeInTheDocument();
  });

  it("auto-expands the just-generated frame", async () => {
    upsertFrame(frame("frame|a", "区域A"));
    rememberLastFrameId("frame|a");
    render(<OpportunitiesPage />);
    expect(await screen.findByText("禁止方向")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npx vitest run --pool=threads "app/(workbench)/opportunities/opportunities-page.test.tsx"`
Expected: FAIL — 现页面仍渲染 mock 框架，找不到空态「还没有机会框架」。

- [ ] **Step 3a: 重写 opportunities 页**

把 `frontend/app/(workbench)/opportunities/page.tsx` 整个替换为：

```tsx
"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { EmptyState, PageHeader } from "@/components/shell/view-states";
import { OpportunityFrameCard } from "@/components/opportunity/opportunity-frame-card";
import {
  clearLastFrameId,
  loadFrames,
  peekLastFrameId,
  removeFrame,
  subscribeFrames,
} from "@/lib/opportunity/frame-history";

export default function OpportunitiesPage() {
  const frames = useSyncExternalStore(subscribeFrames, loadFrames, () => []);
  // lazy 初始化时 peek（纯读，不改 storage），使高亮项首帧即展开；清除放到 effect。
  const [lastId] = useState<string | null>(() => peekLastFrameId());

  useEffect(() => {
    clearLastFrameId();
  }, []);

  if (frames.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader title="机会框架" description="从机会匹配生成的框架历史" />
        <EmptyState message="还没有机会框架，先去机会匹配选一个方向。" />
        <Link
          href="/match"
          className="text-sm text-primary underline-offset-4 hover:underline"
        >
          去机会匹配 →
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="机会框架" description="从机会匹配生成的框架历史" />
      <div className="space-y-4">
        {frames.map((frame) => (
          <OpportunityFrameCard
            key={frame.id}
            frame={frame}
            defaultOpen={frame.id === lastId}
            highlighted={frame.id === lastId}
            onRemove={removeFrame}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3b: 删除旧 mock 数据函数**

`frontend/lib/data/index.ts`：删除整段 `getOpportunityFrame` 函数：

```ts
export async function getOpportunityFrame(): Promise<OpportunityFrame> {
  return settle(goldenFlow.opportunity_frame);
}
```

（保留 `OpportunityFrame` 的 import —— 仍被 `buildOpportunityFrame` 返回类型与 `GoldenFlow` 类型使用。）

- [ ] **Step 3c: 删除旧 query hook**

`frontend/lib/queries/index.ts`：删除 `useOpportunityFrame` 函数：

```ts
export function useOpportunityFrame() {
  return useQuery({ queryKey: ["opportunity-frame"], queryFn: getOpportunityFrame });
}
```

并从 `@/lib/data` 的 import 列表中移除 `getOpportunityFrame`。

- [ ] **Step 4: 跑测试确认通过**

Run: `npx vitest run --pool=threads "app/(workbench)/opportunities/opportunities-page.test.tsx"`
Expected: PASS（3 tests）。

- [ ] **Step 5: 跑全套确认无回归**

Run: `npx vitest run --pool=threads`
Expected: 全部通过（原 96 + 新增；0 failures）。若 `grep -rn "getOpportunityFrame\|useOpportunityFrame" frontend` 仍有残留引用，清掉后再跑。

- [ ] **Step 6: 提交**

```bash
git add "frontend/app/(workbench)/opportunities/page.tsx" "frontend/app/(workbench)/opportunities/opportunities-page.test.tsx" frontend/lib/data/index.ts frontend/lib/queries/index.ts
git commit -m "feat(frontend): opportunities page reads frame history"
```

---

## 最终验证（全部任务完成后）

- [ ] 全套测试：`cd frontend && npx vitest run --pool=threads` → 0 failures。
- [ ] 类型检查（如项目配置）：`npx tsc --noEmit`（若 `tsconfig.json` 存在）。
- [ ] 残留引用检查：`grep -rn "getOpportunityFrame\|useOpportunityFrame" frontend` → 无结果。
- [ ] 交由 `superpowers:finishing-a-development-branch` 收尾（开 PR；注意开 PR 前 main 已同步至 `fa8ca3f`）。
