# 6.7 概念生成前端 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 mock 的 `/concepts` 页接到真实 `POST /concept/generate`：在 `/opportunities` 的每张机会框架卡上加「生成概念」按钮 → 生成 3 张 `ConceptCard` → 存 latest-only store → 跳 `/concepts` 渲染全字段概念卡。

**Architecture:** 沿用 6.6 前端既定约定（上游卡片按钮 → 生成下游 → 写 storage → 导航）。新增数据函数 `generateConcepts` + hook + latest-only concept store + 概念卡组件；改 `OpportunityFrameCard`（加按钮）、`/opportunities` 页（接 mutation）、`/concepts` 页（读 store 重写）。移除 6.7 的 mock query。不改后端、不改 `lib/types`。

**Tech Stack:** TypeScript / Next.js App Router（`next/navigation`、`next/link`）/ React 18 `useSyncExternalStore` / @tanstack/react-query / Tailwind / vitest + @testing-library/react。

**Spec:** `docs/superpowers/specs/2026-06-09-concept-generation-frontend-design.zh-CN.md`

---

## 约定与不变量（实现可依赖）

- 所有命令在 `frontend/` 下执行：`cd D:\Files\GameGraph\.claude\worktrees\concept-generation-frontend\frontend`。
- **本机 vitest 必须加 `--pool=threads`**，否则 forks pool teardown 崩。单文件：`npx vitest run <path> --pool=threads`；全量：`npx vitest run --pool=threads`。
- `frontend/AGENTS.md` 警示「This is NOT the Next.js you know」。本计划只用仓库已在用的 `next/navigation` 的 `useRouter`、`next/link`，不引入新 Next API；写代码前如对某 API 不确定，先查 `node_modules/next/dist/docs/`。
- `lib/types` 的 `ConceptCard` 已存在，字段为：`id, opportunity_frame_id, title, one_sentence_concept, core_fantasy, core_loop, main_player_decisions[], main_mechanics[], reference_sources[], difference_from_references, fit_reason, production_risks[], design_risks[], novelty_reason, suggested_prototype_scope`。`OpportunityFrame` 见 `lib/types`（含可选 `warnings?`）。**不改这两个类型。**
- 既有模式参照：数据函数 `buildOpportunityFrame`（`lib/data/index.ts`）、store `lib/opportunity/frame-history.ts`、其测试 `frame-history.test.ts` / `build-frame.test.ts`、router mock 见 `match-page.test.tsx`。
- `apiBase()` 已在 `lib/data/index.ts`（返回 `/api`），复用。

---

## Task 1: 数据函数 `generateConcepts` + 错误类型 + hook

**Files:**
- Modify: `frontend/lib/data/index.ts`
- Modify: `frontend/lib/queries/index.ts`
- Test: `frontend/lib/data/concept-generate.test.ts`

- [ ] **Step 1: 写失败测试**

新建 `frontend/lib/data/concept-generate.test.ts`:

```ts
import { afterEach, describe, it, expect, vi } from "vitest";
import { generateConcepts, ConceptGenerationError } from "@/lib/data";
import type { ConceptCard, OpportunityFrame } from "@/lib/types";

const FRAME: OpportunityFrame = {
  id: "frame|opp|a|sub|Perspective|第一人称",
  developer_profile_id: "p",
  opportunity_area: "第一人称生存割草",
  source_game_ids: ["a", "b"],
  related_mechanics: ["护符定制"],
  related_player_experiences: ["紧张"],
  related_constraints: ["低美术成本"],
  related_innovation_patterns: ["数值滚雪球"],
  recommended_transformations: ["主变形"],
  forbidden_directions: ["禁止"],
  evidence_path: ["rel"],
  fit_reason: "f",
  risk_reason: "r",
};

const CARD: ConceptCard = {
  id: "concept|frame|opp|a|sub|Perspective|第一人称|1",
  opportunity_frame_id: FRAME.id,
  title: "概念1",
  one_sentence_concept: "一句话",
  core_fantasy: "幻想",
  core_loop: "循环",
  main_player_decisions: ["决策"],
  main_mechanics: ["机制"],
  reference_sources: ["a"],
  difference_from_references: "差异",
  fit_reason: "适配",
  production_risks: ["制作风险"],
  design_risks: ["设计风险"],
  novelty_reason: "新颖",
  suggested_prototype_scope: "原型范围",
};

afterEach(() => vi.restoreAllMocks());

describe("generateConcepts", () => {
  it("POSTs { frame } to /api/concept/generate and returns the cards", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => [CARD] });
    vi.stubGlobal("fetch", fetchMock);

    const result = await generateConcepts(FRAME);

    expect(result).toHaveLength(1);
    expect(result[0].id).toBe(CARD.id);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/concept/generate");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ frame: FRAME });
  });

  it("throws ConceptGenerationError carrying the status on 503", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({}) }),
    );
    await expect(generateConcepts(FRAME)).rejects.toMatchObject({
      name: "ConceptGenerationError",
      status: 503,
    });
  });

  it("throws ConceptGenerationError carrying the status on 502", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 502, json: async () => ({}) }),
    );
    await expect(generateConcepts(FRAME)).rejects.toBeInstanceOf(ConceptGenerationError);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npx vitest run lib/data/concept-generate.test.ts --pool=threads`
Expected: FAIL —— `generateConcepts` / `ConceptGenerationError` 不存在（import 报错）。

- [ ] **Step 3: 加数据函数与错误类型**

在 `frontend/lib/data/index.ts`，在 `buildOpportunityFrame` 函数**之后**新增（紧邻其下，保持「6.x 动作型数据函数」聚在一起）:

```ts
// 6.7 概念生成。把选中的机会框架发给后端，拿回 3 张概念卡。按钮触发，hook 用 useMutation。
// 区分错误码：503=未配置 LLM、502=生成失败（见 ConceptGenerationError.status）。
export class ConceptGenerationError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ConceptGenerationError";
  }
}

export async function generateConcepts(frame: OpportunityFrame): Promise<ConceptCard[]> {
  const res = await fetch(`${apiBase()}/concept/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ frame }),
  });
  if (!res.ok) {
    throw new ConceptGenerationError(
      `POST /concept/generate responded ${res.status}`,
      res.status,
    );
  }
  return (await res.json()) as ConceptCard[];
}
```

（`ConceptCard`、`OpportunityFrame` 已在该文件顶部的 `import type { ... } from "@/lib/types"` 中；若 `ConceptCard` 因后续 Task 4 清理而被移除请保留——本函数用到它。）

- [ ] **Step 4: 加 hook**

在 `frontend/lib/queries/index.ts`:

顶部从 `@/lib/data` 的 import 列表里加入 `generateConcepts`（与 `buildOpportunityFrame` 并列）。
顶部 `import type { ... } from "@/lib/types"` 里确保有 `OpportunityFrame`（与 `OpportunityArea`/`DeveloperProfile` 并列；没有就加）。
在文件末尾 `useBuildOpportunityFrame` 之后新增:

```ts
export function useGenerateConcepts() {
  return useMutation({
    mutationFn: (frame: OpportunityFrame) => generateConcepts(frame),
  });
}
```

- [ ] **Step 5: 跑测试确认通过**

Run: `npx vitest run lib/data/concept-generate.test.ts --pool=threads`
Expected: PASS（3 passed）

- [ ] **Step 6: 提交**

```bash
git add lib/data/index.ts lib/queries/index.ts lib/data/concept-generate.test.ts
git commit -m "feat(frontend): generateConcepts data fn + useGenerateConcepts hook"
```

---

## Task 2: latest-only concept store

**Files:**
- Create: `frontend/lib/concept/concept-store.ts`
- Test: `frontend/lib/concept/concept-store.test.ts`

- [ ] **Step 1: 写失败测试**

新建 `frontend/lib/concept/concept-store.test.ts`:

```ts
import { afterEach, describe, it, expect } from "vitest";
import {
  LATEST_CONCEPTS_KEY,
  clearConcepts,
  loadLatestConcepts,
  saveConcepts,
} from "@/lib/concept/concept-store";
import type { ConceptCard, OpportunityFrame } from "@/lib/types";

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

function card(id: string): ConceptCard {
  return {
    id,
    opportunity_frame_id: "frame|a",
    title: "标题",
    one_sentence_concept: "一句话",
    core_fantasy: "幻想",
    core_loop: "循环",
    main_player_decisions: ["决策"],
    main_mechanics: ["机制"],
    reference_sources: ["a"],
    difference_from_references: "差异",
    fit_reason: "适配",
    production_risks: ["制作风险"],
    design_risks: ["设计风险"],
    novelty_reason: "新颖",
    suggested_prototype_scope: "原型范围",
  };
}

afterEach(() => {
  localStorage.clear();
});

describe("concept-store", () => {
  it("starts null", () => {
    expect(loadLatestConcepts()).toBeNull();
  });

  it("saves and loads the latest set", () => {
    saveConcepts(frame("frame|a", "区域A"), [card("c1"), card("c2"), card("c3")]);
    const latest = loadLatestConcepts();
    expect(latest?.frame.opportunity_area).toBe("区域A");
    expect(latest?.cards.map((c) => c.id)).toEqual(["c1", "c2", "c3"]);
  });

  it("overwrites the previous set (latest-only)", () => {
    saveConcepts(frame("frame|a"), [card("c1")]);
    saveConcepts(frame("frame|b", "新"), [card("c9")]);
    const latest = loadLatestConcepts();
    expect(latest?.frame.id).toBe("frame|b");
    expect(latest?.cards.map((c) => c.id)).toEqual(["c9"]);
  });

  it("returns a stable reference when storage is unchanged", () => {
    saveConcepts(frame("frame|a"), [card("c1")]);
    expect(loadLatestConcepts()).toBe(loadLatestConcepts());
  });

  it("clears the set", () => {
    saveConcepts(frame("frame|a"), [card("c1")]);
    clearConcepts();
    expect(loadLatestConcepts()).toBeNull();
  });

  it("ignores corrupt storage", () => {
    localStorage.setItem(LATEST_CONCEPTS_KEY, "{not json");
    expect(loadLatestConcepts()).toBeNull();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npx vitest run lib/concept/concept-store.test.ts --pool=threads`
Expected: FAIL —— 模块不存在。

- [ ] **Step 3: 写 store**

新建 `frontend/lib/concept/concept-store.ts`:

```ts
// 浏览器侧「最近一次生成的概念」单槽存储（latest-only）。仿 lib/opportunity/frame-history.ts
// 的 useSyncExternalStore 写法：用 raw 字符串缓存解析快照，数据未变时返回稳定引用，
// 避免 useSyncExternalStore 无限重渲染。重新生成即覆盖。
import type { ConceptCard, OpportunityFrame } from "@/lib/types";

export const LATEST_CONCEPTS_KEY = "gamegraph.latest-concepts";

export interface ConceptSet {
  frame: OpportunityFrame;
  cards: ConceptCard[];
}

function parse(raw: string | null): ConceptSet | null {
  if (!raw) return null;
  try {
    const value = JSON.parse(raw);
    if (value && typeof value === "object" && value.frame && Array.isArray(value.cards)) {
      return value as ConceptSet;
    }
    return null;
  } catch {
    return null;
  }
}

let snapshotRaw: string | null = null;
let snapshot: ConceptSet | null = null;

const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((listener) => listener());
}

export function loadLatestConcepts(): ConceptSet | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(LATEST_CONCEPTS_KEY);
  if (raw !== snapshotRaw) {
    snapshotRaw = raw;
    snapshot = parse(raw);
  }
  return snapshot;
}

export function subscribeConcepts(onChange: () => void): () => void {
  listeners.add(onChange);
  let removeStorage = () => {};
  if (typeof window !== "undefined") {
    const handler = (event: StorageEvent) => {
      if (event.key === null || event.key === LATEST_CONCEPTS_KEY) onChange();
    };
    window.addEventListener("storage", handler);
    removeStorage = () => window.removeEventListener("storage", handler);
  }
  return () => {
    listeners.delete(onChange);
    removeStorage();
  };
}

export function saveConcepts(frame: OpportunityFrame, cards: ConceptCard[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(LATEST_CONCEPTS_KEY, JSON.stringify({ frame, cards }));
  emit();
}

export function clearConcepts(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(LATEST_CONCEPTS_KEY);
  emit();
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `npx vitest run lib/concept/concept-store.test.ts --pool=threads`
Expected: PASS（6 passed）

- [ ] **Step 5: 提交**

```bash
git add lib/concept/concept-store.ts lib/concept/concept-store.test.ts
git commit -m "feat(frontend): latest-only concept store"
```

---

## Task 3: 概念卡展示组件 `ConceptCardView`

**Files:**
- Create: `frontend/components/concept/concept-card.tsx`
- Test: `frontend/components/concept/concept-card.test.tsx`

- [ ] **Step 1: 写失败测试**

新建 `frontend/components/concept/concept-card.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConceptCardView } from "@/components/concept/concept-card";
import type { ConceptCard } from "@/lib/types";

const CARD: ConceptCard = {
  id: "concept|f|1",
  opportunity_frame_id: "f",
  title: "第一人称护符割草",
  one_sentence_concept: "用护符构筑在第一人称视角扛过兽潮",
  core_fantasy: "孤身靠 build 翻盘",
  core_loop: "探索→拾取→构筑→应对兽潮",
  main_player_decisions: ["先拿哪枚护符"],
  main_mechanics: ["护符定制"],
  reference_sources: ["vampire_survivors"],
  difference_from_references: "搬到第一人称的近身视野",
  fit_reason: "契合 solo 短局",
  production_risks: ["第一人称美术成本"],
  design_risks: ["视角削弱割草爽快"],
  novelty_reason: "第一人称割草稀缺",
  suggested_prototype_scope: "单关卡 + 3 枚护符",
};

describe("ConceptCardView", () => {
  it("renders title, one-sentence, and the full creative fields", () => {
    render(<ConceptCardView card={CARD} />);
    expect(screen.getByText("第一人称护符割草")).toBeInTheDocument();
    expect(screen.getByText(/用护符构筑/)).toBeInTheDocument();
    expect(screen.getByText("孤身靠 build 翻盘")).toBeInTheDocument();
    expect(screen.getByText("探索→拾取→构筑→应对兽潮")).toBeInTheDocument();
    expect(screen.getByText("先拿哪枚护符")).toBeInTheDocument();
    expect(screen.getByText("护符定制")).toBeInTheDocument();
    expect(screen.getByText("vampire_survivors")).toBeInTheDocument();
    expect(screen.getByText(/搬到第一人称/)).toBeInTheDocument();
    expect(screen.getByText("契合 solo 短局")).toBeInTheDocument();
    expect(screen.getByText("第一人称美术成本")).toBeInTheDocument();
    expect(screen.getByText("视角削弱割草爽快")).toBeInTheDocument();
    expect(screen.getByText("第一人称割草稀缺")).toBeInTheDocument();
    expect(screen.getByText("单关卡 + 3 枚护符")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npx vitest run components/concept/concept-card.test.tsx --pool=threads`
Expected: FAIL —— 组件不存在。

- [ ] **Step 3: 写组件**

新建 `frontend/components/concept/concept-card.tsx`:

```tsx
import type { ConceptCard } from "@/lib/types";

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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
        {label}
      </div>
      <div className="mt-1 text-sm">{children}</div>
    </div>
  );
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="list-disc pl-5 text-sm">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export function ConceptCardView({ card }: { card: ConceptCard }) {
  return (
    <article className="flex flex-col gap-3 rounded-lg border p-4">
      <h2 className="font-semibold">{card.title}</h2>
      <p className="text-sm text-muted-foreground">{card.one_sentence_concept}</p>

      <Field label="核心幻想">{card.core_fantasy}</Field>
      <Field label="核心循环">{card.core_loop}</Field>
      <Field label="主要玩家决策">
        <Bullets items={card.main_player_decisions} />
      </Field>
      <Field label="主要机制">
        <Chips items={card.main_mechanics} />
      </Field>
      <Field label="参考来源">
        <Chips items={card.reference_sources} />
      </Field>
      <Field label="与参考差异">{card.difference_from_references}</Field>
      <Field label="适配理由">{card.fit_reason}</Field>
      <Field label="新颖理由">{card.novelty_reason}</Field>
      <Field label="制作风险">
        <Bullets items={card.production_risks} />
      </Field>
      <Field label="设计风险">
        <Bullets items={card.design_risks} />
      </Field>
      <Field label="建议原型范围">{card.suggested_prototype_scope}</Field>
    </article>
  );
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `npx vitest run components/concept/concept-card.test.tsx --pool=threads`
Expected: PASS（1 passed）

- [ ] **Step 5: 提交**

```bash
git add components/concept/concept-card.tsx components/concept/concept-card.test.tsx
git commit -m "feat(frontend): full-field concept card component"
```

---

## Task 4: 重写 `/concepts` 页读 store + 移除 mock query

**Files:**
- Modify: `frontend/app/(workbench)/concepts/page.tsx`（整文件重写）
- Modify: `frontend/lib/data/index.ts`（删除 `getConcepts` / `ConceptsBundle`）
- Modify: `frontend/lib/queries/index.ts`（删除 `useConcepts`）
- Test: `frontend/app/(workbench)/concepts/concepts-page.test.tsx`（整文件重写）

- [ ] **Step 1: 写失败测试（重写）**

把 `frontend/app/(workbench)/concepts/concepts-page.test.tsx` 整个替换为:

```tsx
import { afterEach, describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ConceptsPage from "@/app/(workbench)/concepts/page";
import { saveConcepts } from "@/lib/concept/concept-store";
import type { ConceptCard, OpportunityFrame } from "@/lib/types";

function frame(area = "第一人称生存割草"): OpportunityFrame {
  return {
    id: "frame|opp|a|sub|Perspective|第一人称",
    developer_profile_id: "p",
    opportunity_area: area,
    source_game_ids: ["a"],
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

function card(id: string, title: string): ConceptCard {
  return {
    id,
    opportunity_frame_id: "frame|opp|a|sub|Perspective|第一人称",
    title,
    one_sentence_concept: "一句话",
    core_fantasy: "幻想",
    core_loop: "循环",
    main_player_decisions: ["决策"],
    main_mechanics: ["机制"],
    reference_sources: ["a"],
    difference_from_references: "差异",
    fit_reason: "适配",
    production_risks: ["制作风险"],
    design_risks: ["设计风险"],
    novelty_reason: "新颖",
    suggested_prototype_scope: "原型范围",
  };
}

afterEach(() => {
  localStorage.clear();
});

describe("ConceptsPage", () => {
  it("shows an empty state with a link to opportunities when there is no concept set", () => {
    render(<ConceptsPage />);
    expect(screen.getByText(/还没有概念/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /去机会框架/ })).toBeInTheDocument();
  });

  it("renders the generated cards and the frame context header", () => {
    saveConcepts(frame("第一人称生存割草"), [
      card("c1", "概念一"),
      card("c2", "概念二"),
      card("c3", "概念三"),
    ]);
    render(<ConceptsPage />);
    expect(screen.getByText("概念一")).toBeInTheDocument();
    expect(screen.getByText("概念二")).toBeInTheDocument();
    expect(screen.getByText("概念三")).toBeInTheDocument();
    expect(screen.getByText(/第一人称生存割草/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npx vitest run app/\(workbench\)/concepts/concepts-page.test.tsx --pool=threads`
Expected: FAIL —— 旧页面用 `useConcepts`，新测试断言空态/store 渲染，不匹配（或编译错误）。

- [ ] **Step 3: 重写页面**

把 `frontend/app/(workbench)/concepts/page.tsx` 整个替换为:

```tsx
"use client";

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { EmptyState, PageHeader } from "@/components/shell/view-states";
import { ConceptCardView } from "@/components/concept/concept-card";
import { loadLatestConcepts, subscribeConcepts } from "@/lib/concept/concept-store";

export default function ConceptsPage() {
  const latest = useSyncExternalStore(subscribeConcepts, loadLatestConcepts, () => null);

  if (!latest || latest.cards.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader title="概念卡" description="由机会框架生成的具体概念" />
        <EmptyState message="还没有概念，先去机会框架选一个方向生成。" />
        <Link
          href="/opportunities"
          className="text-sm text-primary underline-offset-4 hover:underline"
        >
          去机会框架 →
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="概念卡"
        description={`为「${latest.frame.opportunity_area}」生成的概念`}
      />
      <div className="grid items-start gap-4 md:grid-cols-2 xl:grid-cols-3">
        {latest.cards.map((card) => (
          <ConceptCardView key={card.id} card={card} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 移除 mock query**

在 `frontend/lib/data/index.ts`：删除 `ConceptsBundle` 接口与 `getConcepts` 函数（整段）。删除后，若 `ConceptEvaluation` 类型 import 因此变为未使用，则从顶部 `import type { ... } from "@/lib/types"` 移除 `ConceptEvaluation`（保留 `ConceptCard`——`generateConcepts` 用）。

在 `frontend/lib/queries/index.ts`：删除 `useConcepts` 函数；并从顶部 `@/lib/data` import 列表移除 `getConcepts`。

- [ ] **Step 5: 确认无其它引用**

Run（grep 校验没有遗留引用）: 用 Grep 工具搜 `getConcepts|useConcepts|ConceptsBundle` 于 `frontend/`。
Expected: 仅本次改动后无任何引用（0 命中）。若有，按上述方式清理。

- [ ] **Step 6: 跑测试确认通过**

Run: `npx vitest run app/\(workbench\)/concepts/concepts-page.test.tsx --pool=threads`
Expected: PASS（2 passed）

- [ ] **Step 7: 提交**

```bash
git add app/\(workbench\)/concepts/page.tsx app/\(workbench\)/concepts/concepts-page.test.tsx lib/data/index.ts lib/queries/index.ts
git commit -m "feat(frontend): concepts page reads latest concept store; drop mock query"
```

---

## Task 5: `OpportunityFrameCard` 加「生成概念」按钮

**Files:**
- Modify: `frontend/components/opportunity/opportunity-frame-card.tsx`
- Test: `frontend/components/opportunity/opportunity-frame-card.test.tsx`（追加用例）

- [ ] **Step 1: 写失败测试**

在 `frontend/components/opportunity/opportunity-frame-card.test.tsx` **追加**一个用例（沿用该文件已有的 `frame(...)` helper 与 imports；若文件没有 `userEvent` import 则加 `import userEvent from "@testing-library/user-event";`）:

```tsx
it("calls onGenerateConcepts with the frame when the button is clicked", async () => {
  const onGenerateConcepts = vi.fn();
  const user = userEvent.setup();
  render(
    <OpportunityFrameCard
      frame={frame("frame|a", "区域A")}
      onGenerateConcepts={onGenerateConcepts}
    />,
  );
  await user.click(screen.getByRole("button", { name: "生成概念" }));
  expect(onGenerateConcepts).toHaveBeenCalledWith(frame("frame|a", "区域A"));
});
```

（注：`frame("frame|a","区域A")` 两次构造的是等值对象，`toHaveBeenCalledWith` 做深比较即可。确保测试文件顶部 `import { describe, it, expect, vi } from "vitest";` 含 `vi`，且 import 了 `userEvent`、`render`、`screen`。若该测试文件此前是纯渲染、未引入这些，按需补 import。）

- [ ] **Step 2: 跑测试确认失败**

Run: `npx vitest run components/opportunity/opportunity-frame-card.test.tsx --pool=threads`
Expected: FAIL —— 没有名为「生成概念」的按钮。

- [ ] **Step 3: 加按钮与 props**

在 `frontend/components/opportunity/opportunity-frame-card.tsx`：

把组件签名的 props 扩展为（新增 `onGenerateConcepts` 与 `isGenerating`）:

```tsx
export function OpportunityFrameCard({
  frame,
  defaultOpen = false,
  highlighted = false,
  onRemove,
  onGenerateConcepts,
  isGenerating = false,
}: {
  frame: OpportunityFrame;
  defaultOpen?: boolean;
  highlighted?: boolean;
  onRemove?: (id: string) => void;
  onGenerateConcepts?: (frame: OpportunityFrame) => void;
  isGenerating?: boolean;
}) {
```

在 `<header>` 内、`{onRemove ? ... : null}` 之**前**插入「生成概念」按钮（与「移除」并列，始终可点，无需展开）:

```tsx
        {onGenerateConcepts ? (
          <Button
            type="button"
            size="xs"
            onClick={() => onGenerateConcepts(frame)}
            disabled={isGenerating}
          >
            {isGenerating ? "生成中…" : "生成概念"}
          </Button>
        ) : null}
```

（`Button` 已在文件顶部 import；`OpportunityFrame` 类型已 import。其余 JSX 不变。）

- [ ] **Step 4: 跑测试确认通过**

Run: `npx vitest run components/opportunity/opportunity-frame-card.test.tsx --pool=threads`
Expected: PASS（原有用例 + 新用例全过）

- [ ] **Step 5: 提交**

```bash
git add components/opportunity/opportunity-frame-card.tsx components/opportunity/opportunity-frame-card.test.tsx
git commit -m "feat(frontend): add 生成概念 button to opportunity frame card"
```

---

## Task 6: `/opportunities` 页接入生成→存→导航 + 全量回归

**Files:**
- Modify: `frontend/app/(workbench)/opportunities/page.tsx`
- Test: `frontend/app/(workbench)/opportunities/opportunities-page.test.tsx`（追加用例 + 包一层 QueryClient）

- [ ] **Step 1: 写失败测试（重写测试文件）**

把 `frontend/app/(workbench)/opportunities/opportunities-page.test.tsx` 整个替换为（在原有 3 个用例基础上：加 QueryClient 包裹、router/fetch mock，新增「生成概念→存→导航」「503 文案」两个用例）:

```tsx
import { afterEach, describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import OpportunitiesPage from "@/app/(workbench)/opportunities/page";
import { rememberLastFrameId, upsertFrame } from "@/lib/opportunity/frame-history";
import type { ConceptCard, OpportunityFrame } from "@/lib/types";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pushMock }) }));

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

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

function card(id: string): ConceptCard {
  return {
    id,
    opportunity_frame_id: "frame|a",
    title: "概念",
    one_sentence_concept: "一句话",
    core_fantasy: "幻想",
    core_loop: "循环",
    main_player_decisions: ["决策"],
    main_mechanics: ["机制"],
    reference_sources: ["a"],
    difference_from_references: "差异",
    fit_reason: "适配",
    production_risks: ["制作风险"],
    design_risks: ["设计风险"],
    novelty_reason: "新颖",
    suggested_prototype_scope: "原型范围",
  };
}

afterEach(() => {
  vi.restoreAllMocks();
  pushMock.mockClear();
  localStorage.clear();
  sessionStorage.clear();
});

describe("OpportunitiesPage", () => {
  it("shows an empty state with a link to match when there is no history", () => {
    renderWithClient(<OpportunitiesPage />);
    expect(screen.getByText(/还没有机会框架/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /去机会匹配/ })).toBeInTheDocument();
  });

  it("renders frames from history newest-first", () => {
    upsertFrame(frame("frame|a", "区域A"));
    upsertFrame(frame("frame|b", "区域B"));
    renderWithClient(<OpportunitiesPage />);
    expect(screen.getByText("区域A")).toBeInTheDocument();
    expect(screen.getByText("区域B")).toBeInTheDocument();
  });

  it("auto-expands the just-generated frame", async () => {
    upsertFrame(frame("frame|a", "区域A"));
    rememberLastFrameId("frame|a");
    renderWithClient(<OpportunitiesPage />);
    expect(await screen.findByText("禁止方向")).toBeInTheDocument();
  });

  it("generates concepts, stores them, and navigates to /concepts", async () => {
    const user = userEvent.setup();
    upsertFrame(frame("frame|a", "区域A"));
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => [card("c1"), card("c2"), card("c3")],
      }),
    );
    renderWithClient(<OpportunitiesPage />);
    await user.click(screen.getByRole("button", { name: "生成概念" }));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/concepts"));
    const stored = JSON.parse(localStorage.getItem("gamegraph.latest-concepts")!);
    expect(stored.frame.id).toBe("frame|a");
    expect(stored.cards.map((c: ConceptCard) => c.id)).toEqual(["c1", "c2", "c3"]);
  });

  it("shows the 503 message and does not navigate when LLM is unconfigured", async () => {
    const user = userEvent.setup();
    upsertFrame(frame("frame|a", "区域A"));
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({}) }),
    );
    renderWithClient(<OpportunitiesPage />);
    await user.click(screen.getByRole("button", { name: "生成概念" }));
    await waitFor(() =>
      expect(screen.getByText(/需配置 LLM/)).toBeInTheDocument(),
    );
    expect(pushMock).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npx vitest run app/\(workbench\)/opportunities/opportunities-page.test.tsx --pool=threads`
Expected: FAIL —— 当前页面没有「生成概念」按钮/不接 mutation。

- [ ] **Step 3: 重写页面**

把 `frontend/app/(workbench)/opportunities/page.tsx` 整个替换为:

```tsx
"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
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
import { saveConcepts } from "@/lib/concept/concept-store";
import { ConceptGenerationError } from "@/lib/data";
import { useGenerateConcepts } from "@/lib/queries";
import type { OpportunityFrame } from "@/lib/types";

function generationErrorMessage(error: unknown): string {
  if (error instanceof ConceptGenerationError) {
    if (error.status === 503) return "需配置 LLM 才能生成概念。";
    if (error.status === 502) return "概念生成失败，可重试。";
  }
  return "加载失败";
}

export default function OpportunitiesPage() {
  const router = useRouter();
  const frames = useSyncExternalStore(subscribeFrames, loadFrames, () => []);
  // lazy 初始化时 peek（纯读，不改 storage），使高亮项首帧即展开；清除放到 effect。
  const [lastId] = useState<string | null>(() => peekLastFrameId());
  const generate = useGenerateConcepts();
  const [generatingId, setGeneratingId] = useState<string | null>(null);

  useEffect(() => {
    clearLastFrameId();
  }, []);

  function generateConcepts(frame: OpportunityFrame) {
    setGeneratingId(frame.id);
    generate.mutate(frame, {
      onSuccess: (cards) => {
        saveConcepts(frame, cards);
        router.push("/concepts");
      },
      onSettled: () => setGeneratingId(null),
    });
  }

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
      {generate.isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {generationErrorMessage(generate.error)}
        </div>
      ) : null}
      <div className="space-y-4">
        {frames.map((frame) => (
          <OpportunityFrameCard
            key={frame.id}
            frame={frame}
            defaultOpen={frame.id === lastId}
            highlighted={frame.id === lastId}
            onRemove={removeFrame}
            onGenerateConcepts={generateConcepts}
            isGenerating={generatingId === frame.id}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `npx vitest run app/\(workbench\)/opportunities/opportunities-page.test.tsx --pool=threads`
Expected: PASS（5 passed）

- [ ] **Step 5: 全量回归 + 类型检查**

Run: `npx vitest run --pool=threads`
Expected: 全绿（基线 111 + 本计划新增约 12 = 约 123 passed，0 failed；具体数字以实际为准，关键是 0 failed）。

Run: `npx tsc --noEmit`
Expected: 无类型错误（若报未使用 import，按 Task 4 Step 4 清理）。

- [ ] **Step 6: 提交**

```bash
git add app/\(workbench\)/opportunities/page.tsx app/\(workbench\)/opportunities/opportunities-page.test.tsx
git commit -m "feat(frontend): generate concepts from frame card and navigate to /concepts"
```

---

## Self-Review

**1. Spec coverage（逐节核对）:**
- §3 触发模式（frame 卡按钮 → 生成 → 存 → 跳）→ Task 5（按钮）+ Task 6（wiring）✓
- §4 latest-only store → Task 2 ✓
- §5 `generateConcepts` + `ConceptGenerationError` + `useGenerateConcepts` → Task 1 ✓；删 `getConcepts/ConceptsBundle/useConcepts` → Task 4 ✓
- §6 503/502 文案就地显示 → Task 6 `generationErrorMessage` + 测试 ✓
- §7 改动单元（data/queries/store/frame-card/opportunities/concepts/concept-card + 测试）→ Task 1–6 全覆盖 ✓
- §8 概念卡全字段、扁平、移除评估徽章 → Task 3（全字段）+ Task 4（页面无徽章）✓
- §9 空态指向 /opportunities → Task 4 ✓
- §10 测试映射（数据函数/store/frame 卡按钮/两页/503）→ 各 Task TDD ✓
- §11 范围外（6.8/全量历史/后端）→ 未触碰 ✓
- §12 不改 types、复用 apiBase、不引新 Next API → 全程遵守 ✓

**2. Placeholder scan:** 无 TBD/TODO；每个 code step 含完整代码或精确编辑指令。✓

**3. Type consistency:**
- `ConceptGenerationError{status}`（Task 1 定义，Task 6 `instanceof` 判定一致）✓
- `generateConcepts(frame) -> Promise<ConceptCard[]>`（Task 1 定义，Task 6 经 `useGenerateConcepts` 调用一致）✓
- `ConceptSet { frame, cards }` + `saveConcepts/loadLatestConcepts/subscribeConcepts/clearConcepts` + key `gamegraph.latest-concepts`（Task 2 定义，Task 4/6 与测试一致）✓
- `ConceptCardView({ card })`（Task 3 定义，Task 4 页面使用一致）✓
- `OpportunityFrameCard` 新增 `onGenerateConcepts(frame)`/`isGenerating`（Task 5 定义，Task 6 传参一致）✓
- 按钮名「生成概念」/「生成中…」（Task 5 实现与 Task 5/6 测试断言一致）✓

**执行顺序:** Task 1 → 2 → 3 → 4 → 5 → 6（Task 4 依赖 1/2/3；Task 6 依赖 1/2/5）。每个任务测试集可分别验证；Task 6 含全量回归与 tsc。
