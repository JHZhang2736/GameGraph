# 6.5 机会匹配前端 设计

> 状态:已与用户对齐,待评审。配套后端见 `2026-06-09-opportunity-matching-design.zh-CN.md`(6.5 后端,PR #24)。

## 1. 目标与范围

把已完成的 6.5 后端 `POST /opportunity/match` 接到前端:用户在「开发者画像」确认画像后,进入新的「机会匹配」页,点「匹配机会」按钮,看到一批从自己知识图谱里**真实匹配**出来的候选机会区域(锚点配方 × 一个创新变形 + 新颖度),以及被排除的方向和警告。

**范围 = C1 纯展示**:渲染候选列表 + 被拒方向 + 警告。**不做**候选的选中 / 高亮 / 存储,**不做**展开成机会框架(那是 6.6 的职责),**不改动**现有 `/opportunities` 页。

### 端到端切片
```
开发者画像(6.4,已实现)
   │  确认画像 → 存浏览器 storage
   ▼
机会匹配(6.5,本设计)   ← [匹配机会] 按钮 → POST /opportunity/match → 候选列表
   │  (挑选 → 展开框架,留给 6.6)
   ▼
机会框架(6.6,另一 agent 并发开发)
```

## 2. 消费的 API 契约(后端已实现)

```
POST /api/opportunity/match
  请求体: DeveloperProfile        (前端现有类型 lib/types DeveloperProfile)
  响应:   OpportunityMatchResult
```
`/api` 前缀经 Next rewrites 代理到后端(同 `listGames` 等现有调用)。无 LLM 配置时后端会降级为全量保留并在 `warnings[]` 说明——前端无需特殊处理,照常渲染。

## 3. 数据形状(镜像后端 `app/schemas/opportunity.py`)

新增到 `frontend/lib/types/index.ts`(全部为**新增**,不改动现有任何类型):

```ts
export type TransformationType = "substitute" | "combine";

export interface Transformation {
  type: TransformationType;
  dimension: string;            // 替代: "Perspective"|"ArtStyle"|"Genre";组合: "Mechanic"
  from_value: string | null;   // 替代必有;组合为 null
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
  existing_combination_count: number;   // 图谱中已有相同组合的游戏数;越小越新颖
  evidence: OpportunityEvidence;
}

export type RiskPosture = "safe" | "balanced" | "challenging";

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

> 注:与 6.6 约定的 `OpportunityFrame.warnings?: string[]` 增量**不在本设计范围**——本设计只新增上述类型,不触碰 `OpportunityFrame`,以免与 6.6 前端工作并发改同一类型块时冲突。

## 4. 数据层(`frontend/lib/data/index.ts`)

新增一个函数,沿用现有 `fetch` + `apiBase()` 模式:

```ts
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

## 5. 查询 hook(`frontend/lib/queries/index.ts`)

按钮触发的动作,用 `useMutation`(与 `useImportGame` 一致):

```ts
export function useMatchOpportunities() {
  return useMutation({
    mutationFn: (profile: DeveloperProfile) => matchOpportunities(profile),
  });
}
```

画像由现成的 `useDeveloperProfile()` 提供(确认过的存储画像,否则 golden-flow 回退)。

**取舍**:mutation 不缓存,离开页面结果即丢,符合「按钮触发」语义,且实现最简。代价是再次进入需重新点按钮——可接受。

## 6. 纯函数格式化(`frontend/lib/opportunity/format.ts`,新建,可单测)

把展示逻辑抽成无 React 依赖的纯函数,便于单测:

```ts
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

// 越小越新颖。rank 已过滤到 <=2,但对任意 n 容错。
export function formatNovelty(existingCombinationCount: number): string {
  return existingCombinationCount === 0
    ? "全新组合"
    : `稀有组合(图谱 ${existingCombinationCount} 款)`;
}

export interface RiskMeta { label: string; className: string }
export function riskPostureMeta(p: RiskPosture): RiskMeta {
  switch (p) {
    case "safe":
      return { label: "稳健", className: "border-green-300 bg-green-50 text-green-700" };
    case "balanced":
      return { label: "平衡", className: "border-amber-300 bg-amber-50 text-amber-700" };
    case "challenging":
      return { label: "挑战", className: "border-red-300 bg-red-50 text-red-700" };
  }
}
```

## 7. 组件与页面

### 7.1 候选卡 `frontend/components/opportunity/opportunity-candidate-card.tsx`
展示型组件,入参 `{ area: OpportunityArea }`,渲染:
- 顶部一行:风险档徽章(`riskPostureMeta`)+ 新颖度徽章(`formatNovelty`)
- 变形:`formatTransformation(area.transformation)`,作为卡片标题/主行(脊梁)
- 锚点配方:`area.anchor_summary`
- 适配理由 `fit_reason` / 风险理由 `risk_reason`,各一段
- 证据(次要,可折叠或弱化):锚点游戏 `anchor_game_id`、佐证目标值游戏数 `evidence.target_value_game_ids.length`(组合类再加 `combination_game_ids.length`)

复用现有 UI 原语(`components/ui/card`、`badge`、现有 `Chips` 风格)。

### 7.2 页面 `frontend/app/(workbench)/match/page.tsx`(client)
- `PageHeader title="机会匹配" description="从你的画像匹配出的创新机会"`
- 「匹配机会」按钮:`onClick` 取 `useDeveloperProfile()` 的画像 → `mutate(profile)`;`isPending` 时按钮 loading/禁用
- 画像尚未加载好时按钮禁用;`getDeveloperProfile` 总会返回(回退 golden-flow),故不做「无画像」硬阻断,仅在用回退样例时可选提示(YAGNI:本版不加)
- 结果区按 mutation 状态分支:
  - `isPending` → loading 提示
  - `isError` → `ErrorState`,重试 = 重新 `mutate`
  - 成功且 `areas.length > 0` → 候选卡列表(grid)
  - 成功且 `areas.length === 0` → 「未匹配到候选,可能与图谱规模或画像约束有关」
- `warnings[]`(非空):顶部提示条(复用 6.4/golden 的 warnings 视觉)
- 被拒方向 `rejected[]`(非空):次要区块,逐条列 `rejection_reason`;`candidate_id` 不直接展示给用户(语义不友好),本版仅展示原因文本

### 7.3 导航 `frontend/lib/nav.ts`
「创意流程」组在「开发者画像」与「机会框架」之间插入:
```ts
{ href: "/match", label: "机会匹配" },
```

## 8. 错误处理与边界状态

| 场景 | 表现 |
|---|---|
| 未点按钮(初始) | 仅显示标题 + 按钮,无结果区 |
| 请求中 | 按钮 loading,结果区 loading 提示 |
| 网络/5xx 错误 | `ErrorState` + 重试按钮 |
| `areas` 为空 | 空态文案 + 渲染 `warnings` |
| 有 `warnings` | 顶部提示条 |
| 有 `rejected` | 次要区块列原因 |

## 9. 测试(vitest + testing-library,沿用现有模式)

1. **`frontend/lib/opportunity/format.test.ts`**(纯函数):
   - `formatTransformation` 替代 → `视角:第三人称 → 第一人称`
   - `formatTransformation` 组合 → `借入机制:多用途道具`
   - `formatNovelty(0)` → 含「全新组合」;`formatNovelty(2)` → 含「图谱 2 款」
   - `riskPostureMeta` 三档 label 正确
2. **`frontend/lib/data/api.test.ts`**(扩展,`vi.stubGlobal("fetch", ...)`):
   - `matchOpportunities` 成功解析 `OpportunityMatchResult`
   - `!ok`(500)抛错
3. **`frontend/app/(workbench)/match/match-page.test.tsx`**(`QueryClientProvider` 包裹真实页面 + `vi.stubGlobal("fetch")` + `userEvent`):
   - 点「匹配机会」→ `waitFor` 候选变形文本出现、风险徽章出现、被拒原因出现、warning 出现
   - 空 `areas` → 空态文案出现
   - `!ok` → `ErrorState` 出现

## 10. 文件清单

| 动作 | 文件 | 职责 |
|---|---|---|
| 改 | `frontend/lib/types/index.ts` | 新增 6.5 类型(仅追加) |
| 改 | `frontend/lib/data/index.ts` | 新增 `matchOpportunities` |
| 改 | `frontend/lib/queries/index.ts` | 新增 `useMatchOpportunities` |
| 建 | `frontend/lib/opportunity/format.ts` | 纯函数格式化 |
| 建 | `frontend/lib/opportunity/format.test.ts` | 格式化单测 |
| 建 | `frontend/components/opportunity/opportunity-candidate-card.tsx` | 候选卡 |
| 建 | `frontend/app/(workbench)/match/page.tsx` | 机会匹配页 |
| 建 | `frontend/app/(workbench)/match/match-page.test.tsx` | 页面测试 |
| 改 | `frontend/lib/nav.ts` | 导航加「机会匹配」 |
| 改 | `frontend/lib/data/api.test.ts` | 加 `matchOpportunities` 测试 |

## 11. 明确不做(YAGNI / 留给 6.6)
- 候选选中、高亮、存储,展开成机会框架
- 改动现有 `/opportunities`(6.6)页
- `OpportunityFrame.warnings?` 类型增量(归 6.6 前端)
- 把 `candidate_id` 解析成人读说明(本版被拒区块只展示原因即可)
- 结果缓存 / 跨页持久化
```
