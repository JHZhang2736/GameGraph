# 6.5 机会匹配前端 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增「机会匹配」页,消费后端 `POST /opportunity/match`,展示候选机会区域 + 被拒方向 + 警告(C1 纯展示)。

**Architecture:** 前端三层照搬现有模式——`lib/types`(类型,镜像后端 schema)、`lib/data` + `lib/queries`(fetch + react-query mutation)、`app/(workbench)/match/page.tsx`(页面)+ `components/opportunity`(展示组件)+ `lib/opportunity/format.ts`(纯函数格式化)。不做选中/展开框架,不改 `/opportunities` 页。

**Tech Stack:** Next.js(app router,见 `frontend/AGENTS.md` 警告:此 Next 与训练数据有出入,写代码前查 `node_modules/next/dist/docs/`)、React、TypeScript、@tanstack/react-query、vitest + @testing-library/react + @testing-library/user-event、Tailwind。

**约定:** 所有命令从 `frontend/` 目录执行;所有 `git` 从 worktree 根执行(路径含 `frontend/`)。完整测试基线:`npm test` = 68 passed / 20 files。

参考 spec:`docs/superpowers/specs/2026-06-09-opportunity-matching-frontend-design.zh-CN.md`

---

### Task 1: TS 类型(镜像后端 opportunity schema)

**Files:**
- Modify: `frontend/lib/types/index.ts`(在文件末尾追加,不改动现有内容)
- Test: `frontend/lib/types/types.test.ts`(追加用例)

- [ ] **Step 1: 写失败测试**

在 `frontend/lib/types/types.test.ts` 的 import 中追加 `TRANSFORMATION_TYPES, RISK_POSTURES`,并在 `describe("shared type constants", ...)` 内追加两条用例:

```ts
  it("exposes transformation types", () => {
    expect(TRANSFORMATION_TYPES).toEqual(["substitute", "combine"]);
  });

  it("exposes risk postures", () => {
    expect(RISK_POSTURES).toEqual(["safe", "balanced", "challenging"]);
  });
```

import 行改为:
```ts
import {
  CONFIDENCE_LEVELS,
  QUALITY_STATUSES,
  CONSTRAINT_TYPES,
  EVALUATION_CATEGORIES,
  TRANSFORMATION_TYPES,
  RISK_POSTURES,
} from "@/lib/types";
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx vitest run lib/types/types.test.ts`
Expected: FAIL —`TRANSFORMATION_TYPES`/`RISK_POSTURES` 未导出。

- [ ] **Step 3: 追加类型与常量**

在 `frontend/lib/types/index.ts` **末尾追加**:

```ts
// 6.5 机会匹配(opportunity matching)。镜像后端 app/schemas/opportunity.py。
export const TRANSFORMATION_TYPES = ["substitute", "combine"] as const;
export type TransformationType = (typeof TRANSFORMATION_TYPES)[number];

export interface Transformation {
  type: TransformationType;
  // 替代: "Perspective" | "ArtStyle" | "Genre";组合: "Mechanic"
  dimension: string;
  from_value: string | null; // 替代必有;组合为 null
  to_value: string;
}

export interface OpportunityEvidence {
  anchor_game_id: string;
  target_value_game_ids: string[];
  combination_game_ids: string[];
}

export interface CandidateOpportunityArea {
  id: string;
  anchor_game_id: string;
  anchor_summary: string;
  transformation: Transformation;
  existing_combination_count: number; // 图谱中已有相同组合的游戏数;越小越新颖
  evidence: OpportunityEvidence;
}

export const RISK_POSTURES = ["safe", "balanced", "challenging"] as const;
export type RiskPosture = (typeof RISK_POSTURES)[number];

export interface OpportunityArea extends CandidateOpportunityArea {
  risk_posture: RiskPosture;
  fit_reason: string;
  risk_reason: string;
}

export interface RejectedOpportunity {
  candidate_id: string;
  rejection_reason: string;
}

export interface OpportunityMatchResult {
  profile_id: string;
  areas: OpportunityArea[];
  rejected: RejectedOpportunity[];
  warnings: string[];
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `npx vitest run lib/types/types.test.ts`
Expected: PASS(6 用例)。

- [ ] **Step 5: 提交**

```bash
git add frontend/lib/types/index.ts frontend/lib/types/types.test.ts
git commit -m "feat(types): add 6.5 opportunity matching types"
```

---

### Task 2: 纯函数格式化

**Files:**
- Create: `frontend/lib/opportunity/format.ts`
- Test: `frontend/lib/opportunity/format.test.ts`

- [ ] **Step 1: 写失败测试**

创建 `frontend/lib/opportunity/format.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import {
  formatTransformation,
  formatNovelty,
  riskPostureMeta,
} from "@/lib/opportunity/format";
import type { Transformation } from "@/lib/types";

describe("formatTransformation", () => {
  it("renders a substitute as dimension:from → to", () => {
    const t: Transformation = {
      type: "substitute",
      dimension: "Perspective",
      from_value: "第三人称",
      to_value: "第一人称",
    };
    expect(formatTransformation(t)).toBe("视角:第三人称 → 第一人称");
  });

  it("renders a combine as 借入<dimension>:<to>", () => {
    const t: Transformation = {
      type: "combine",
      dimension: "Mechanic",
      from_value: null,
      to_value: "多用途道具",
    };
    expect(formatTransformation(t)).toBe("借入机制:多用途道具");
  });

  it("falls back to the raw dimension when unmapped", () => {
    const t: Transformation = {
      type: "combine",
      dimension: "SomethingNew",
      from_value: null,
      to_value: "x",
    };
    expect(formatTransformation(t)).toBe("借入SomethingNew:x");
  });
});

describe("formatNovelty", () => {
  it("calls 0 a brand-new combination", () => {
    expect(formatNovelty(0)).toContain("全新组合");
  });

  it("reports the existing count when nonzero", () => {
    expect(formatNovelty(2)).toContain("图谱 2 款");
  });
});

describe("riskPostureMeta", () => {
  it("maps each posture to a Chinese label", () => {
    expect(riskPostureMeta("safe").label).toBe("稳健");
    expect(riskPostureMeta("balanced").label).toBe("平衡");
    expect(riskPostureMeta("challenging").label).toBe("挑战");
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx vitest run lib/opportunity/format.test.ts`
Expected: FAIL —模块不存在。

- [ ] **Step 3: 实现**

创建 `frontend/lib/opportunity/format.ts`:

```ts
import type { RiskPosture, Transformation } from "@/lib/types";

const DIMENSION_LABELS: Record<string, string> = {
  Perspective: "视角",
  ArtStyle: "美术风格",
  Genre: "类型",
  Mechanic: "机制",
};

// 替代: "视角:第三人称 → 第一人称";组合: "借入机制:多用途道具"
export function formatTransformation(t: Transformation): string {
  const dim = DIMENSION_LABELS[t.dimension] ?? t.dimension;
  if (t.type === "substitute") {
    return `${dim}:${t.from_value ?? "?"} → ${t.to_value}`;
  }
  return `借入${dim}:${t.to_value}`;
}

// 越小越新颖。后端 rank 已过滤到 <=2,但对任意 n 容错。
export function formatNovelty(existingCombinationCount: number): string {
  return existingCombinationCount === 0
    ? "全新组合"
    : `稀有组合(图谱 ${existingCombinationCount} 款)`;
}

export interface RiskMeta {
  label: string;
  className: string;
}

export function riskPostureMeta(posture: RiskPosture): RiskMeta {
  switch (posture) {
    case "safe":
      return { label: "稳健", className: "border-green-300 bg-green-50 text-green-700" };
    case "balanced":
      return { label: "平衡", className: "border-amber-300 bg-amber-50 text-amber-700" };
    case "challenging":
      return { label: "挑战", className: "border-red-300 bg-red-50 text-red-700" };
  }
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `npx vitest run lib/opportunity/format.test.ts`
Expected: PASS(6 用例)。

- [ ] **Step 5: 提交**

```bash
git add frontend/lib/opportunity/format.ts frontend/lib/opportunity/format.test.ts
git commit -m "feat(opportunity): add transformation/novelty/risk formatters"
```

---

### Task 3: 数据层 + 查询 hook

**Files:**
- Modify: `frontend/lib/data/index.ts`(新增 `matchOpportunities`)
- Modify: `frontend/lib/queries/index.ts`(新增 `useMatchOpportunities`)
- Test: `frontend/lib/data/api.test.ts`(追加用例)

- [ ] **Step 1: 写失败测试**

在 `frontend/lib/data/api.test.ts` 的 import 中加入 `matchOpportunities`,并追加用例:

```ts
  it("matchOpportunities posts the profile and parses the result", async () => {
    const result = {
      profile_id: "dev_profile_1",
      areas: [],
      rejected: [],
      warnings: ["图谱规模较小。"],
    };
    const fetchMock = mockFetch(200, result);
    vi.stubGlobal("fetch", fetchMock);
    const parsed = await matchOpportunities({ id: "dev_profile_1" } as never);
    expect(parsed.warnings).toEqual(["图谱规模较小。"]);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/opportunity/match");
    expect((init as RequestInit).method).toBe("POST");
  });

  it("matchOpportunities throws on a 500", async () => {
    vi.stubGlobal("fetch", mockFetch(500, {}));
    await expect(matchOpportunities({ id: "x" } as never)).rejects.toThrow();
  });
```

import 行(顶部)改为包含 `matchOpportunities`:
```ts
import {
  listGames,
  getNeighbors,
  searchGraphNodes,
  importGame,
  ImportError,
  matchOpportunities,
} from "@/lib/data";
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx vitest run lib/data/api.test.ts`
Expected: FAIL —`matchOpportunities` 未导出。

- [ ] **Step 3: 实现数据层函数**

在 `frontend/lib/data/index.ts` 的 import 类型清单里加入 `OpportunityMatchResult`(已存在的 `import type { ... } from "@/lib/types";` 块内追加该名字),并在文件中(`getOpportunityFrame` 之后)新增:

```ts
// 6.5 机会匹配。把开发者画像发给后端,拿回一批候选机会区域 + 被拒方向 + 警告。
// 这是一个由按钮触发的动作(非 load-on-mount),配套 hook 用 useMutation。
export async function matchOpportunities(
  profile: DeveloperProfile,
): Promise<OpportunityMatchResult> {
  const res = await fetch(`${apiBase()}/opportunity/match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  if (!res.ok) throw new Error(`POST /opportunity/match responded ${res.status}`);
  return (await res.json()) as OpportunityMatchResult;
}
```

(`DeveloperProfile` 已在该文件的类型 import 中。)

- [ ] **Step 4: 运行测试确认通过**

Run: `npx vitest run lib/data/api.test.ts`
Expected: PASS。

- [ ] **Step 5: 新增查询 hook**

在 `frontend/lib/queries/index.ts`:
- 顶部 `from "@/lib/data"` 的 import 清单追加 `matchOpportunities`;
- 顶部 `from "@/lib/types"` 的 import 改为 `import type { DeveloperProfile, ProfileParseInput } from "@/lib/types";`;
- 文件末尾追加:

```ts
export function useMatchOpportunities() {
  return useMutation({
    mutationFn: (profile: DeveloperProfile) => matchOpportunities(profile),
  });
}
```

(`useMutation` 已在顶部从 `@tanstack/react-query` 导入。)

- [ ] **Step 6: 运行全套确认无回归**

Run: `npm test`
Expected: 全绿(原 68 + 本任务新增用例,且类型编译通过)。

- [ ] **Step 7: 提交**

```bash
git add frontend/lib/data/index.ts frontend/lib/data/api.test.ts frontend/lib/queries/index.ts
git commit -m "feat(data): add matchOpportunities + useMatchOpportunities"
```

---

### Task 4: 候选卡组件

**Files:**
- Create: `frontend/components/opportunity/opportunity-candidate-card.tsx`
- Test: `frontend/components/opportunity/opportunity-candidate-card.test.tsx`

- [ ] **Step 1: 写失败测试**

创建 `frontend/components/opportunity/opportunity-candidate-card.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
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

describe("OpportunityCandidateCard", () => {
  it("renders the transformation, novelty, risk label, summary and reasons", () => {
    render(<OpportunityCandidateCard area={AREA} />);
    expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument();
    expect(screen.getByText("全新组合")).toBeInTheDocument();
    expect(screen.getByText("平衡")).toBeInTheDocument();
    expect(
      screen.getByText("吸血鬼幸存者:自动攻击的弹幕生存 roguelite"),
    ).toBeInTheDocument();
    expect(screen.getByText("契合短周期、强系统性的偏好。")).toBeInTheDocument();
    expect(screen.getByText("第一人称弹幕密度需要重新调校。")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx vitest run components/opportunity/opportunity-candidate-card.test.tsx`
Expected: FAIL —组件不存在。

- [ ] **Step 3: 实现组件**

创建 `frontend/components/opportunity/opportunity-candidate-card.tsx`:

```tsx
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `npx vitest run components/opportunity/opportunity-candidate-card.test.tsx`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add frontend/components/opportunity/opportunity-candidate-card.tsx frontend/components/opportunity/opportunity-candidate-card.test.tsx
git commit -m "feat(opportunity): add candidate card component"
```

---

### Task 5: 机会匹配页

**Files:**
- Create: `frontend/app/(workbench)/match/page.tsx`
- Test: `frontend/app/(workbench)/match/match-page.test.tsx`

- [ ] **Step 1: 写失败测试**

创建 `frontend/app/(workbench)/match/match-page.test.tsx`:

```tsx
import { afterEach, describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MatchPage from "@/app/(workbench)/match/page";
import type { OpportunityMatchResult } from "@/lib/types";

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

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
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
    expect(
      screen.getByText("图谱规模较小，新颖度判断偏粗。"),
    ).toBeInTheDocument();
    expect(screen.getByText(/不做在线多人/)).toBeInTheDocument();
  });

  it("shows an empty state when no areas match", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch(200, { profile_id: "p", areas: [], rejected: [], warnings: [] }),
    );
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText(/未匹配到候选/)).toBeInTheDocument(),
    );
  });

  it("shows an error state on a 500", async () => {
    vi.stubGlobal("fetch", mockFetch(500, {}));
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText("加载失败")).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx vitest run "app/(workbench)/match/match-page.test.tsx"`
Expected: FAIL —页面不存在。

- [ ] **Step 3: 实现页面**

创建 `frontend/app/(workbench)/match/page.tsx`:

```tsx
"use client";

import { Button } from "@/components/ui/button";
import {
  EmptyState,
  ErrorState,
  PageHeader,
} from "@/components/shell/view-states";
import { OpportunityCandidateCard } from "@/components/opportunity/opportunity-candidate-card";
import { useDeveloperProfile, useMatchOpportunities } from "@/lib/queries";

export default function MatchPage() {
  const { data: profile } = useDeveloperProfile();
  const match = useMatchOpportunities();
  const result = match.data;

  function runMatch() {
    if (profile) match.mutate(profile);
  }

  return (
    <div className="space-y-6">
      <PageHeader title="机会匹配" description="从你的画像匹配出的创新机会" />

      <div>
        <Button
          type="button"
          disabled={!profile || match.isPending}
          onClick={runMatch}
        >
          {match.isPending ? "匹配中…" : "匹配机会"}
        </Button>
      </div>

      {match.isError ? <ErrorState onRetry={runMatch} /> : null}

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
                <OpportunityCandidateCard key={area.id} area={area} />
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

- [ ] **Step 4: 运行测试确认通过**

Run: `npx vitest run "app/(workbench)/match/match-page.test.tsx"`
Expected: PASS(3 用例)。

- [ ] **Step 5: 提交**

```bash
git add "frontend/app/(workbench)/match/page.tsx" "frontend/app/(workbench)/match/match-page.test.tsx"
git commit -m "feat(match): add opportunity matching page"
```

---

### Task 6: 导航接入

**Files:**
- Modify: `frontend/lib/nav.ts`(创意流程组插入「机会匹配」)
- Test: `frontend/components/shell/app-sidebar.test.tsx`(追加断言)

- [ ] **Step 1: 写失败测试**

在 `frontend/components/shell/app-sidebar.test.tsx` 的用例里追加断言:

```tsx
    expect(screen.getByRole("link", { name: "机会匹配" })).toHaveAttribute(
      "href",
      "/match",
    );
```

放在现有 `机会框架` 断言之后即可。

- [ ] **Step 2: 运行测试确认失败**

Run: `npx vitest run components/shell/app-sidebar.test.tsx`
Expected: FAIL —找不到「机会匹配」链接。

- [ ] **Step 3: 实现导航**

修改 `frontend/lib/nav.ts`,在「创意流程」组的 `开发者画像` 与 `机会框架` 之间插入一项:

```ts
  {
    title: "创意流程",
    items: [
      { href: "/profile", label: "开发者画像" },
      { href: "/match", label: "机会匹配" },
      { href: "/opportunities", label: "机会框架" },
      { href: "/concepts", label: "概念卡" },
      { href: "/prototype", label: "原型简报" },
    ],
  },
```

- [ ] **Step 4: 运行测试确认通过**

Run: `npx vitest run components/shell/app-sidebar.test.tsx`
Expected: PASS。

- [ ] **Step 5: 全套回归 + 提交**

Run: `npm test`
Expected: 全绿。

```bash
git add frontend/lib/nav.ts frontend/components/shell/app-sidebar.test.tsx
git commit -m "feat(nav): add 机会匹配 entry to creative flow"
```

---

## 自检结果

**Spec 覆盖:** §3 类型→Task 1;§6 格式化→Task 2;§4 数据层 + §5 hook→Task 3;§7.1 候选卡→Task 4;§7.2 页面 + §8 状态→Task 5;§7.3 导航→Task 6;§9 测试分散在各任务。无遗漏。

**占位符扫描:** 无 TBD/TODO,每个改代码的步骤都给了完整代码。

**类型一致性:** `Transformation` / `OpportunityArea` / `OpportunityMatchResult` / `matchOpportunities` / `useMatchOpportunities` / `formatTransformation` / `formatNovelty` / `riskPostureMeta` / `OpportunityCandidateCard` 在定义与消费处签名一致。

**实现时需对照 PR #24 实测的点:** 组合类变形的 `dimension` 字符串(本计划假设 `"Mechanic"`)。`formatTransformation` 有 `?? t.dimension` 兜底,即使后端用别的串也只是少了中文映射、不报错。若后端 PR #24 已可本地起服务,实现者可发一次真实 `POST /opportunity/match` 核对响应字段名。
