# 机会发现看板(持久化 + 累积式去重)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 机会匹配改为「带记忆的累积式发现看板」——前端按画像 localStorage 持久化已发现机会(刷新不丢),「再来一批」把已见候选 id 发给后端去重,只回新候选。

**Architecture:** 后端 `/opportunity/match` body 改为 `{ profile, seen_ids }`,`match_opportunities` 在枚举后按 `seen_ids` 过滤再排序,空池给枯竭提示。前端 `matchOpportunities` 带 `seenIds`,新建按画像分键的看板存储,改造 match 页:挂载恢复看板、匹配结果追加、提供「再来一批 / 清空看板」。

**Tech Stack:** Python 3.12 + Pydantic v2 + FastAPI + pytest(后端);Next.js app-router + React + @tanstack/react-query + vitest/@testing-library(前端)。前端见 `frontend/AGENTS.md`:此 Next 与训练数据有出入,改前用到框架 API 时查 `node_modules/next/dist/docs/`。

**约定:** 后端命令从 `backend/` 跑、前端从 `frontend/` 跑;git 从 worktree 根跑(路径含 `backend/`、`frontend/`)。基线:后端 `python -m pytest -q` = 161 passed, 5 deselected;前端 `npm test` = 111 passed / 28 files。

参考 spec:`docs/superpowers/specs/2026-06-09-opportunity-discovery-board-design.zh-CN.md`

---

### Task 1: 后端服务 —— `seen_ids` 去重 + 枯竭提示

**Files:**
- Modify: `backend/app/services/opportunity_service.py`
- Test: `backend/tests/test_opportunity_service.py`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_opportunity_service.py` 末尾追加(沿用文件内已有的 `StubRepo`、`StubLlm`、`_profile`、`_games`、`enumerate_candidates`、`rank_candidates`):

```python
def test_match_excludes_seen_candidates() -> None:
    from app.services.opportunity_service import enumerate_candidates, rank_candidates
    ranked = rank_candidates(enumerate_candidates(_games()))
    assert len(ranked) >= 2  # 夹具应产出多个候选,便于排除其一
    seen = ranked[0].id
    batch = OpportunityJudgmentBatch(judgments=[], warnings=[])
    result = match_opportunities(_profile(), StubRepo(_games()), StubLlm(batch), seen_ids=[seen])
    all_ids = [a.id for a in result.areas] + [r.candidate_id for r in result.rejected]
    assert seen not in all_ids


def test_match_warns_when_all_candidates_seen() -> None:
    from app.services.opportunity_service import enumerate_candidates
    every_id = [c.id for c in enumerate_candidates(_games())]
    batch = OpportunityJudgmentBatch(judgments=[], warnings=[])
    result = match_opportunities(_profile(), StubRepo(_games()), StubLlm(batch), seen_ids=every_id)
    assert result.areas == []
    assert any("已无更多新机会" in w for w in result.warnings)


def test_match_empty_seen_ids_is_unchanged() -> None:
    batch = OpportunityJudgmentBatch(judgments=[], warnings=[])
    a = match_opportunities(_profile(), StubRepo(_games()), StubLlm(batch))
    b = match_opportunities(_profile(), StubRepo(_games()), StubLlm(batch), seen_ids=[])
    assert [x.id for x in a.areas] == [x.id for x in b.areas]
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_opportunity_service.py -k "seen or all_candidates_seen" -v`
Expected: FAIL —`match_opportunities` 还没有 `seen_ids` 参数(TypeError)。

- [ ] **Step 3: 实现**

在 `backend/app/services/opportunity_service.py`:

(a) 顶部 import 区加(若尚无):
```python
from collections.abc import Iterable
```

(b) 在现有 `_LLM_FAILED_WARNING` 等常量附近新增:
```python
_EXHAUSTED_WARNING = "已无更多新机会：当前图谱中可探索的候选已全部呈现，可入库更多游戏以拓宽。"
```

(c) 给 `_fallback_result` 加一个前置透传参数(其余不变):
```python
def _fallback_result(
    profile_id: str,
    candidates: list[CandidateOpportunityArea],
    warning: str,
    extra_warnings: Iterable[str] = (),
) -> OpportunityMatchResult:
    areas = [
        _area_from_candidate(
            c, RiskPosture.BALANCED, _FALLBACK_FIT_REASON, _FALLBACK_RISK_REASON
        )
        for c in candidates
    ]
    return _finalize(profile_id, areas, [], [*extra_warnings, warning])
```

(d) 改 `match_opportunities` 的开头与三个返回点。把函数开头:
```python
    games = repository.fetch_game_dimensions()
    candidates = rank_candidates(enumerate_candidates(games))

    if llm_client is None:
        return _fallback_result(profile.id, candidates, _NO_LLM_WARNING)

    try:
        batch = llm_client.judge(profile, candidates)
    except Exception:
        logger.warning("Opportunity LLM judge failed; falling back", exc_info=True)
        return _fallback_result(profile.id, candidates, _LLM_FAILED_WARNING)
```
替换为(签名加 `seen_ids`,过滤,枯竭计算,两处 fallback 透传 `exhausted`):
```python
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
```
并把函数签名改为:
```python
def match_opportunities(
    profile: DeveloperProfile,
    repository: SupportsGameDimensions,
    llm_client: SupportsOpportunityJudgment | None,
    seen_ids: Iterable[str] = (),
) -> OpportunityMatchResult:
```
最后,把函数末尾的正常返回(读文件确认其形如 `return _finalize(profile.id, areas, rejected, warnings)`)改为:
```python
    return _finalize(profile.id, areas, rejected, [*exhausted, *warnings])
```

- [ ] **Step 4: 运行确认通过 + 全量回归**

Run: `python -m pytest tests/test_opportunity_service.py -v`
Expected: 新 3 个 + 现有全部 PASS。
Run: `python -m pytest -q`
Expected: 全绿(现有 161 + 新 3)。

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/opportunity_service.py backend/tests/test_opportunity_service.py
git commit -m "feat(opportunity): exclude seen_ids in match_opportunities + exhaustion warning"
```
提交信息末尾空一行加:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

### Task 2: 后端 API —— 请求体改为 `{ profile, seen_ids }`

**Files:**
- Modify: `backend/app/api/routes_opportunity.py`
- Test: `backend/tests/test_opportunity_api.py`

- [ ] **Step 1: 写/改失败测试**

打开 `backend/tests/test_opportunity_api.py`,把现有「快乐路径」用例里 POST `/opportunity/match` 的 body 从「裸 profile dict」改为 `{"profile": <profile dict>, "seen_ids": []}`;并新增一条断言旧形(裸 profile)返回 422 的用例。具体:

- 找到现有 `client.post("/opportunity/match", json=<profile>)`,改为 `client.post("/opportunity/match", json={"profile": <profile>, "seen_ids": []})`,其余断言不变。
- 追加:
```python
def test_match_endpoint_rejects_bare_profile_body(...):
    # 复用该文件已有的 client / profile 夹具构造方式
    resp = client.post("/opportunity/match", json=<bare profile dict>)
    assert resp.status_code == 422
```
（请先读该测试文件,复用其既有的 app/client fixture、`dependency_overrides` 与 profile 构造方式,不要新造。）

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_opportunity_api.py -v`
Expected: 改过的快乐路径用例 FAIL(当前端点收裸 profile,新 body 形状 422),或新 422 用例尚未成立 —— 取决于端点尚未改。

- [ ] **Step 3: 实现**

在 `backend/app/api/routes_opportunity.py`:
- import 区把 `from app.schemas.common import StrictBaseModel` 改为 `from app.schemas.common import NonEmptyStr, StrictBaseModel`,并新增 `from pydantic import Field`。
- 在 `match_endpoint` 之前新增请求 schema(仿同文件已有的 `OpportunityFrameRequest`):
```python
class OpportunityMatchRequest(StrictBaseModel):
    profile: DeveloperProfile
    seen_ids: list[NonEmptyStr] = Field(default_factory=list)
```
- 改端点:
```python
@router.post("/opportunity/match", response_model=OpportunityMatchResult)
def match_endpoint(
    request: OpportunityMatchRequest,
    repository: OpportunityRepository = Depends(get_opportunity_repository),
    llm_client: OpportunityLlmClient | None = Depends(get_opportunity_llm),
) -> OpportunityMatchResult:
    return match_opportunities(
        request.profile, repository, llm_client, seen_ids=request.seen_ids
    )
```

- [ ] **Step 4: 运行确认通过 + 全量回归**

Run: `python -m pytest tests/test_opportunity_api.py -v`  → PASS
Run: `python -m pytest -q`  → 全绿

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/routes_opportunity.py backend/tests/test_opportunity_api.py
git commit -m "feat(opportunity): wrap match request as {profile, seen_ids}"
```
末尾空一行加 trailer:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

### Task 3: 前端数据层 + hook —— 传 `seenIds`

**Files:**
- Modify: `frontend/lib/data/index.ts`
- Modify: `frontend/lib/queries/index.ts`
- Test: `frontend/lib/data/api.test.ts`

- [ ] **Step 1: 改失败测试**

在 `frontend/lib/data/api.test.ts` 的 `matchOpportunities` 两个用例里:
- 快乐路径:调用改为 `matchOpportunities({ id: "dev_profile_1" } as never, ["opp|seen|1"])`,并在断言里加:
```ts
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.seen_ids).toEqual(["opp|seen|1"]);
    expect(body.profile).toEqual({ id: "dev_profile_1" });
```
（保留原有 url/method 断言。）
- 500 用例:调用改为 `matchOpportunities({ id: "x" } as never, [])`。

- [ ] **Step 2: 运行确认失败**

Run（从 `frontend/`）: `npx vitest run lib/data/api.test.ts`
Expected: FAIL —`matchOpportunities` 还是单参、body 是裸 profile。

- [ ] **Step 3: 实现**

`frontend/lib/data/index.ts` 把 `matchOpportunities` 替换为:
```ts
// 6.5 机会匹配。把开发者画像 + 已见候选 id 发给后端,拿回一批没见过的新候选。
// seen_ids 用于跨批去重(累积式发现看板)。按钮触发,配套 hook 用 useMutation。
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

`frontend/lib/queries/index.ts` 把 `useMatchOpportunities` 替换为:
```ts
export function useMatchOpportunities() {
  return useMutation({
    mutationFn: ({ profile, seenIds }: { profile: DeveloperProfile; seenIds: string[] }) =>
      matchOpportunities(profile, seenIds),
  });
}
```
（`DeveloperProfile` 已在该文件 import;`matchOpportunities` 已 import。）

- [ ] **Step 4: 运行确认通过**

Run: `npx vitest run lib/data/api.test.ts`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add frontend/lib/data/index.ts frontend/lib/queries/index.ts frontend/lib/data/api.test.ts
git commit -m "feat(data): matchOpportunities sends seen_ids; hook takes {profile, seenIds}"
```
末尾空一行加 trailer:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

### Task 4: 前端看板存储(按画像分键)

**Files:**
- Create: `frontend/lib/opportunity/board-storage.ts`
- Test: `frontend/lib/opportunity/board-storage.test.ts`

- [ ] **Step 1: 写失败测试**

创建 `frontend/lib/opportunity/board-storage.test.ts`:
```ts
import { afterEach, describe, it, expect } from "vitest";
import { loadBoard, saveBoard, clearBoard } from "@/lib/opportunity/board-storage";
import type { OpportunityArea } from "@/lib/types";

const AREA: OpportunityArea = {
  id: "opp|a|sub|Perspective|第一人称",
  anchor_game_id: "a",
  anchor_summary: "s",
  transformation: { type: "substitute", dimension: "Perspective", from_value: "第三人称", to_value: "第一人称" },
  existing_combination_count: 0,
  evidence: { anchor_game_id: "a", target_value_game_ids: ["g0"], combination_game_ids: [] },
  risk_posture: "balanced",
  fit_reason: "f",
  risk_reason: "r",
};

afterEach(() => localStorage.clear());

describe("board-storage", () => {
  it("returns an empty board when nothing is stored", () => {
    expect(loadBoard("p1")).toEqual({ areas: [], seen_ids: [] });
  });

  it("saves and loads a board keyed by profile id", () => {
    saveBoard("p1", { areas: [AREA], seen_ids: ["opp|a|sub|Perspective|第一人称"] });
    expect(loadBoard("p1")).toEqual({ areas: [AREA], seen_ids: ["opp|a|sub|Perspective|第一人称"] });
    expect(loadBoard("p2")).toEqual({ areas: [], seen_ids: [] }); // 不同画像互不影响
  });

  it("clears a profile's board", () => {
    saveBoard("p1", { areas: [AREA], seen_ids: ["x"] });
    clearBoard("p1");
    expect(loadBoard("p1")).toEqual({ areas: [], seen_ids: [] });
  });

  it("returns an empty board on corrupt json", () => {
    localStorage.setItem("gamegraph.opportunity-board.p1", "{not json");
    expect(loadBoard("p1")).toEqual({ areas: [], seen_ids: [] });
  });
});
```

- [ ] **Step 2: 运行确认失败**

Run: `npx vitest run lib/opportunity/board-storage.test.ts`
Expected: FAIL —模块不存在。

- [ ] **Step 3: 实现**

创建 `frontend/lib/opportunity/board-storage.ts`(仿 `lib/profile/storage.ts` 的 SSR 安全写法):
```ts
// 按开发者画像分键的「机会发现看板」浏览器持久化:累积已保留的机会(areas)与
// 已见候选 id(seen_ids,用于跨批去重)。纯 localStorage,刷新/重进可恢复。
import type { OpportunityArea } from "@/lib/types";

export interface OpportunityBoard {
  areas: OpportunityArea[];
  seen_ids: string[];
}

const EMPTY_BOARD: OpportunityBoard = { areas: [], seen_ids: [] };

function key(profileId: string): string {
  return `gamegraph.opportunity-board.${profileId}`;
}

export function loadBoard(profileId: string): OpportunityBoard {
  if (typeof window === "undefined") return EMPTY_BOARD;
  const raw = window.localStorage.getItem(key(profileId));
  if (!raw) return EMPTY_BOARD;
  try {
    const parsed = JSON.parse(raw) as Partial<OpportunityBoard>;
    return {
      areas: Array.isArray(parsed.areas) ? parsed.areas : [],
      seen_ids: Array.isArray(parsed.seen_ids) ? parsed.seen_ids : [],
    };
  } catch {
    return EMPTY_BOARD;
  }
}

export function saveBoard(profileId: string, board: OpportunityBoard): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key(profileId), JSON.stringify(board));
}

export function clearBoard(profileId: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(key(profileId));
}
```

- [ ] **Step 4: 运行确认通过**

Run: `npx vitest run lib/opportunity/board-storage.test.ts`
Expected: PASS（4 用例）。

- [ ] **Step 5: 提交**

```bash
git add frontend/lib/opportunity/board-storage.ts frontend/lib/opportunity/board-storage.test.ts
git commit -m "feat(opportunity): per-profile localStorage board (persist areas + seen_ids)"
```
末尾空一行加 trailer:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

### Task 5: 改造 match 页 —— 累积看板 + 持久化 + 再来一批 + 清空

**Files:**
- Modify: `frontend/app/(workbench)/match/page.tsx`
- Test: `frontend/app/(workbench)/match/match-page.test.tsx`

**集成约束(务必先读这两个现有文件再动手):**
- 现页面已含 6.6「生成机会框架」流程:`useBuildOpportunityFrame`、`generate(area)`、`onGenerate`/`isGenerating` 传给 `OpportunityCandidateCard`、成功后 `upsertFrame` + `rememberLastFrameId` + `router.push("/opportunities")`。**这套必须原样保留**。
- 现有 4 个测试(快乐路径渲染、空态、500 错误、生成框架并跳转)需在改造后仍通过——按新行为(累积看板)更新它们的写法,但断言意图不变;尤其「生成框架」用例的两段 `mockResolvedValueOnce` 和 `gamegraph.opportunity-frames` / `last-frame-id` 断言要保留。

- [ ] **Step 1: 写/改测试(先红)**

把 `frontend/app/(workbench)/match/match-page.test.tsx` 更新为:保留并适配现有 4 个用例,新增 3 个累积/持久化用例。要点:
- `useMatchOpportunities` 现在 mutate 的入参是 `{ profile, seenIds }`,但页面内部调用,测试仍通过 `vi.stubGlobal("fetch", ...)` 在 HTTP 层打桩,无需改 mock 方式。
- 看板按 `profile.id` 持久化到 `localStorage` key `gamegraph.opportunity-board.<profileId>`(profile 来自 `useDeveloperProfile`,即 golden-flow 样例画像;其 id 由该夹具决定 —— 测试里用 `loadBoard`/通过 key 前缀断言,不要硬编码具体 id,改用 `Object.keys(localStorage)` 找 `gamegraph.opportunity-board.` 前缀)。
- 新增用例(完整代码):
```ts
  it("appends results into a persisted board", async () => {
    vi.stubGlobal("fetch", mockFetch(200, RESULT));
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument(),
    );
    const boardKey = Object.keys(localStorage).find((k) =>
      k.startsWith("gamegraph.opportunity-board."),
    );
    expect(boardKey).toBeDefined();
    const board = JSON.parse(localStorage.getItem(boardKey!)!);
    expect(board.areas).toHaveLength(1);
    expect(board.seen_ids).toContain("opp|vampire_survivors|sub|Perspective|第一人称");
    expect(board.seen_ids).toContain("opp|x|comb|Mechanic|在线匹配"); // 被拒 id 也进 seen
  });

  it("restores the board on remount (survives refresh)", async () => {
    vi.stubGlobal("fetch", mockFetch(200, RESULT));
    const first = renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument(),
    );
    first.unmount();
    renderWithClient(<MatchPage />); // 重新挂载,无需再点
    await waitFor(() =>
      expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument(),
    );
  });

  it("clears the board", async () => {
    vi.stubGlobal("fetch", mockFetch(200, RESULT));
    const user = userEvent.setup();
    renderWithClient(<MatchPage />);
    await clickMatch();
    await waitFor(() =>
      expect(screen.getByText("视角:第三人称 → 第一人称")).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "清空看板" }));
    await waitFor(() =>
      expect(screen.queryByText("视角:第三人称 → 第一人称")).not.toBeInTheDocument(),
    );
  });
```
- 适配现有用例:`clickMatch` 仍找名为「匹配机会」的按钮(看板初始为空时按钮即此文案),保持不变。空态用例:空 areas 仍渲染「未匹配到候选」提示——保留。

- [ ] **Step 2: 运行确认失败**

Run: `npx vitest run "app/(workbench)/match/match-page.test.tsx"`
Expected: 新用例 FAIL(页面尚无看板持久化/清空)。

- [ ] **Step 3: 实现页面改造**

把 `frontend/app/(workbench)/match/page.tsx` 改为累积看板模型,**保留 6.6 generate 流程**。关键行为:
- 引入 `loadBoard / saveBoard / clearBoard`(`@/lib/opportunity/board-storage`)与其 `OpportunityBoard` 类型。
- 本地状态:`areas: OpportunityArea[]`、`seenIds: string[]`、`latestRejected: RejectedOpportunity[]`、`latestWarnings: string[]`,以及 `lastProfileId: string | null`。
- **渲染期同步**(仿 profile 页):当 `profile && profile.id !== lastProfileId` 时,`setLastProfileId(profile.id)` 并从 `loadBoard(profile.id)` 载入 `areas`/`seenIds`(同时清空 latestRejected/Warnings)。
- `runMatch()`:`if (!profile) return;` 然后 `match.mutate({ profile, seenIds }, { onSuccess: (result) => { const merged = [...areas, ...result.areas.filter(a => !areas.some(x => x.id === a.id))]; const nextSeen = Array.from(new Set([...seenIds, ...result.areas.map(a => a.id), ...result.rejected.map(r => r.candidate_id)])); setAreas(merged); setSeenIds(nextSeen); setLatestRejected(result.rejected); setLatestWarnings(result.warnings); saveBoard(profile.id, { areas: merged, seen_ids: nextSeen }); } })`。
- `clearAll()`:`if (!profile) return;` `clearBoard(profile.id); setAreas([]); setSeenIds([]); setLatestRejected([]); setLatestWarnings([]);`。
- 按钮区:主按钮 `disabled={!profile || match.isPending}` `onClick={runMatch}`,文案 `match.isPending ? "匹配中…" : areas.length === 0 ? "匹配机会" : "再来一批"`;当 `areas.length > 0` 额外渲染 `<Button variant="outline" type="button" onClick={clearAll}>清空看板</Button>`(用现有 `@/components/ui/button` 的 outline 变体)。
- 结果区:`latestWarnings.length > 0` → 顶部琥珀提示条(同现有写法);`areas.length > 0` → grid 渲染卡片(`OpportunityCandidateCard`,保留 `onGenerate={generate}` 与 `isGenerating`);`areas.length === 0` 且已点过(可用「match.isSuccess || latestWarnings.length>0」判断)→ `EmptyState message="未匹配到候选，可能与图谱规模或画像约束有关。"`;`latestRejected.length > 0` → 现有「被排除的方向」区块,数据源改 `latestRejected`。
- `generate(area)`、`useBuildOpportunityFrame`、`router`、`upsertFrame`、`rememberLastFrameId`、错误态(`match.isError` / `buildFrame.isError`)全部保留。

（先读现有 `page.tsx` 与 `match-page.test.tsx`,在其结构上增量改造;不要丢失任何现有 import/行为。若某现有测试因新结构需微调断言写法,在保持其意图的前提下更新。）

- [ ] **Step 4: 运行确认通过 + 全量前端回归**

Run: `npx vitest run "app/(workbench)/match/match-page.test.tsx"`  → PASS（4 适配 + 3 新)
Run: `npm test`  → 全绿（基线 111 + 新增)

- [ ] **Step 5: 提交**

```bash
git add "frontend/app/(workbench)/match/page.tsx" "frontend/app/(workbench)/match/match-page.test.tsx"
git commit -m "feat(match): accumulating discovery board with persistence, re-match and clear"
```
末尾空一行加 trailer:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## 自检结果

**Spec 覆盖:** §3.1 请求体 → Task 2;§3.2 去重+枯竭 → Task 1;§4.1 数据层 → Task 3;§4.2 hook → Task 3;§4.3 看板存储 → Task 4;§4.4 页面 → Task 5;§5 测试分散在各任务。无遗漏。

**占位符扫描:** 后端/数据层/存储为完整代码。Task 2 的 api 测试与 Task 5 的页面改造给出完整新代码 + 明确的「读现有文件增量改」指令(因其需在既有 6.6 集成与既有测试上改),无 TODO/TBD。

**类型/签名一致性:** `match_opportunities(..., seen_ids: Iterable[str]=())`、`_fallback_result(..., extra_warnings=())`、`OpportunityMatchRequest{profile, seen_ids}`、`matchOpportunities(profile, seenIds=[])`、`useMatchOpportunities()` mutate 入参 `{profile, seenIds}`、`OpportunityBoard{areas, seen_ids}`、`loadBoard/saveBoard/clearBoard(profileId)` 在定义与调用处一致。Task 5 onSuccess 合并逻辑使用的字段(`result.areas`/`result.rejected[].candidate_id`/`result.warnings`)与后端 `OpportunityMatchResult` 一致。

**执行顺序:** Task 1→2(后端先服务后 API)、3→4→5(前端数据层→存储→页面);前端 Task 5 依赖 3、4。
