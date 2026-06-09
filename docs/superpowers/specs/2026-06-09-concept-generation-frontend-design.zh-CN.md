# 6.7 概念生成前端设计 Spec

## 1. 目的与范围

把当前 mock 的 `/concepts` 页接到真实后端 `POST /concept/generate`：从 6.6 已生成的某个 `OpportunityFrame` 触发概念生成，渲染后端返回的 3 张 `ConceptCard`。

**范围 = 把「机会框架 → 概念卡」这一段接通**，沿用 6.6 已确立的交互约定（上游产物卡片加按钮 → 生成下游 → 写 storage → 跳下一页）。**不做** 6.8 概念评估（评分/分类/徽章），**不做**全量概念历史，**不动**后端。

本设计在 6.6 机会框架前端下游、6.8 概念评估前端上游。

## 2. 现状（origin/main `94f5bc7`，已含 6.6 前端）

- `/match`：候选卡 `OpportunityCandidateCard` 有「生成机会框架」按钮 → `useBuildOpportunityFrame` → `POST /opportunity/frame` → `upsertFrame` + `rememberLastFrameId` → `router.push("/opportunities")`。
- `/opportunities`：`useSyncExternalStore(subscribeFrames, loadFrames)` 读 **frame history store**（`lib/opportunity/frame-history.ts`，localStorage），渲染多张可折叠 `OpportunityFrameCard`（最新高亮展开，可删除）。
- `/concepts`：**仍是 mock** —— `useConcepts()` → `getConcepts()` 返回 `{ cards, evaluations }`（golden-flow），load-on-mount 显示卡 + 评估徽章。
- 后端 `POST /concept/generate { frame }` → `ConceptCard[]`（恒 3 张），错误 503（未配置 LLM）/ 502（生成失败）/ 422（请求非法）已就绪。
- 前端 `lib/types` 的 `ConceptCard` 已存在且字段与后端一致，**本设计不改 types**。

## 3. 核心模型：frame → 3 张概念卡（沿用 6.6 约定）

6.6 确立的模式是「上游产物卡片上的按钮生成下游产物并导航」。6.7 把它**精确下沉一层**：

```
/opportunities 的某张 OpportunityFrameCard
   │  新增「生成概念」按钮
   ▼ generateConcepts.mutate(frame) → POST /api/concept/generate { frame } → ConceptCard[]
   │  onSuccess: saveConcepts(frame, cards) + router.push("/concepts")
   │  onError:   就地显示 503/502 文案（不跳转）
   ▼
/concepts  读 concept store（latest-only）→ 渲染 frame 主题 + 3 张全字段概念卡
```

**触发点** = 每张 frame 卡上的「生成概念」按钮（仿候选卡的 `onGenerate` / `isGenerating`）。

## 4. 概念持久化：latest-only

只持久化「最近一次生成」的结果 `{ frame, cards }`（仿 frame-history 的「刚生成」语义，但只保留一组）：

- 新建 `lib/concept/concept-store.ts`，仿 `lib/opportunity/frame-history.ts` 的 `useSyncExternalStore` + 快照缓存写法（用 raw 字符串缓存解析快照，使数据未变时返回稳定引用，避免无限重渲染）。
- 写在 **localStorage** 单槽（key 如 `gamegraph.latest-concepts`），存 `{ frame: OpportunityFrame, cards: ConceptCard[] }`。重新生成 → 覆盖。
- 接口：`saveConcepts(frame, cards)` / `loadLatestConcepts(): { frame, cards } | null` / `subscribeConcepts(onChange)` / `clearConcepts()`。
- 从 /opportunities 生成后 `router.push("/concepts")`，/concepts 用 `useSyncExternalStore` 读出该槽即时呈现；刷新后仍在（localStorage）。

> 选 latest-only（而非全量按 frame 分组的历史）：契合「选一个 frame → 看它的概念」主流程，store 与页面都最简。全量历史留后续平滑升级。

## 5. 数据函数与 hook

`lib/data/index.ts` 新增（仿 `buildOpportunityFrame`）：

```ts
export class ConceptGenerationError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ConceptGenerationError";
  }
}

// 6.7 概念生成。把选中的机会框架发给后端，拿回 3 张概念卡。按钮触发，hook 用 useMutation。
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

`lib/queries/index.ts` 新增：

```ts
export function useGenerateConcepts() {
  return useMutation({
    mutationFn: (frame: OpportunityFrame) => generateConcepts(frame),
  });
}
```

**清理**：`getConcepts` / `ConceptsBundle` / `useConcepts` 不再被任何页面使用 → 删除（移除 6.7 的 mock）。`goldenFlow.concept_cards` / `concept_evaluations` 仍可保留在 fixture（其它处或 6.8 可能引用，本设计不动 fixture）。

## 6. 错误处理（区分 503/502）

错误显示在触发处（/opportunities，页级 banner，不跳转——与 match 页 `buildFrame.isError` 同位）：

| status | 文案 |
|---|---|
| 503 | 需配置 LLM 才能生成概念。 |
| 502 | 概念生成失败，可重试。 |
| 其他 | 加载失败 |

从 `useGenerateConcepts().error` 取 `ConceptGenerationError.status` 决定文案。

## 7. 改动单元

| 文件 | 责任 | 动作 |
|---|---|---|
| `lib/data/index.ts` | `generateConcepts(frame)` + `ConceptGenerationError`；删除 `getConcepts`/`ConceptsBundle` | 改 |
| `lib/queries/index.ts` | `useGenerateConcepts()`；删除 `useConcepts` | 改 |
| `lib/concept/concept-store.ts` | latest-only store（仿 frame-history 快照写法） | 新 |
| `components/opportunity/opportunity-frame-card.tsx` | 加 `onGenerateConcepts(frame)` + `isGenerating` props 与「生成概念」按钮 | 改 |
| `app/(workbench)/opportunities/page.tsx` | 接 `useGenerateConcepts`，逐卡 `generatingId`，onSuccess 存+跳，onError 页级 503/502 文案 | 改 |
| `app/(workbench)/concepts/page.tsx` | 重写：读 store → frame 主题 header + 3 张全字段卡；空态引导去 /opportunities；移除评估徽章 | 改 |
| `components/concept/concept-card.tsx` | 单张概念卡展示组件（全字段），供 `/concepts` 页 map 渲染 | 新 |
| 对应 `*.test.tsx` / `*.test.ts` | 数据函数 / store / frame 卡按钮 / 两页 测试 | 新/改 |

## 8. 概念卡展示（全字段，扁平）

每张 `ConceptCard` 显示全部创意字段：标题、一句话概念、核心幻想、核心循环、主要玩家决策、主要机制、参考来源、与参考差异、适配理由、制作风险、设计风险、新颖理由、建议原型范围。无折叠。`/concepts` 顶部 header 用 `frame.opportunity_area` 给出「为哪个机会生成」的上下文。

**移除评估徽章**：真卡来自 API，无法匹配 mock 评估（id 不同）；评估属 6.8，本期不显示。

## 9. /concepts 空态

无 store 数据时显示空态 + 链接「先去机会框架生成一个概念 →」指向 `/opportunities`（仿 /opportunities 空态指向 /match）。

## 10. 测试（vitest，本机须 `--pool=threads`）

| 验收点 | 测试 |
|---|---|
| `generateConcepts` 发对请求、解析卡 | mock `fetch`，断言 POST `/concept/generate` body `{frame}`、返回 cards |
| 503/502 抛带 status 的错误 | mock 非 2xx → 断言 `ConceptGenerationError.status` |
| store 存取/清/快照稳定 | 仿 `frame-history.test.ts`：save/load/clear，未变时引用稳定 |
| frame 卡按钮触发 | 点「生成概念」调 `onGenerateConcepts(frame)` |
| /opportunities 生成 → 导航 | mock `next/navigation` `useRouter`，点按钮 → fetch + `router.push("/concepts")`；503/502 文案 |
| /concepts 渲染 / 空态 | 预置 store → 渲染 3 张卡关键字段；无 store → 空态 + 链接 |

## 11. 范围外（留后续）

- 6.8 概念评估（评分/分类/徽章）。
- 全量概念历史（按 frame 分组、多组保留）——本期 latest-only。
- 6.6 frame 生成本身（已完成）。
- 后端任何改动。

## 12. 跨模块 / 约定

- 复用 6.6 的 `apiBase()`（前端 `/api` 经 Next rewrites 代理到后端）。
- 复用 6.6 的导航/按钮/storage 约定，保持创意流程四页（画像→匹配→框架→概念）一致的手感。
- `lib/types` 不改。
- **Next 注意**：仓库 `frontend/AGENTS.md` 警示「This is NOT the Next.js you know」，实现期写代码前须查 `node_modules/next/dist/docs/`；本设计只用已在用的 `next/navigation` `useRouter`、`next/link`，不引入新 Next API。
