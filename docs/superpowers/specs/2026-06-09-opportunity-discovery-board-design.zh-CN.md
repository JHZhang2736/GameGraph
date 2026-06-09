# 6.5 机会发现看板:持久化 + 累积式去重 设计

> 状态:已与用户对齐,待评审。6.5 完善方向 **#1**(刷新不丢)+ 用户追加的「后端去重」,合为一个连贯特性。#2 SSE 为后续独立项。

## 1. 目标

把机会匹配从「每次全量重算、刷新即丢」改为**带记忆的累积式发现看板**:

- **刷新不丢**(#1):浏览器 localStorage 按画像 id 持久化已发现的机会;刷新/重进页面从本地恢复。
- **跨批去重**(追加需求):点「再来一批」时把**已见过的候选 id**发给后端,后端排除它们,只回没见过的新候选 → 逐步累积、不重复。

与已做的 #3 多样性互补:多样性让**单批**铺得开,去重让**跨批**不重复,合起来是「带记忆的增量探索」。探索仍在确定性引擎的有证据候选里进行,不越界。

## 2. UX 模型(累积 = 方案 A)

- 看板 = 该画像**至今所有已保留的机会**(`OpportunityArea` 列表),持久化在 localStorage。
- 按钮:看板空时显示「匹配机会」,非空时显示「再来一批」;点击都带上 `seen_ids` 请求,新机会**追加**到看板。
- 「清空看板」按钮:重置该画像的累积,从空开始。
- 被排除方向(rejected):只展示**当前这一批**;但其 id 进 `seen_ids`,不再复现。
- 候选卡保留现有 6.6「生成机会框架」入口(`onGenerate`)。
- 换画像:存储按画像 id 分键,自然从空看板开始。

## 3. 后端改动

### 3.1 请求体改形(`backend/app/api/routes_opportunity.py`)
`POST /opportunity/match` 的 body 从裸 `DeveloperProfile` 改为包装对象(仿同文件已有的 `OpportunityFrameRequest`):

```python
class OpportunityMatchRequest(StrictBaseModel):
    profile: DeveloperProfile
    seen_ids: list[NonEmptyStr] = Field(default_factory=list)
```

端点签名改为 `request: OpportunityMatchRequest`,调用 `match_opportunities(request.profile, repository, llm_client, seen_ids=request.seen_ids)`。
(需 import `NonEmptyStr`、`Field`;前端是唯一消费者,同步改,契约破坏可控。)

### 3.2 去重 + 枯竭提示(`backend/app/services/opportunity_service.py`)

`match_opportunities` 加可选参数 `seen_ids: Iterable[str] = ()`,在枚举后、排序前过滤:

```python
def match_opportunities(
    profile: DeveloperProfile,
    repository: SupportsGameDimensions,
    llm_client: SupportsOpportunityJudgment | None,
    seen_ids: Iterable[str] = (),
) -> OpportunityMatchResult:
    games = repository.fetch_game_dimensions()
    seen = set(seen_ids)
    enumerated = enumerate_candidates(games)
    fresh = [c for c in enumerated if c.id not in seen]
    candidates = rank_candidates(fresh)
    exhausted = [_EXHAUSTED_WARNING] if (enumerated and not fresh) else []

    if llm_client is None:
        return _fallback_result(profile.id, candidates, _NO_LLM_WARNING, exhausted)
    try:
        batch = llm_client.judge(profile, candidates)
    except Exception:
        logger.warning("Opportunity LLM judge failed; falling back", exc_info=True)
        return _fallback_result(profile.id, candidates, _LLM_FAILED_WARNING, exhausted)
    # ...(中段不变:按 batch 组装 areas/rejected/warnings)...
    return _finalize(profile.id, areas, rejected, [*exhausted, *warnings])
```

`_fallback_result` 加一个前置参数透传:

```python
def _fallback_result(profile_id, candidates, warning, extra_warnings=()):
    areas = [...]  # 不变
    return _finalize(profile_id, areas, [], [*extra_warnings, warning])
```

新增常量:
```python
_EXHAUSTED_WARNING = "已无更多新机会：当前图谱中可探索的候选已全部呈现，可入库更多游戏以拓宽。"
```

要点:`seen_ids` 为空时行为与现状完全一致(回归);全部见过时 `fresh` 为空 → `candidates` 空 → 走稀疏/枯竭提示,areas 为空。`rank_candidates`(含 #3 多样性,待 #36 合并)在 `fresh` 上运行,自然组合。

## 4. 前端改动

### 4.1 数据层(`frontend/lib/data/index.ts`)
`matchOpportunities` 加 `seenIds` 参数,body 改为包装对象:

```ts
export async function matchOpportunities(
  profile: DeveloperProfile,
  seenIds: string[] = [],
): Promise<OpportunityMatchResult> {
  const res = await fetch(`${apiBase()}/opportunity/match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile, seen_ids: seenIds }),
  });
  if (!res.ok) throw new Error(`POST /opportunity/match responded ${res.status}`);
  return (await res.json()) as OpportunityMatchResult;
}
```

### 4.2 hook(`frontend/lib/queries/index.ts`)
mutationFn 改收对象:

```ts
export function useMatchOpportunities() {
  return useMutation({
    mutationFn: ({ profile, seenIds }: { profile: DeveloperProfile; seenIds: string[] }) =>
      matchOpportunities(profile, seenIds),
  });
}
```

### 4.3 看板存储(新建 `frontend/lib/opportunity/board-storage.ts`,仿 `lib/profile/storage.ts`)
按画像 id 分键,SSR 安全:

```ts
export interface OpportunityBoard {
  areas: OpportunityArea[];
  seen_ids: string[];
}
const EMPTY_BOARD: OpportunityBoard = { areas: [], seen_ids: [] };
function key(profileId: string): string { return `gamegraph.opportunity-board.${profileId}`; }

export function loadBoard(profileId: string): OpportunityBoard   // 无/损坏/SSR → EMPTY_BOARD
export function saveBoard(profileId: string, board: OpportunityBoard): void
export function clearBoard(profileId: string): void
```

### 4.4 页面(`frontend/app/(workbench)/match/page.tsx` 改造)
- 本地状态:`areas: OpportunityArea[]`、`seenIds: string[]`、`latestRejected`、`latestWarnings`。
- **挂载/换画像恢复**:仿 profile 页的「渲染期同步 + lastProfileId」模式,当 `profile.id` 变化时从 `loadBoard(profile.id)` 载入看板。
- **匹配/再来一批**:`match.mutate({ profile, seenIds }, { onSuccess: (result) => { 追加 result.areas(按 id 去重保险)、并入 seenIds(新 areas id + rejected candidate_id)、saveBoard 持久化、记录 latestRejected/latestWarnings } })`。
- **清空看板**:`clearBoard(profile.id)`;重置状态。
- 按钮文案:`areas.length === 0 ? "匹配机会" : "再来一批"`;另置「清空看板」按钮(看板非空时显示)。
- 渲染:从累积 `areas` 渲染卡片(保留 `onGenerate` 6.6 入口);`latestRejected` 仅展示当前批;`latestWarnings` 顶部提示条(含枯竭提示)。
- 错误态保留;`isPending` 时按钮 loading。

## 5. 测试

### 后端
- `match_opportunities` 传 `seen_ids` → 对应候选被排除(StubRepo + 断言结果 areas 不含其 id)。
- `seen_ids` 覆盖全部候选 → areas 空 + 含枯竭警告。
- `seen_ids` 为空 → 行为同现状(回归)。
- API:`POST /opportunity/match` 收 `{ profile, seen_ids }` 正常 200;旧形(裸 profile)应 422(契约已改)。

### 前端
- `board-storage.test.ts`:save/load/clear 按画像分键;无数据→EMPTY_BOARD;损坏 JSON→EMPTY_BOARD。
- `api.test.ts`(更新):`matchOpportunities(profile, seenIds)` 请求体含 `seen_ids`;500 抛错。
- `match-page.test.tsx`:首次匹配填充看板并持久化;「再来一批」带上累积 `seen_ids` 且新结果追加;重挂载从存储恢复;清空看板置空;枯竭警告渲染。

## 6. 不做(YAGNI)
- 跨设备/后端持久化(仍纯 localStorage)。
- 被拒方向的累积展示(只展示当前批;但去重覆盖其 id)。
- SSE 流式(#2,独立项)。
- 看板内排序/筛选/删除单条(本期只「追加 + 清空」)。

## 7. 与并行工作的关系
- 依赖/共存 #36(#3 多样性,改 `rank_candidates`):本特性改 `match_opportunities` 不同函数 + 新增请求 schema + 前端,基本不冲突;若 #36 先合,`rank_candidates(fresh)` 自动叠加多样性。
- 不动 6.6 frame 相关(`/opportunity/frame`、`build_frame`、frame-history)。
