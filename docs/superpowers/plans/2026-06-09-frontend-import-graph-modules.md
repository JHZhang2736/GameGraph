# 前端游戏入库 & 知识图谱模块 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让前端能粘贴/上传 `GameImportDocument` JSON 校验后写入真实后端,并把知识图谱视图接到真实 Neo4j,以「聚焦 + 按需展开」方式在 200+ 游戏规模下流畅探索。

**Architecture:** 后端新增 3 个薄查询接口(`GET /games`、`/graph/search`、`/graph/neighbors`),Cypher + 结果整形放在 `GameRepository`,纯整形逻辑抽到可单测的 `services/graph_query.py`;路由用 `FakeRepository` + `dependency_overrides` 单测,真实 Cypher 用 `@pytest.mark.integration`(默认 deselected)。前端在 `lib/data/` 单点把 fixture 换成真实 `fetch`,新增 zod 入库校验,入库走「输入→校验→预览→提交→结果」,图谱走「随机焦点→邻域→按需展开」。

**Tech Stack:** FastAPI + Neo4j(后端);Next.js App Router + React + TypeScript + TanStack Query + @xyflow/react + zod(前端);pytest / Vitest + RTL(测试)。

> **环境提醒(前端):** 本仓库的 Next.js 与训练数据有出入。写任何 Next.js 代码前,先看 `frontend/node_modules/next/dist/docs/` 里相关指南(App Router、client component、文件约定)。所有前端命令在 `frontend/` 下跑;所有后端命令在 `backend/` 下跑。工作区为 worktree:`D:\Files\GameGraph\.claude\worktrees\import-graph-modules`。

---

## 文件结构

**后端(新增/修改):**
- Create `backend/app/schemas/graph.py` — 图谱查询的响应 schema(`GameSummary`、`GraphNodeDTO`、`GraphEdgeDTO`、`NeighborhoodResult`、`NodeSearchHit`)。
- Create `backend/app/services/graph_query.py` — 纯整形函数 `build_neighborhood(...)`(把 Cypher 行整形为 `NeighborhoodResult`,可单测,不碰 neo4j)。
- Modify `backend/app/graph/game_repository.py` — 新增 `list_games()`、`search_nodes()`、`neighbors()`。
- Create `backend/app/api/routes_graph.py` — `GET /graph/search`、`GET /graph/neighbors`。
- Modify `backend/app/api/routes_import.py` — 新增 `GET /games`(复用 `get_repository`)。
- Modify `backend/app/main.py` — 注册 `routes_graph`。
- Create `backend/tests/test_graph_query.py`、`backend/tests/test_graph_api.py`、`backend/tests/test_games_list_api.py`;Modify `backend/tests/test_game_repository_integration.py`(加邻域/列表/搜索集成用例)。

**前端(新增/修改):**
- Create `frontend/lib/import/schema.ts` — zod 镜像 `GameImportDocument` + 文档级契约校验。
- Modify `frontend/lib/types/index.ts` — 新增 `GameImportDocument`/`ImportGameProfile`/`ReferenceValueTag`/`GameSummary`/`GraphNodeType`/`NeighborhoodResult`/`ImportSummary`/`NodeSearchHit`,并给图谱节点/边加 `node_type` 与可选 `confidence`。
- Modify `frontend/lib/data/index.ts` — 新增 `listGames`/`getNeighbors`/`searchGraphNodes`/`importGame`/`getGameDocument`(真实 `fetch`)。
- Modify `frontend/lib/queries/index.ts` — 新增 `useGames`/`useImportGame`(mutation)/`useGraphSearch`。
- Create `frontend/components/import/json-input.tsx`、`import-preview.tsx`、`import-result.tsx`。
- Create `frontend/app/(workbench)/games/import/page.tsx`;Modify `frontend/app/(workbench)/games/page.tsx`。
- Modify `frontend/components/graph/graph-canvas.tsx`(节点类型着色、可选 confidence、点击节点回调)。
- Modify `frontend/app/(workbench)/graph/page.tsx`(随机焦点、🎲、搜索、按需展开、超限提示)。
- 对应测试文件随任务创建。

---

## Task 1: 后端图谱响应 schema + 纯邻域整形函数

**Files:**
- Create: `backend/app/schemas/graph.py`
- Create: `backend/app/services/graph_query.py`
- Test: `backend/tests/test_graph_query.py`

- [ ] **Step 1: 写 schema**

`backend/app/schemas/graph.py`:

```python
from __future__ import annotations

from app.schemas.common import (
    ConfidenceLevel,
    EvidenceRef,
    QualityStatus,
    StrictBaseModel,
)


class GameSummary(StrictBaseModel):
    id: str
    title: str
    short_description: str
    confidence: ConfidenceLevel
    quality_status: QualityStatus


class GraphNodeDTO(StrictBaseModel):
    id: str
    label: str
    node_type: str


class GraphEdgeDTO(StrictBaseModel):
    id: str
    source: str
    target: str
    relation: str
    confidence: ConfidenceLevel | None = None
    quality_status: QualityStatus | None = None
    claim_id: str | None = None
    evidence: list[EvidenceRef] = []


class NeighborhoodResult(StrictBaseModel):
    focus: GraphNodeDTO
    nodes: list[GraphNodeDTO]
    edges: list[GraphEdgeDTO]
    truncated: bool = False


class NodeSearchHit(StrictBaseModel):
    id: str
    label: str
    node_type: str
```

- [ ] **Step 2: 写 `build_neighborhood` 的失败测试**

`backend/tests/test_graph_query.py`:

```python
from app.services.graph_query import NeighborRow, build_neighborhood


def _focus() -> dict:
    return {"id": "game_hk", "label": "Hollow Knight", "node_type": "Game"}


def test_structural_edge_has_no_confidence_and_uses_rel_type_as_relation():
    rows = [
        NeighborRow(
            rel_type="HAS_MECHANIC",
            rel_props={},
            neighbor_label="Mechanic",
            neighbor_key="precise platforming",
            neighbor_display="precise platforming",
        )
    ]
    result = build_neighborhood(_focus(), rows, limit=150)
    assert result.focus.id == "game_hk"
    assert len(result.nodes) == 1
    assert result.nodes[0].node_type == "Mechanic"
    assert result.nodes[0].id == "precise platforming"
    edge = result.edges[0]
    assert edge.relation == "HAS_MECHANIC"
    assert edge.confidence is None
    assert edge.source == "game_hk"
    assert edge.target == "precise platforming"
    assert result.truncated is False


def test_claim_edge_carries_relation_confidence_and_evidence():
    rows = [
        NeighborRow(
            rel_type="CLAIM",
            rel_props={
                "claim_id": "claim_1",
                "relation": "reinforces",
                "confidence": "low",
                "quality_status": "weak_evidence",
                "evidence_json": '[{"title":"GDC talk","notes":"n","url":"http://x"}]',
            },
            neighbor_label="Concept",
            neighbor_key="exploration flow",
            neighbor_display="exploration flow",
        )
    ]
    edge = build_neighborhood(_focus(), rows, limit=150).edges[0]
    assert edge.relation == "reinforces"
    assert edge.confidence == "low"
    assert edge.quality_status == "weak_evidence"
    assert edge.claim_id == "claim_1"
    assert edge.evidence[0].title == "GDC talk"
    assert edge.id == "claim_1"


def test_truncated_flag_set_when_rows_capped():
    rows = [
        NeighborRow("HAS_MECHANIC", {}, "Mechanic", f"m{i}", f"m{i}")
        for i in range(3)
    ]
    result = build_neighborhood(_focus(), rows, limit=2)
    assert len(result.nodes) == 2
    assert result.truncated is True
```

- [ ] **Step 3: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_graph_query.py -q`
Expected: FAIL（`graph_query` / `NeighborRow` 不存在）

- [ ] **Step 4: 实现 `graph_query.py`**

`backend/app/services/graph_query.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.schemas.common import EvidenceRef
from app.schemas.graph import GraphEdgeDTO, GraphNodeDTO, NeighborhoodResult


@dataclass
class NeighborRow:
    rel_type: str
    rel_props: dict = field(default_factory=dict)
    neighbor_label: str = ""
    neighbor_key: str = ""
    neighbor_display: str = ""


def _evidence(rel_props: dict) -> list[EvidenceRef]:
    raw = rel_props.get("evidence_json")
    if not raw:
        return []
    return [EvidenceRef.model_validate(item) for item in json.loads(raw)]


def _edge(focus_id: str, row: NeighborRow) -> GraphEdgeDTO:
    props = row.rel_props
    claim_id = props.get("claim_id")
    edge_id = claim_id or f"{focus_id}-{row.rel_type}-{row.neighbor_key}"
    return GraphEdgeDTO(
        id=edge_id,
        source=focus_id,
        target=row.neighbor_key,
        relation=props.get("relation") or row.rel_type,
        confidence=props.get("confidence"),
        quality_status=props.get("quality_status"),
        claim_id=claim_id,
        evidence=_evidence(props),
    )


def build_neighborhood(
    focus: dict, rows: list[NeighborRow], limit: int
) -> NeighborhoodResult:
    capped = rows[:limit]
    nodes = [
        GraphNodeDTO(
            id=row.neighbor_key,
            label=row.neighbor_display,
            node_type=row.neighbor_label,
        )
        for row in capped
    ]
    edges = [_edge(focus["id"], row) for row in capped]
    return NeighborhoodResult(
        focus=GraphNodeDTO(**focus),
        nodes=nodes,
        edges=edges,
        truncated=len(rows) > limit,
    )
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_graph_query.py -q`
Expected: PASS（3 passed）

- [ ] **Step 6: 提交**

```bash
git add backend/app/schemas/graph.py backend/app/services/graph_query.py backend/tests/test_graph_query.py
git commit -m "feat(backend): graph query schemas and neighborhood builder"
```

---

## Task 2: `GET /games` 列表接口

**Files:**
- Modify: `backend/app/graph/game_repository.py`
- Modify: `backend/app/api/routes_import.py`
- Test: `backend/tests/test_games_list_api.py`

- [ ] **Step 1: 写路由失败测试**

`backend/tests/test_games_list_api.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes_import import get_repository
from app.schemas.graph import GameSummary


class FakeRepo:
    def list_games(self) -> list[GameSummary]:
        return [
            GameSummary(
                id="game_hk",
                title="Hollow Knight",
                short_description="metroidvania",
                confidence="high",
                quality_status="reviewed",
            )
        ]


@pytest.fixture()
def client() -> TestClient:
    app.dependency_overrides[get_repository] = lambda: FakeRepo()
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def test_list_games_returns_summaries(client: TestClient) -> None:
    response = client.get("/games")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == "game_hk"
    assert body[0]["title"] == "Hollow Knight"
    assert body[0]["confidence"] == "high"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_games_list_api.py -q`
Expected: FAIL（404 / 路由不存在）

- [ ] **Step 3: 实现 repository 方法**

在 `backend/app/graph/game_repository.py` 顶部 import 处加入 `from app.schemas.graph import GameSummary`,并在 `GameRepository` 内新增方法:

```python
    def list_games(self) -> list[GameSummary]:
        with self._driver.session() as session:
            rows = session.execute_read(self._read_games)
        return [GameSummary(**row) for row in rows]

    @staticmethod
    def _read_games(tx) -> list[dict]:
        result = tx.run(
            "MATCH (g:Game) RETURN g.id AS id, g.title AS title, "
            "g.short_description AS short_description, g.confidence AS confidence, "
            "g.quality_status AS quality_status ORDER BY g.title"
        )
        return [dict(record) for record in result]
```

- [ ] **Step 4: 实现路由**

在 `backend/app/api/routes_import.py` import 处加入 `from app.schemas.graph import GameSummary`,并新增:

```python
@router.get("/games", response_model=list[GameSummary])
def list_games(
    repository: GameRepository = Depends(get_repository),
) -> list[GameSummary]:
    return repository.list_games()
```

> 注意:`GET /games` 必须定义在 `GET /games/{game_id}` 之前,避免路由冲突。

- [ ] **Step 5: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_games_list_api.py tests/test_import_api.py -q`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add backend/app/graph/game_repository.py backend/app/api/routes_import.py backend/tests/test_games_list_api.py
git commit -m "feat(backend): GET /games list endpoint"
```

---

## Task 3: `GET /graph/search` 节点搜索接口

**Files:**
- Modify: `backend/app/graph/game_repository.py`
- Create: `backend/app/api/routes_graph.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_graph_api.py`

- [ ] **Step 1: 写路由失败测试**

`backend/tests/test_graph_api.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes_graph import get_repository
from app.schemas.graph import NeighborhoodResult, NodeSearchHit


class FakeGraphRepo:
    def search_nodes(self, q: str, limit: int) -> list[NodeSearchHit]:
        return [NodeSearchHit(id="game_hk", label="Hollow Knight", node_type="Game")]

    def neighbors(self, node_id, hops, limit, rel_types):  # used in Task 4
        return NeighborhoodResult(
            focus={"id": node_id, "label": node_id, "node_type": "Game"},
            nodes=[],
            edges=[],
            truncated=False,
        )


@pytest.fixture()
def client() -> TestClient:
    app.dependency_overrides[get_repository] = lambda: FakeGraphRepo()
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def test_search_returns_hits(client: TestClient) -> None:
    response = client.get("/graph/search", params={"q": "hollow"})
    assert response.status_code == 200
    assert response.json()[0]["node_type"] == "Game"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_graph_api.py -q`
Expected: FAIL（`routes_graph` 不存在）

- [ ] **Step 3: 实现 repository 搜索**

在 `backend/app/graph/game_repository.py` import 处补 `NodeSearchHit`,并新增方法:

```python
    def search_nodes(self, q: str, limit: int = 20) -> list[NodeSearchHit]:
        with self._driver.session() as session:
            rows = session.execute_read(self._search_nodes, q, limit)
        return [NodeSearchHit(**row) for row in rows]

    @staticmethod
    def _search_nodes(tx, q: str, limit: int) -> list[dict]:
        result = tx.run(
            "MATCH (n) WHERE n.title IS NOT NULL OR n.name IS NOT NULL "
            "WITH n, coalesce(n.title, n.name) AS label "
            "WHERE toLower(label) CONTAINS toLower($q) "
            "RETURN coalesce(n.id, n.name) AS id, label, head(labels(n)) AS node_type "
            "LIMIT $limit",
            q=q,
            limit=limit,
        )
        return [dict(record) for record in result]
```

- [ ] **Step 4: 实现 `routes_graph.py`**

`backend/app/api/routes_graph.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.routes_import import get_repository
from app.graph.game_repository import GameRepository
from app.schemas.graph import NodeSearchHit

router = APIRouter()


@router.get("/graph/search", response_model=list[NodeSearchHit])
def search_graph(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    repository: GameRepository = Depends(get_repository),
) -> list[NodeSearchHit]:
    return repository.search_nodes(q, limit)
```

- [ ] **Step 5: 注册路由**

在 `backend/app/main.py` 中:

```python
from app.api.routes_graph import router as graph_router
```

并在 `app.include_router(profile_router)` 之后加:

```python
app.include_router(graph_router)
```

- [ ] **Step 6: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_graph_api.py -q`
Expected: PASS（test_search_returns_hits）

- [ ] **Step 7: 提交**

```bash
git add backend/app/graph/game_repository.py backend/app/api/routes_graph.py backend/app/main.py backend/tests/test_graph_api.py
git commit -m "feat(backend): GET /graph/search node search endpoint"
```

---

## Task 4: `GET /graph/neighbors` 邻域接口 + 集成测试

**Files:**
- Modify: `backend/app/graph/game_repository.py`
- Modify: `backend/app/api/routes_graph.py`
- Modify: `backend/tests/test_graph_api.py`
- Modify: `backend/tests/test_game_repository_integration.py`

- [ ] **Step 1: 写路由失败测试(追加到 `test_graph_api.py`)**

```python
def test_neighbors_returns_bounded_subgraph(client: TestClient) -> None:
    response = client.get("/graph/neighbors", params={"node_id": "game_hk"})
    assert response.status_code == 200
    body = response.json()
    assert body["focus"]["id"] == "game_hk"
    assert body["truncated"] is False


def test_neighbors_parses_rel_types_csv(client: TestClient) -> None:
    response = client.get(
        "/graph/neighbors",
        params={"node_id": "game_hk", "rel_types": "HAS_MECHANIC,CLAIM"},
    )
    assert response.status_code == 200
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_graph_api.py -q`
Expected: FAIL（/graph/neighbors 不存在）

- [ ] **Step 3: 实现 repository `neighbors`**

在 `backend/app/graph/game_repository.py` import 处补 `from app.services.graph_query import NeighborRow, build_neighborhood` 与 `NeighborhoodResult`,并新增方法:

```python
    def neighbors(
        self,
        node_id: str,
        hops: int = 1,
        limit: int = 150,
        rel_types: list[str] | None = None,
    ) -> NeighborhoodResult | None:
        with self._driver.session() as session:
            data = session.execute_read(
                self._read_neighbors, node_id, limit, rel_types
            )
        if data is None:
            return None
        focus, rows = data
        return build_neighborhood(focus, rows, limit)

    @staticmethod
    def _read_neighbors(tx, node_id, limit, rel_types):
        focus_rec = tx.run(
            "MATCH (n) WHERE n.id = $id OR n.name = $id "
            "RETURN coalesce(n.id, n.name) AS id, "
            "coalesce(n.title, n.name) AS label, head(labels(n)) AS node_type "
            "LIMIT 1",
            id=node_id,
        ).single()
        if focus_rec is None:
            return None
        result = tx.run(
            "MATCH (n) WHERE n.id = $id OR n.name = $id "
            "MATCH (n)-[r]->(m) "
            "WHERE $rel_types IS NULL OR type(r) IN $rel_types "
            "RETURN type(r) AS rel_type, properties(r) AS rel_props, "
            "head(labels(m)) AS neighbor_label, "
            "coalesce(m.id, m.name) AS neighbor_key, "
            "coalesce(m.title, m.name) AS neighbor_display "
            "LIMIT $cap",
            id=node_id,
            rel_types=rel_types,
            cap=limit + 1,
        )
        rows = [
            NeighborRow(
                rel_type=rec["rel_type"],
                rel_props=dict(rec["rel_props"]),
                neighbor_label=rec["neighbor_label"],
                neighbor_key=rec["neighbor_key"],
                neighbor_display=rec["neighbor_display"],
            )
            for rec in result
        ]
        return dict(focus_rec), rows
```

> `cap=limit + 1` 让我们能判断是否超限:`build_neighborhood` 在 `len(rows) > limit` 时置 `truncated=True` 并截到 `limit`。

- [ ] **Step 4: 实现路由(追加到 `routes_graph.py`)**

import 处补 `from app.schemas.graph import NeighborhoodResult` 与 `from fastapi import HTTPException`,新增:

```python
@router.get("/graph/neighbors", response_model=NeighborhoodResult)
def graph_neighbors(
    node_id: str = Query(min_length=1),
    hops: int = Query(default=1, ge=1, le=2),
    limit: int = Query(default=150, ge=1, le=500),
    rel_types: str | None = Query(default=None),
    repository: GameRepository = Depends(get_repository),
) -> NeighborhoodResult:
    parsed = [t for t in rel_types.split(",") if t] if rel_types else None
    result = repository.neighbors(node_id, hops, limit, parsed)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    return result
```

- [ ] **Step 5: 跑路由测试确认通过**

Run: `cd backend && python -m pytest tests/test_graph_api.py -q`
Expected: PASS（4 passed）

- [ ] **Step 6: 写真实 Cypher 集成测试(追加到 `test_game_repository_integration.py`)**

在文件末尾追加(沿用现有 `driver` fixture,导入后自动写入 animal_well 再断言):

```python
def test_list_search_and_neighbors_round_trip(driver) -> None:
    repo = GameRepository(driver)
    repo.upsert_game(animal_well_document())

    games = repo.list_games()
    assert any(g.id == "game_animal_well" for g in games)

    hits = repo.search_nodes("animal", limit=10)
    assert any(h.node_type == "Game" for h in hits)

    hood = repo.neighbors("game_animal_well", hops=1, limit=150, rel_types=None)
    assert hood is not None
    assert hood.focus.id == "game_animal_well"
    assert len(hood.nodes) > 0
    assert repo.neighbors("game_missing", 1, 150, None) is None
```

- [ ] **Step 7: 跑完整后端测试(集成默认 deselected)确认无回归**

Run: `cd backend && python -m pytest -q`
Expected: PASS（原 96 + 新增 route/单元用例;集成用例 deselected）

- [ ] **Step 8: 提交**

```bash
git add backend/app/graph/game_repository.py backend/app/api/routes_graph.py backend/tests/test_graph_api.py backend/tests/test_game_repository_integration.py
git commit -m "feat(backend): GET /graph/neighbors bounded neighborhood endpoint"
```

---

## Task 5: 前端 zod 入库校验 schema

**Files:**
- Modify: `frontend/package.json`(加 zod)
- Create: `frontend/lib/import/schema.ts`
- Test: `frontend/lib/import/schema.test.ts`

- [ ] **Step 1: 安装 zod**

Run: `cd frontend && npm install zod`
Expected: `added 1 package`(zod 出现在 dependencies)

- [ ] **Step 2: 写失败测试**

`frontend/lib/import/schema.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { parseImportDocument } from "@/lib/import/schema";

const evidence = { title: "GDC", notes: "n", url: "http://x" };

function validDoc() {
  return {
    candidate: {
      id: "game_hk",
      title: "Hollow Knight",
      source_refs: [evidence],
      short_description: "metroidvania",
      selection_reason: "reference",
    },
    profile: {
      game_id: "game_hk",
      one_sentence_summary: "s",
      core_hook: "h",
      core_loop: "l",
      progression_model: "p",
      failure_model: "f",
      content_structure: "c",
      main_player_actions: ["jump"],
      main_player_decisions: ["route"],
      main_player_experiences: ["tension"],
      main_mechanics: ["platforming"],
      replayability_sources: ["secrets"],
      production_constraints: ["small team"],
      innovation_patterns: ["x"],
      reusable_reference_patterns: ["y"],
      non_replicable_risks: ["z"],
      genre: ["metroidvania"],
      art_style: ["hand-drawn"],
      audio_style: ["orchestral"],
      perspective: ["2d"],
      theme: ["dark"],
      narrative_style: ["environmental"],
      game_feel: ["tight"],
      team_model: ["small"],
      reference_value_tags: [
        { tag: "atmosphere", confidence: "high", quality_status: "reviewed", evidence: [evidence] },
      ],
      evidence: [evidence],
      confidence: "high",
      quality_status: "reviewed",
    },
    claims: [
      {
        id: "claim_1",
        subject: "Hollow Knight",
        relation: "reinforces",
        object: "exploration flow",
        explanation: "e",
        evidence: [evidence],
        confidence: "high",
        quality_status: "reviewed",
      },
    ],
  };
}

describe("parseImportDocument", () => {
  it("accepts a valid document", () => {
    const result = parseImportDocument(validDoc());
    expect(result.ok).toBe(true);
  });

  it("rejects empty main_mechanics with a field path", () => {
    const doc = validDoc();
    doc.profile.main_mechanics = [];
    const result = parseImportDocument(doc);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.some((e) => e.path.includes("main_mechanics"))).toBe(true);
    }
  });

  it("rejects evidence with neither url nor quote_or_summary", () => {
    const doc = validDoc();
    doc.profile.evidence = [{ title: "t", notes: "n" } as never];
    const result = parseImportDocument(doc);
    expect(result.ok).toBe(false);
  });

  it("rejects when profile.game_id does not match candidate.id", () => {
    const doc = validDoc();
    doc.profile.game_id = "game_other";
    const result = parseImportDocument(doc);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.some((e) => e.message.includes("game_id"))).toBe(true);
    }
  });
});
```

- [ ] **Step 3: 跑测试确认失败**

Run: `cd frontend && npx vitest run lib/import/schema.test.ts`
Expected: FAIL（模块不存在）

- [ ] **Step 4: 实现 schema**

`frontend/lib/import/schema.ts`:

```typescript
import { z } from "zod";

const nonEmpty = z.string().trim().min(1);
const nonEmptyList = z.array(nonEmpty).min(1);

const evidenceRef = z
  .object({
    title: nonEmpty,
    url: nonEmpty.optional(),
    quote_or_summary: nonEmpty.optional(),
    notes: nonEmpty,
  })
  .strict()
  .refine((e) => Boolean(e.url) || Boolean(e.quote_or_summary), {
    message: "EvidenceRef requires url or quote_or_summary",
  });

const evidenceList = z.array(evidenceRef).min(1);
const confidence = z.enum(["low", "medium", "high"]);
const quality = z.enum(["draft", "reviewed", "weak_evidence", "conflicting"]);

const referenceValueTag = z
  .object({
    tag: nonEmpty,
    confidence,
    quality_status: quality,
    evidence: z.array(evidenceRef),
  })
  .strict();

const seedGame = z
  .object({
    id: nonEmpty,
    title: nonEmpty,
    source_refs: evidenceList,
    short_description: nonEmpty,
    selection_reason: nonEmpty,
  })
  .strict();

const profile = z
  .object({
    game_id: nonEmpty,
    one_sentence_summary: nonEmpty,
    core_hook: nonEmpty,
    core_loop: nonEmpty,
    progression_model: nonEmpty,
    failure_model: nonEmpty,
    content_structure: nonEmpty,
    main_player_actions: nonEmptyList,
    main_player_decisions: nonEmptyList,
    main_player_experiences: nonEmptyList,
    main_mechanics: nonEmptyList,
    replayability_sources: nonEmptyList,
    production_constraints: nonEmptyList,
    innovation_patterns: nonEmptyList,
    reusable_reference_patterns: nonEmptyList,
    non_replicable_risks: nonEmptyList,
    genre: nonEmptyList,
    art_style: nonEmptyList,
    audio_style: nonEmptyList,
    perspective: nonEmptyList,
    theme: nonEmptyList,
    narrative_style: nonEmptyList,
    game_feel: nonEmptyList,
    team_model: nonEmptyList,
    reference_value_tags: z.array(referenceValueTag).min(1),
    evidence: evidenceList,
    confidence,
    quality_status: quality,
  })
  .strict();

const claim = z
  .object({
    id: nonEmpty,
    subject: nonEmpty,
    relation: nonEmpty,
    object: nonEmpty,
    explanation: nonEmpty,
    evidence: evidenceList,
    confidence,
    quality_status: quality,
  })
  .strict();

export const importDocumentSchema = z
  .object({
    candidate: seedGame,
    profile,
    claims: z.array(claim),
  })
  .strict()
  .refine((doc) => doc.profile.game_id === doc.candidate.id, {
    message: "profile.game_id must match candidate.id",
    path: ["profile", "game_id"],
  });

export type ImportDocument = z.infer<typeof importDocumentSchema>;

export interface FieldError {
  path: string;
  message: string;
}

export type ParseResult =
  | { ok: true; document: ImportDocument }
  | { ok: false; errors: FieldError[] };

export function parseImportDocument(raw: unknown): ParseResult {
  const result = importDocumentSchema.safeParse(raw);
  if (result.success) {
    return { ok: true, document: result.data };
  }
  return {
    ok: false,
    errors: result.error.issues.map((issue) => ({
      path: issue.path.join("."),
      message: issue.message,
    })),
  };
}
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd frontend && npx vitest run lib/import/schema.test.ts`
Expected: PASS（4 passed）

- [ ] **Step 6: 提交**

```bash
git add frontend/package.json frontend/package-lock.json frontend/lib/import/schema.ts frontend/lib/import/schema.test.ts
git commit -m "feat(frontend): zod import-document schema with field-level errors"
```

---

## Task 6: 前端类型扩展(图谱 / 摘要 / 入库结果)

**Files:**
- Modify: `frontend/lib/types/index.ts`

- [ ] **Step 1: 追加类型**

在 `frontend/lib/types/index.ts` 末尾追加(沿用文件中已有的 `ConfidenceLevel`/`QualityStatus`/`EvidenceRef`):

```typescript
// 图谱查询 DTO（镜像后端 app/schemas/graph.py）
export type GraphNodeType =
  | "Game"
  | "Mechanic"
  | "PlayerAction"
  | "PlayerDecision"
  | "Experience"
  | "Concept"
  | "ReferenceTag"
  | "Genre"
  | "ArtStyle"
  | "AudioStyle"
  | "Perspective"
  | "Theme"
  | "NarrativeStyle"
  | "GameFeel"
  | "TeamModel"
  | "ProductionConstraint"
  | "InnovationPattern"
  | "ReferencePattern"
  | "Risk"
  | "ReplayabilitySource";

export interface GameSummary {
  id: string;
  title: string;
  short_description: string;
  confidence: ConfidenceLevel;
  quality_status: QualityStatus;
}

export interface NodeSearchHit {
  id: string;
  label: string;
  node_type: string;
}

export interface ImportSummary {
  game_id: string;
  mechanics_written: number;
  experiences_written: number;
  tags_written: number;
  concepts_written: number;
  claims_written: number;
}
```

> 注:图谱节点/边的 TS 形状定义在 `lib/data/index.ts` 的 `GraphNode`/`GraphEdge`(Task 7 改),与本文件的 `GraphNodeType` 配合使用。

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增报错

- [ ] **Step 3: 提交**

```bash
git add frontend/lib/types/index.ts
git commit -m "feat(frontend): add graph/summary/import-result types"
```

---

## Task 7: 前端数据访问层接入真实后端

**Files:**
- Modify: `frontend/lib/data/index.ts`
- Test: `frontend/lib/data/api.test.ts`

- [ ] **Step 1: 写失败测试(mock global fetch)**

`frontend/lib/data/api.test.ts`:

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";
import {
  listGames,
  getNeighbors,
  searchGraphNodes,
  importGame,
  ImportError,
} from "@/lib/data";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("backend data layer", () => {
  it("listGames maps the summaries", async () => {
    vi.stubGlobal("fetch", mockFetch(200, [{ id: "game_hk", title: "Hollow Knight" }]));
    const games = await listGames();
    expect(games[0].id).toBe("game_hk");
  });

  it("getNeighbors passes node_id and rel_types query", async () => {
    const fetchMock = mockFetch(200, { focus: { id: "game_hk" }, nodes: [], edges: [], truncated: false });
    vi.stubGlobal("fetch", fetchMock);
    await getNeighbors({ nodeId: "game_hk", relTypes: ["HAS_MECHANIC"] });
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain("node_id=game_hk");
    expect(calledUrl).toContain("rel_types=HAS_MECHANIC");
  });

  it("searchGraphNodes returns hits", async () => {
    vi.stubGlobal("fetch", mockFetch(200, [{ id: "game_hk", label: "Hollow Knight", node_type: "Game" }]));
    const hits = await searchGraphNodes("hollow");
    expect(hits[0].node_type).toBe("Game");
  });

  it("importGame throws ImportError with backend detail on 409", async () => {
    vi.stubGlobal("fetch", mockFetch(409, { detail: "profile.game_id must match candidate.id" }));
    await expect(importGame({} as never)).rejects.toBeInstanceOf(ImportError);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run lib/data/api.test.ts`
Expected: FAIL（导出不存在）

- [ ] **Step 3: 实现数据层(追加到 `frontend/lib/data/index.ts`)**

先在文件顶部 import 区补充类型:

```typescript
import type {
  GameSummary,
  ImportSummary,
  NodeSearchHit,
} from "@/lib/types";
import type { ImportDocument } from "@/lib/import/schema";
```

更新 `GraphNode`/`GraphEdge`(把 `confidence`/`quality_status` 改可选、加 `node_type`),并在文件末尾追加 API 函数:

```typescript
// 替换原有 GraphNode / GraphEdge 定义为:
export interface GraphNode {
  id: string;
  label: string;
  node_type: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  confidence?: GoldenFlow["graph_relations"][number]["confidence"];
  quality_status?: GoldenFlow["graph_relations"][number]["quality_status"];
  claim_id?: string;
  evidence: EvidenceRef[];
}

export interface NeighborhoodResult {
  focus: GraphNode;
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncated: boolean;
}

export class ImportError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ImportError";
  }
}

export async function listGames(): Promise<GameSummary[]> {
  const res = await fetch(`${API_BASE}/games`);
  if (!res.ok) throw new Error(`GET /games responded ${res.status}`);
  return (await res.json()) as GameSummary[];
}

export async function getGameDocument(id: string): Promise<ImportDocument> {
  const res = await fetch(`${API_BASE}/games/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(`GET /games/${id} responded ${res.status}`);
  return (await res.json()) as ImportDocument;
}

export interface NeighborsParams {
  nodeId: string;
  hops?: number;
  limit?: number;
  relTypes?: string[];
}

export async function getNeighbors(
  params: NeighborsParams,
): Promise<NeighborhoodResult> {
  const query = new URLSearchParams({ node_id: params.nodeId });
  if (params.hops) query.set("hops", String(params.hops));
  if (params.limit) query.set("limit", String(params.limit));
  if (params.relTypes?.length) query.set("rel_types", params.relTypes.join(","));
  const res = await fetch(`${API_BASE}/graph/neighbors?${query.toString()}`);
  if (!res.ok) throw new Error(`GET /graph/neighbors responded ${res.status}`);
  return (await res.json()) as NeighborhoodResult;
}

export async function searchGraphNodes(q: string): Promise<NodeSearchHit[]> {
  const res = await fetch(`${API_BASE}/graph/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error(`GET /graph/search responded ${res.status}`);
  return (await res.json()) as NodeSearchHit[];
}

export async function importGame(doc: ImportDocument): Promise<ImportSummary> {
  const res = await fetch(`${API_BASE}/import/game`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(doc),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ImportError(
      (body as { detail?: string }).detail ?? `import responded ${res.status}`,
      res.status,
    );
  }
  return (await res.json()) as ImportSummary;
}
```

> `getGraph()`(fixture 派生)保留不动,但 `graph/page.tsx`(Task 13)将改用 `getNeighbors`。`getSeedGames()` 保留,`games/page.tsx`(Task 9)改用 `listGames`。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd frontend && npx vitest run lib/data/api.test.ts`
Expected: PASS（4 passed）

- [ ] **Step 5: 全量类型检查 + 既有 data 测试无回归**

Run: `cd frontend && npx tsc --noEmit && npx vitest run lib/data`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add frontend/lib/data/index.ts frontend/lib/data/api.test.ts
git commit -m "feat(frontend): real backend fetch in data layer (games/graph/import)"
```

---

## Task 8: 前端 query hooks

**Files:**
- Modify: `frontend/lib/queries/index.ts`

- [ ] **Step 1: 追加 hooks**

在 `frontend/lib/queries/index.ts` 中,补充 import:

```typescript
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  getNeighbors,
  importGame,
  listGames,
  searchGraphNodes,
  type NeighborsParams,
} from "@/lib/data";
import type { ImportDocument } from "@/lib/import/schema";
```

并在文件末尾追加:

```typescript
export function useGames() {
  return useQuery({ queryKey: ["games"], queryFn: listGames });
}

export function useNeighbors(params: NeighborsParams | null) {
  return useQuery({
    queryKey: ["neighbors", params],
    queryFn: () => getNeighbors(params as NeighborsParams),
    enabled: params !== null,
  });
}

export function useGraphSearch(q: string) {
  return useQuery({
    queryKey: ["graph-search", q],
    queryFn: () => searchGraphNodes(q),
    enabled: q.trim().length > 0,
  });
}

export function useImportGame() {
  return useMutation({ mutationFn: (doc: ImportDocument) => importGame(doc) });
}
```

> `useQuery` 已在文件中 import;把第一行的 `import { useQuery }` 合并为 `import { useMutation, useQuery }`(勿重复声明)。

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增报错

- [ ] **Step 3: 提交**

```bash
git add frontend/lib/queries/index.ts
git commit -m "feat(frontend): query hooks for games/neighbors/search/import"
```

---

## Task 9: 游戏列表页接真实 `/games`

**Files:**
- Modify: `frontend/app/(workbench)/games/page.tsx`
- Modify: `frontend/app/(workbench)/games/games-page.test.tsx`

- [ ] **Step 1: 改写测试(mock useGames)**

把 `games-page.test.tsx` 整体替换为:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import GamesPage from "@/app/(workbench)/games/page";

vi.mock("@/lib/queries", async (orig) => {
  const actual = await orig<typeof import("@/lib/queries")>();
  return {
    ...actual,
    useGames: () => ({
      data: [
        { id: "game_hk", title: "Hollow Knight", short_description: "metroidvania", confidence: "high", quality_status: "reviewed" },
      ],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    }),
  };
});

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("GamesPage", () => {
  it("lists imported games and shows an import entry", async () => {
    renderWithClient(<GamesPage />);
    await waitFor(() => expect(screen.getByText("Hollow Knight")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /导入游戏/ })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run app/\(workbench\)/games/games-page.test.tsx`
Expected: FAIL（页面仍用 useSeedGames / 无导入入口）

- [ ] **Step 3: 改写页面**

`frontend/app/(workbench)/games/page.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useGames } from "@/lib/queries";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";
import { ConfidenceBadge } from "@/components/artifacts/confidence-badge";
import { QualityBadge } from "@/components/artifacts/quality-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function GamesPage() {
  const { data, isLoading, isError, refetch } = useGames();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <PageHeader title="游戏入库" description="已入库的种子游戏" />
        <Link
          href="/games/import"
          className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:opacity-90"
        >
          导入游戏
        </Link>
      </div>
      {data.length === 0 ? (
        <EmptyState message="种子库暂无游戏,点右上角“导入游戏”开始" />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>标题</TableHead>
              <TableHead>简述</TableHead>
              <TableHead>置信度</TableHead>
              <TableHead>质量</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((game) => (
              <TableRow key={game.id}>
                <TableCell className="font-medium">
                  <Link href={`/games/${game.id}`} className="hover:underline">
                    {game.title}
                  </Link>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {game.short_description}
                </TableCell>
                <TableCell>
                  <ConfidenceBadge level={game.confidence} />
                </TableCell>
                <TableCell>
                  <QualityBadge status={game.quality_status} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd frontend && npx vitest run app/\(workbench\)/games/games-page.test.tsx`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add "frontend/app/(workbench)/games/page.tsx" "frontend/app/(workbench)/games/games-page.test.tsx"
git commit -m "feat(frontend): games list reads real GET /games + import entry"
```

---

## Task 10: 入库页 — JSON 输入与校验

**Files:**
- Create: `frontend/components/import/json-input.tsx`
- Create: `frontend/app/(workbench)/games/import/page.tsx`
- Test: `frontend/app/(workbench)/games/import/import-page.test.tsx`

> 写代码前先看 `frontend/node_modules/next/dist/docs/` 关于 client component 与新建路由段的说明。

- [ ] **Step 1: 写失败测试**

`frontend/app/(workbench)/games/import/import-page.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ImportPage from "@/app/(workbench)/games/import/page";

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ImportPage />
    </QueryClientProvider>,
  );
}

describe("ImportPage validation", () => {
  it("shows a field error for invalid JSON document", async () => {
    renderPage();
    const textarea = screen.getByPlaceholderText(/粘贴/);
    fireEvent.change(textarea, { target: { value: '{"candidate":{}}' } });
    fireEvent.click(screen.getByRole("button", { name: /校验/ }));
    await waitFor(() =>
      expect(screen.getByText(/校验未通过/)).toBeInTheDocument(),
    );
  });

  it("rejects non-JSON text", async () => {
    renderPage();
    const textarea = screen.getByPlaceholderText(/粘贴/);
    fireEvent.change(textarea, { target: { value: "not json" } });
    fireEvent.click(screen.getByRole("button", { name: /校验/ }));
    await waitFor(() => expect(screen.getByText(/无法解析 JSON/)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run app/\(workbench\)/games/import/import-page.test.tsx`
Expected: FAIL（页面不存在）

- [ ] **Step 3: 实现 `json-input.tsx`**

`frontend/components/import/json-input.tsx`:

```tsx
"use client";

import { useState } from "react";
import { parseImportDocument, type FieldError } from "@/lib/import/schema";
import type { ImportDocument } from "@/lib/import/schema";

export function JsonInput({
  onValid,
}: {
  onValid: (doc: ImportDocument) => void;
}) {
  const [text, setText] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldError[]>([]);

  function validate() {
    setParseError(null);
    setFieldErrors([]);
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      setParseError("无法解析 JSON,请检查格式");
      return;
    }
    const result = parseImportDocument(parsed);
    if (result.ok) {
      onValid(result.document);
    } else {
      setFieldErrors(result.errors);
    }
  }

  async function pasteFromClipboard() {
    try {
      setText(await navigator.clipboard.readText());
    } catch {
      setParseError("无法读取剪贴板,请手动粘贴");
    }
  }

  function onFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    file.text().then(setText);
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={pasteFromClipboard}
          className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent"
        >
          从剪贴板粘贴
        </button>
        <label className="cursor-pointer rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
          上传 .json 文件
          <input type="file" accept="application/json,.json" className="hidden" onChange={onFile} />
        </label>
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="粘贴 GameImportDocument JSON…"
        className="h-64 w-full rounded-md border p-3 font-mono text-xs"
      />
      <button
        type="button"
        onClick={validate}
        className="rounded-md bg-primary px-4 py-1.5 text-sm text-primary-foreground hover:opacity-90"
      >
        校验并预览
      </button>
      {parseError ? (
        <p className="rounded-md bg-destructive/10 p-2 text-sm text-destructive">{parseError}</p>
      ) : null}
      {fieldErrors.length > 0 ? (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          <p className="mb-1 font-medium">校验未通过:</p>
          <ul className="list-disc space-y-1 pl-5">
            {fieldErrors.map((e, i) => (
              <li key={i}>
                <code>{e.path || "(根)"}</code> — {e.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 4: 实现 `import/page.tsx`(本任务仅到校验态,预览/提交在 Task 11 接上)**

`frontend/app/(workbench)/games/import/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { JsonInput } from "@/components/import/json-input";
import { PageHeader } from "@/components/shell/view-states";
import type { ImportDocument } from "@/lib/import/schema";

export default function ImportPage() {
  const [doc, setDoc] = useState<ImportDocument | null>(null);

  return (
    <div>
      <PageHeader title="导入游戏" description="粘贴或上传 GameImportDocument,校验后预览并入库" />
      {doc === null ? (
        <JsonInput onValid={setDoc} />
      ) : (
        <p className="text-sm text-muted-foreground">已校验通过:{doc.candidate.title}(预览见下一步)</p>
      )}
    </div>
  );
}
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd frontend && npx vitest run app/\(workbench\)/games/import/import-page.test.tsx`
Expected: PASS（2 passed）

- [ ] **Step 6: 提交**

```bash
git add "frontend/components/import/json-input.tsx" "frontend/app/(workbench)/games/import/page.tsx" "frontend/app/(workbench)/games/import/import-page.test.tsx"
git commit -m "feat(frontend): import page JSON input with local zod validation"
```

---

## Task 11: 入库页 — 结构化预览、提交与结果

**Files:**
- Create: `frontend/components/import/import-preview.tsx`
- Create: `frontend/components/import/import-result.tsx`
- Modify: `frontend/app/(workbench)/games/import/page.tsx`
- Test: `frontend/components/import/import-preview.test.tsx`

- [ ] **Step 1: 写预览组件失败测试**

`frontend/components/import/import-preview.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ImportPreview } from "@/components/import/import-preview";
import type { ImportDocument } from "@/lib/import/schema";

const evidence = { title: "GDC", notes: "n", url: "http://x" };

const doc = {
  candidate: { id: "game_hk", title: "Hollow Knight", source_refs: [evidence], short_description: "mv", selection_reason: "ref" },
  profile: {
    game_id: "game_hk", one_sentence_summary: "s", core_hook: "h", core_loop: "l",
    progression_model: "p", failure_model: "f", content_structure: "c",
    main_player_actions: ["jump"], main_player_decisions: ["route"], main_player_experiences: ["tension"],
    main_mechanics: ["platforming"], replayability_sources: ["x"], production_constraints: ["y"],
    innovation_patterns: ["i"], reusable_reference_patterns: ["r"], non_replicable_risks: ["k"],
    genre: ["mv"], art_style: ["a"], audio_style: ["o"], perspective: ["2d"], theme: ["dark"],
    narrative_style: ["env"], game_feel: ["tight"], team_model: ["small"],
    reference_value_tags: [{ tag: "atmosphere", confidence: "high", quality_status: "reviewed", evidence: [evidence] }],
    evidence: [evidence], confidence: "high", quality_status: "reviewed",
  },
  claims: [
    { id: "c1", subject: "Hollow Knight", relation: "reinforces", object: "flow", explanation: "e", evidence: [evidence], confidence: "low", quality_status: "weak_evidence" },
  ],
} as unknown as ImportDocument;

describe("ImportPreview", () => {
  it("renders title, mechanics and a downgraded claim", () => {
    render(<ImportPreview document={doc} onBack={vi.fn()} onConfirm={vi.fn()} pending={false} />);
    expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
    expect(screen.getByText("platforming")).toBeInTheDocument();
    // 低置信度/弱证据论断带降级标记
    expect(screen.getByText(/reinforces/)).toBeInTheDocument();
    expect(screen.getByText(/weak_evidence/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run components/import/import-preview.test.tsx`
Expected: FAIL（组件不存在）

- [ ] **Step 3: 实现 `import-preview.tsx`**

`frontend/components/import/import-preview.tsx`:

```tsx
"use client";

import type { ImportDocument } from "@/lib/import/schema";
import { ConfidenceBadge } from "@/components/artifacts/confidence-badge";
import { QualityBadge } from "@/components/artifacts/quality-badge";
import { EvidenceList } from "@/components/artifacts/evidence-list";
import { ClaimRow } from "@/components/artifacts/claim-row";

function Chips({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="mb-2">
      <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">{label}</div>
      <div className="flex flex-wrap gap-1">
        {items.map((item) => (
          <span key={item} className="rounded border bg-muted px-2 py-0.5 text-xs">{item}</span>
        ))}
      </div>
    </div>
  );
}

export function ImportPreview({
  document,
  onBack,
  onConfirm,
  pending,
}: {
  document: ImportDocument;
  onBack: () => void;
  onConfirm: () => void;
  pending: boolean;
}) {
  const { candidate, profile, claims } = document;
  return (
    <div className="space-y-4">
      <div className="rounded-lg border p-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">{candidate.title}</h2>
          <ConfidenceBadge level={profile.confidence} />
          <QualityBadge status={profile.quality_status} />
        </div>
        <p className="mt-1 text-sm text-muted-foreground">{profile.one_sentence_summary}</p>
        <p className="mt-1 text-xs text-muted-foreground">核心钩子:{profile.core_hook} · 核心循环:{profile.core_loop}</p>
        <div className="mt-2 text-xs text-muted-foreground">来源({candidate.source_refs.length}):</div>
        <EvidenceList evidence={candidate.source_refs} />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <Chips label="主要机制" items={profile.main_mechanics} />
        <Chips label="主要体验" items={profile.main_player_experiences} />
        <Chips label="主要动作" items={profile.main_player_actions} />
        <Chips label="主要决策" items={profile.main_player_decisions} />
      </div>

      <div>
        <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">参考价值标签</div>
        <div className="space-y-2">
          {profile.reference_value_tags.map((tag) => (
            <div key={tag.tag} className="rounded border p-2">
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium">{tag.tag}</span>
                <ConfidenceBadge level={tag.confidence} />
                <QualityBadge status={tag.quality_status} />
              </div>
              <EvidenceList evidence={tag.evidence} />
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">设计论断</div>
        <div className="space-y-2">
          {claims.map((claim) => (
            <ClaimRow key={claim.id} claim={claim} />
          ))}
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <button type="button" onClick={onBack} className="rounded-md border px-4 py-1.5 text-sm hover:bg-accent">
          返回修改
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={pending}
          className="rounded-md bg-primary px-4 py-1.5 text-sm text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {pending ? "入库中…" : "确认入库"}
        </button>
      </div>
    </div>
  );
}
```

> `ClaimRow` 接受 `DesignClaim`;zod 推断出的 claim 类型字段与之一致(`confidence`/`quality_status` 为字面量联合,兼容)。如 `tsc` 报字面量不兼容,在传入处用 `claim as DesignClaim`。

- [ ] **Step 4: 实现 `import-result.tsx`**

`frontend/components/import/import-result.tsx`:

```tsx
"use client";

import Link from "next/link";
import type { ImportSummary } from "@/lib/types";

export function ImportResult({
  summary,
  onImportAnother,
}: {
  summary: ImportSummary;
  onImportAnother: () => void;
}) {
  return (
    <div className="space-y-3 rounded-lg border p-4">
      <p className="font-medium text-green-700">✓ 入库成功</p>
      <p className="text-sm text-muted-foreground">
        写入:{summary.mechanics_written} 机制 · {summary.experiences_written} 体验 ·{" "}
        {summary.tags_written} 标签 · {summary.concepts_written} 概念 · {summary.claims_written} 论断
      </p>
      <div className="flex gap-2">
        <Link
          href={`/graph?focus=${encodeURIComponent(summary.game_id)}`}
          className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:opacity-90"
        >
          🔍 在图谱中查看
        </Link>
        <Link
          href={`/games/${encodeURIComponent(summary.game_id)}`}
          className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent"
        >
          查看游戏档案
        </Link>
        <button
          type="button"
          onClick={onImportAnother}
          className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent"
        >
          再导入一个
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: 串起入库流程(改写 `import/page.tsx`)**

`frontend/app/(workbench)/games/import/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { JsonInput } from "@/components/import/json-input";
import { ImportPreview } from "@/components/import/import-preview";
import { ImportResult } from "@/components/import/import-result";
import { PageHeader } from "@/components/shell/view-states";
import { useImportGame } from "@/lib/queries";
import type { ImportDocument } from "@/lib/import/schema";

export default function ImportPage() {
  const [doc, setDoc] = useState<ImportDocument | null>(null);
  const mutation = useImportGame();

  function reset() {
    mutation.reset();
    setDoc(null);
  }

  if (mutation.isSuccess) {
    return (
      <div>
        <PageHeader title="导入游戏" description="入库结果" />
        <ImportResult summary={mutation.data} onImportAnother={reset} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="导入游戏" description="粘贴或上传 GameImportDocument,校验后预览并入库" />
      {doc === null ? (
        <JsonInput onValid={setDoc} />
      ) : (
        <div className="space-y-3">
          {mutation.isError ? (
            <p className="rounded-md bg-destructive/10 p-2 text-sm text-destructive">
              入库失败:{(mutation.error as Error).message}
            </p>
          ) : null}
          <ImportPreview
            document={doc}
            onBack={reset}
            onConfirm={() => mutation.mutate(doc)}
            pending={mutation.isPending}
          />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 6: 跑测试 + 类型检查确认通过**

Run: `cd frontend && npx vitest run components/import && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add "frontend/components/import/import-preview.tsx" "frontend/components/import/import-result.tsx" "frontend/components/import/import-preview.test.tsx" "frontend/app/(workbench)/games/import/page.tsx"
git commit -m "feat(frontend): structured import preview, submit and result"
```

---

## Task 12: GraphCanvas 节点类型着色 + 节点点击

**Files:**
- Modify: `frontend/components/graph/graph-canvas.tsx`
- Test: `frontend/components/graph/graph-canvas.test.tsx`

- [ ] **Step 1: 写失败测试**

`frontend/components/graph/graph-canvas.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { nodeColor } from "@/components/graph/graph-canvas";

describe("nodeColor", () => {
  it("colors games and mechanics differently", () => {
    expect(nodeColor("Game")).not.toBe(nodeColor("Mechanic"));
  });
  it("falls back to a non-empty neutral color for unknown types", () => {
    expect(nodeColor("Genre")).toBeTruthy();
    expect(nodeColor("SomethingElse")).toBeTruthy();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run components/graph/graph-canvas.test.tsx`
Expected: FAIL（`nodeColor` 未导出）

- [ ] **Step 3: 改写 `graph-canvas.tsx`**

`frontend/components/graph/graph-canvas.tsx`:

```tsx
"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { GraphData, GraphEdge } from "@/lib/data";

const NODE_COLORS: Record<string, string> = {
  Game: "#4f46e5",
  Mechanic: "#818cf8",
  PlayerAction: "#818cf8",
  PlayerDecision: "#818cf8",
  Experience: "#14b8a6",
  Concept: "#f87171",
  ReferenceTag: "#f59e0b",
};

const DEFAULT_NODE_COLOR = "#94a3b8";

export function nodeColor(nodeType: string): string {
  return NODE_COLORS[nodeType] ?? DEFAULT_NODE_COLOR;
}

function isDowngraded(edge: GraphEdge): boolean {
  return (
    edge.confidence === "low" ||
    edge.quality_status === "weak_evidence" ||
    edge.quality_status === "conflicting"
  );
}

const EDGE_COLOR: Record<string, string> = {
  high: "#16a34a",
  medium: "#71717a",
  low: "#d97706",
};

export function GraphCanvas({
  graph,
  onSelectEdge,
  onSelectNode,
}: {
  graph: GraphData;
  onSelectEdge?: (edgeId: string) => void;
  onSelectNode?: (nodeId: string) => void;
}) {
  const nodes = useMemo<Node[]>(
    () =>
      graph.nodes.map((node, index) => ({
        id: node.id,
        position: {
          x: 250 + Math.cos((index / Math.max(graph.nodes.length, 1)) * 2 * Math.PI) * 220,
          y: 250 + Math.sin((index / Math.max(graph.nodes.length, 1)) * 2 * Math.PI) * 220,
        },
        data: { label: node.label },
        style: {
          fontSize: 12,
          width: 160,
          borderColor: nodeColor(node.node_type),
          borderWidth: 2,
        },
      })),
    [graph.nodes],
  );

  const edges = useMemo<Edge[]>(
    () =>
      graph.edges.map((edge) => {
        const downgraded = isDowngraded(edge);
        const stroke = downgraded
          ? "#d97706"
          : edge.confidence
            ? EDGE_COLOR[edge.confidence]
            : "#94a3b8";
        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.relation,
          animated: downgraded,
          style: { stroke, strokeDasharray: downgraded ? "5 5" : undefined },
        };
      }),
    [graph.edges],
  );

  return (
    <div className="h-[560px] rounded-lg border">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        onEdgeClick={(_, edge) => onSelectEdge?.(edge.id)}
        onNodeClick={(_, node) => onSelectNode?.(node.id)}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
```

> `GraphData` 仍来自 `lib/data`,其 `nodes` 现含 `node_type`、`edges` 的 `confidence` 现可选(Task 7 已改)。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd frontend && npx vitest run components/graph/graph-canvas.test.tsx`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add "frontend/components/graph/graph-canvas.tsx" "frontend/components/graph/graph-canvas.test.tsx"
git commit -m "feat(frontend): node-type coloring and node-click in GraphCanvas"
```

---

## Task 13: 图谱页 — 随机焦点 / 搜索 / 按需展开 / 超限提示

**Files:**
- Modify: `frontend/app/(workbench)/graph/page.tsx`
- Modify: `frontend/app/(workbench)/graph/graph-page.test.tsx`

- [ ] **Step 1: 改写测试(mock useGames + getNeighbors)**

`frontend/app/(workbench)/graph/graph-page.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const neighborsMock = vi.fn();

vi.mock("@/lib/queries", async (orig) => {
  const actual = await orig<typeof import("@/lib/queries")>();
  return {
    ...actual,
    useGames: () => ({
      data: [{ id: "game_hk", title: "Hollow Knight", short_description: "mv", confidence: "high", quality_status: "reviewed" }],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    }),
  };
});

vi.mock("@/lib/data", async (orig) => {
  const actual = await orig<typeof import("@/lib/data")>();
  return { ...actual, getNeighbors: (...args: unknown[]) => neighborsMock(...args) };
});

import GraphPage from "@/app/(workbench)/graph/page";

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><GraphPage /></QueryClientProvider>);
}

beforeEach(() => {
  neighborsMock.mockReset();
  neighborsMock.mockResolvedValue({
    focus: { id: "game_hk", label: "Hollow Knight", node_type: "Game" },
    nodes: [{ id: "platforming", label: "platforming", node_type: "Mechanic" }],
    edges: [{ id: "e1", source: "game_hk", target: "platforming", relation: "HAS_MECHANIC", evidence: [] }],
    truncated: false,
  });
});

describe("GraphPage", () => {
  it("loads a random focus on mount and renders its relation", async () => {
    renderPage();
    await waitFor(() => expect(neighborsMock).toHaveBeenCalled());
    expect((neighborsMock.mock.calls[0][0] as { nodeId: string }).nodeId).toBe("game_hk");
  });

  it("shows a truncation warning when truncated is true", async () => {
    neighborsMock.mockResolvedValue({
      focus: { id: "game_hk", label: "Hollow Knight", node_type: "Game" },
      nodes: [], edges: [], truncated: true,
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/结果过多/)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run app/\(workbench\)/graph/graph-page.test.tsx`
Expected: FAIL（页面仍用 useGraph、无随机焦点/超限提示)

- [ ] **Step 3: 改写 `graph/page.tsx`**

`frontend/app/(workbench)/graph/page.tsx`:

```tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import { useGames } from "@/lib/queries";
import { getNeighbors, type GraphData, type GraphEdge, type GraphNode, type NeighborhoodResult } from "@/lib/data";
import { GraphCanvas } from "@/components/graph/graph-canvas";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/shell/view-states";
import { ConfidenceBadge } from "@/components/artifacts/confidence-badge";
import { QualityBadge } from "@/components/artifacts/quality-badge";
import { EvidenceList } from "@/components/artifacts/evidence-list";

function mergeNeighborhood(prev: GraphData, next: NeighborhoodResult): GraphData {
  const nodeMap = new Map<string, GraphNode>(prev.nodes.map((n) => [n.id, n]));
  nodeMap.set(next.focus.id, next.focus);
  for (const n of next.nodes) nodeMap.set(n.id, n);
  const edgeMap = new Map<string, GraphEdge>(prev.edges.map((e) => [e.id, e]));
  for (const e of next.edges) edgeMap.set(e.id, e);
  return { nodes: [...nodeMap.values()], edges: [...edgeMap.values()] };
}

export default function GraphPage() {
  const { data: games, isLoading: gamesLoading, isError: gamesError, refetch } = useGames();
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [truncated, setTruncated] = useState(false);
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);
  const [loadError, setLoadError] = useState(false);

  async function focusOn(nodeId: string, replace: boolean) {
    setLoadError(false);
    try {
      const result = await getNeighbors({ nodeId });
      setTruncated(result.truncated);
      setGraph((prev) =>
        replace ? mergeNeighborhood({ nodes: [], edges: [] }, result) : mergeNeighborhood(prev, result),
      );
    } catch {
      setLoadError(true);
    }
  }

  // 进入时随机选一个游戏作为焦点（支持 ?focus= 覆盖）
  useEffect(() => {
    if (!games || games.length === 0) return;
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("focus");
    const focusId = requested ?? games[Math.floor(Math.random() * games.length)].id;
    void focusOn(focusId, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [games]);

  function reroll() {
    if (!games || games.length === 0) return;
    void focusOn(games[Math.floor(Math.random() * games.length)].id, true);
  }

  const selected = useMemo(
    () => graph.edges.find((e) => e.id === selectedEdge) ?? null,
    [graph.edges, selectedEdge],
  );

  if (gamesLoading) return <LoadingState />;
  if (gamesError) return <ErrorState onRetry={() => refetch()} />;
  if (!games || games.length === 0) return <EmptyState message="暂无已入库游戏,先去导入" />;

  return (
    <div>
      <PageHeader title="知识图谱" description="聚焦 + 按需展开;低置信度关系以琥珀色虚线降级展示。" />
      <div className="mb-3 flex items-center gap-2">
        <button type="button" onClick={reroll} className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
          🎲 换一个
        </button>
        <span className="text-sm text-muted-foreground">焦点节点已加载,点节点可展开邻居。</span>
      </div>
      {truncated ? (
        <p className="mb-2 rounded-md bg-amber-50 p-2 text-sm text-amber-700">
          结果过多,已截断;请缩小范围或加筛选。
        </p>
      ) : null}
      {loadError ? (
        <p className="mb-2 rounded-md bg-destructive/10 p-2 text-sm text-destructive">加载邻域失败,请重试。</p>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <GraphCanvas
          graph={graph}
          onSelectEdge={setSelectedEdge}
          onSelectNode={(id) => focusOn(id, false)}
        />
        <aside className="space-y-3">
          {selected ? (
            <div className="rounded-lg border p-3">
              <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">证据路径</h2>
              <div className="mb-1 text-sm font-medium">
                {selected.source} · {selected.relation} · {selected.target}
              </div>
              <div className="mb-2 flex items-center gap-2">
                {selected.confidence ? <ConfidenceBadge level={selected.confidence} /> : null}
                {selected.quality_status ? <QualityBadge status={selected.quality_status} /> : null}
              </div>
              {selected.claim_id ? (
                <div className="mb-2 text-xs text-muted-foreground">来源论断:{selected.claim_id}</div>
              ) : null}
              <EvidenceList evidence={selected.evidence} />
            </div>
          ) : (
            <p className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
              点击一条关系查看证据路径;点击节点展开其邻居。
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}
```

> 搜索框可作为增强后续加入;本任务先实现「随机焦点 + 🎲 + 点击展开 + 超限提示 + 证据路径」,满足 spec §8.1/§8.2/§8.3 核心。若要带搜索,见下一步可选增强。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd frontend && npx vitest run app/\(workbench\)/graph/graph-page.test.tsx`
Expected: PASS（2 passed）

- [ ] **Step 5: 全量前端测试 + 类型检查**

Run: `cd frontend && npx tsc --noEmit && npm test`
Expected: 全绿(原 47 + 新增)

- [ ] **Step 6: 提交**

```bash
git add "frontend/app/(workbench)/graph/page.tsx" "frontend/app/(workbench)/graph/graph-page.test.tsx"
git commit -m "feat(frontend): graph explorer with random focus, expand-on-click, truncation guard"
```

---

## Task 14: 端到端联调与收尾

**Files:**
- 无新增;手动验证 + 文档更新

- [ ] **Step 1: 后端全量测试**

Run: `cd backend && python -m pytest -q`
Expected: 全绿(集成 deselected)

- [ ] **Step 2: 前端全量测试 + 构建**

Run: `cd frontend && npm test && npm run build`
Expected: 测试全绿;`next build` 成功

- [ ] **Step 3: 真实联调(需本机 Neo4j)**

启动后端(设 `NEO4J_PASSWORD`)与前端 dev server,手动走一遍:导入 `backend/app/fixtures/games/hollow_knight.json` → 看 ImportSummary → 「在图谱中查看」→ 图谱以该游戏为焦点 → 点机制节点展开 → 🎲 换焦点。
> 此步为人工验证,若环境不具备可记录为待办,不阻塞合并。

- [ ] **Step 4: 提交收尾(若有微调)**

```bash
git add -A
git commit -m "chore: end-to-end wiring for import & graph modules"
```

---

## Self-Review 记录

- **Spec 覆盖**:§4 三接口 → Task 2/3/4;§5 zod → Task 5;§5.2/§6 类型+数据层 → Task 6/7/8;§7 入库三步 → Task 9/10/11;§8 图谱探索 → Task 12/13;§10 测试 → 各任务内嵌 + Task 14。搜索接口(§4.3)后端已建(Task 3),前端 `useGraphSearch`/`searchGraphNodes` 已就绪(Task 7/8),图谱页搜索框作为可选增强(Task 13 备注);其余 §8 核心(随机焦点/展开/超限)已覆盖。
- **占位符**:无 TBD/TODO;每个代码步骤含完整代码。两处测试笔误已在备注中明确修正写法。
- **类型一致**:`NeighborRow`/`build_neighborhood`/`NeighborhoodResult`/`GraphNodeDTO`/`GraphEdgeDTO` 跨后端任务一致;前端 `GraphData`/`GraphNode`/`GraphEdge`/`NeighborhoodResult`/`ImportDocument`/`ImportSummary` 跨任务一致;`getNeighbors` 入参 `{ nodeId, relTypes }` 在 data 层、hook、图谱页一致。
