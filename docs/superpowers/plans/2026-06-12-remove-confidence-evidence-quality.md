# 移除 confidence / evidence / quality_status 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从前后端契约、服务、图谱存储、约 200 个 fixture、测试与导入文档中彻底移除 `confidence` / `evidence`(`EvidenceRef`/`source_refs`) / `quality_status` 三层「信任/质量」元数据，只保留实质内容。

**Architecture:** 前后端是 `extra="forbid"` 的镜像契约，字段删一边另一边必须同步，否则校验失败。因此按「后端整层 → 前端整层 → 文档」三个原子提交推进，每个提交内部把 schema/服务/数据/测试一起改到自洽、测试全绿。保留 `OpportunityEvidence`、`OpportunityFrame.evidence_path`（图谱结构/推理路径，与「信任 LLM」无关）。

**Tech Stack:** 后端 Python + Pydantic v2 + Neo4j；前端 TypeScript + Zod + Next.js + Vitest。后端测试 `cd backend; pytest`；前端测试 `vitest --pool=threads`。

参考 spec：`docs/superpowers/specs/2026-06-12-remove-confidence-evidence-quality-design.zh-CN.md`

---

## 重要约定（每个任务都适用）

- **后端测试目录**：worktree 内必须 `cd backend/` 再跑 `pytest`，否则会 import 到主仓库旧 editable `app`。
- **前端测试**：必须 `vitest --pool=threads`（本机 forks pool teardown 会崩）；跑前确保 worktree 已 junction 链接主仓库 `node_modules`。
- Task 1（后端）由于契约耦合是一个**原子提交**：schema/服务/fixture/后端测试一起改到 `pytest` 全绿才提交。Task 2（前端）同理。

---

## Task 1: 后端整层移除（schema + 服务 + fixture + 后端测试）

**Files:**
- Modify: `backend/app/schemas/common.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/schemas/artifacts.py`
- Modify: `backend/app/schemas/graph.py`
- Modify: `backend/app/schemas/developer_profile.py:21-25`
- Modify: `backend/app/services/developer_profile_parser.py`
- Modify: `backend/app/services/profile_llm.py:28-33`
- Modify: `backend/app/services/import_service.py`
- Modify: `backend/app/services/graph_query.py`
- Modify: `backend/app/services/fixture_pipeline.py:201-214`
- Data: `backend/app/fixtures/games/*.json`（约 200 个）+ `backend/app/fixtures/golden_flow.json`
- Test: `backend/tests/*`（更新引用点）
- Throwaway script: `backend/strip_fixtures.py`（跑完删除）

- [ ] **Step 1: 改 `common.py` — 删三个类型**

把 `backend/app/schemas/common.py` 改为（删 `ConfidenceLevel`、`QualityStatus`、`EvidenceRef`，保留其余）：

```python
from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


NonEmptyStr = Annotated[str, Field(min_length=1)]


class StrictBaseModel(BaseModel):
    """Base model shared by contract schemas."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class ConstraintType(StrEnum):
    HARD = "hard"
    STRONG_PREFERENCE = "strong_preference"
    SOFT_PREFERENCE = "soft_preference"
```

注意：`model_validator`、`Self`、`Annotated` 中已不再需要的 import 一并清掉（如上所示，仅保留 `Annotated`、`Field`、`BaseModel`、`ConfigDict`、`StrEnum`）。

- [ ] **Step 2: 改 `schemas/__init__.py` — 删 export**

删掉 `ConfidenceLevel`、`EvidenceRef`、`QualityStatus` 三处 import 与 `__all__` 条目。改后 `from app.schemas.common import (...)` 只保留 `ConstraintType, NonEmptyStr, StrictBaseModel`，`__all__` 移除这三个名字。

- [ ] **Step 3: 改 `artifacts.py`**

- 顶部 import 改为：`from app.schemas.common import ConstraintType, NonEmptyStr, StrictBaseModel`
- `SeedGame`：删 `source_refs` 行。
- `DesignClaim`：删 `evidence`、`confidence`、`quality_status` 三行。
- `GraphRelation`：删 `evidence`、`confidence`、`quality_status` 三行。
- 删整个 `ReferenceValueTag` 类。
- `GameDesignProfile`：`reference_value_tags` 改为 `list[NonEmptyStr] = Field(min_length=1)`；删 `evidence`、`confidence`、`quality_status` 三行。

改后 `DesignClaim` / `GraphRelation` / `SeedGame` 示例：

```python
class SeedGame(StrictBaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    short_description: str = Field(min_length=1)
    selection_reason: str = Field(min_length=1)


class DesignClaim(StrictBaseModel):
    id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    object: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class GraphRelation(StrictBaseModel):
    id: str = Field(min_length=1)
    source_node: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    target_node: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
```

`GameDesignProfile` 中改动的一行：

```python
    reference_value_tags: list[NonEmptyStr] = Field(min_length=1)
    # （删除其后的 evidence / confidence / quality_status 三行）
```

- [ ] **Step 4: 改 `graph.py`**

```python
from __future__ import annotations

from app.schemas.common import StrictBaseModel


class GameSummary(StrictBaseModel):
    id: str
    title: str
    short_description: str


class GraphNodeDTO(StrictBaseModel):
    id: str
    label: str
    node_type: str


class GraphEdgeDTO(StrictBaseModel):
    id: str
    source: str
    target: str
    relation: str
    claim_id: str | None = None


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

- [ ] **Step 5: 改 `developer_profile.py`**

`ProfileFieldSource` 删 `confidence` 行，并去掉 `ConfidenceLevel` import：

```python
from app.schemas.common import NonEmptyStr, StrictBaseModel
```

```python
class ProfileFieldSource(StrictBaseModel):
    field: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
    source_kind: SourceKind
```

- [ ] **Step 6: 改 `developer_profile_parser.py`**

- 顶部 import 改为：`from app.schemas.common import ConstraintType`（删 `ConfidenceLevel`）。
- `_source` 去掉 `confidence` 参数：

```python
def _source(
    field: str,
    source_text: str,
    source_kind: SourceKind = "raw_text",
) -> ProfileFieldSource:
    return ProfileFieldSource(
        field=field,
        source_text=source_text,
        source_kind=source_kind,
    )
```

- `_time_budget` 中 `_source("time_budget", raw_text, ConfidenceLevel.MEDIUM)` 改为 `_source("time_budget", raw_text)`。
- `parse_developer_profile_input` 中 audio 默认分支 `_source("audio_ability", "defaulted to basic", ConfidenceLevel.LOW)` 改为 `_source("audio_ability", "defaulted to basic")`。

- [ ] **Step 7: 改 `profile_llm.py`**

- 顶部 import 改为：`from app.schemas.common import ConstraintType, StrictBaseModel`（删 `ConfidenceLevel`）。
- `ExtractedSource` 删 `confidence` 行：

```python
class ExtractedSource(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")

    field: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
```

- `SYSTEM_PROMPT` 中「每个抽取出的关键字段都尽量给出原文片段作为来源。」一句保留无碍（仍指 source_text），无需改。

- [ ] **Step 8: 改 `import_service.py`**

- 删 `from pydantic import TypeAdapter` 与 `from app.schemas.common import EvidenceRef, StrictBaseModel` 中的 `EvidenceRef`（改为 `from app.schemas.common import StrictBaseModel`）。
- 删 `_EVIDENCE_LIST_ADAPTER` 与 `_evidence_json` 两处定义。
- `_game_node` 的 `properties` 删 `confidence`、`quality_status`、`source_refs_json`、`evidence_json` 四行。
- `_tag_edges`：`to_key={"name": tag.tag}` 改为 `to_key={"name": tag}`（tag 现在是字符串），`properties` 改为 `{}`。
- `_claim_edges` 的 `properties` 删 `evidence_json`、`confidence`、`quality_status` 三行。

改后三处：

```python
def _game_node(document: GameImportDocument) -> NodeMerge:
    candidate = document.candidate
    profile = document.profile
    properties = {
        "title": candidate.title,
        "short_description": candidate.short_description,
        "selection_reason": candidate.selection_reason,
        "one_sentence_summary": profile.one_sentence_summary,
        "core_hook": profile.core_hook,
        "core_loop": profile.core_loop,
        "progression_model": profile.progression_model,
        "failure_model": profile.failure_model,
        "content_structure": profile.content_structure,
        "document_json": document.model_dump_json(),
    }
    return NodeMerge(label="Game", key={"id": candidate.id}, properties=properties)
```

```python
def _tag_edges(document: GameImportDocument) -> list[EdgeMerge]:
    game_key = {"id": document.candidate.id}
    edges: list[EdgeMerge] = []
    for tag in document.profile.reference_value_tags:
        edges.append(
            EdgeMerge(
                rel_type="TAGGED",
                from_label="Game",
                from_key=game_key,
                to_label="ReferenceTag",
                to_key={"name": tag},
                properties={},
            )
        )
    return edges
```

```python
def _claim_edges(document: GameImportDocument) -> list[EdgeMerge]:
    game_key = {"id": document.candidate.id}
    edges: list[EdgeMerge] = []
    for claim in document.claims:
        edges.append(
            EdgeMerge(
                rel_type="CLAIM",
                from_label="Game",
                from_key=game_key,
                to_label="Concept",
                to_key={"name": claim.object},
                properties={
                    "claim_id": claim.id,
                    "relation": claim.relation,
                    "explanation": claim.explanation,
                },
            )
        )
    return edges
```

- [ ] **Step 9: 改 `graph_query.py`**

- 删 `import json`、`from app.schemas.common import EvidenceRef`。
- 删 `_evidence` 函数。
- `_edge` 去掉 `confidence` / `quality_status` / `evidence` 三个入参：

```python
from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.graph import GraphEdgeDTO, GraphNodeDTO, NeighborhoodResult


@dataclass
class NeighborRow:
    rel_type: str
    rel_props: dict = field(default_factory=dict)
    neighbor_label: str = ""
    neighbor_key: str = ""
    neighbor_display: str = ""
    source_key: str = ""
    target_key: str = ""


def _edge(row: NeighborRow) -> GraphEdgeDTO:
    props = row.rel_props
    claim_id = props.get("claim_id")
    edge_id = claim_id or f"{row.source_key}-{row.rel_type}-{row.target_key}"
    return GraphEdgeDTO(
        id=edge_id,
        source=row.source_key,
        target=row.target_key,
        relation=props.get("relation") or row.rel_type,
        claim_id=claim_id,
    )
```

（`build_neighborhood` 不变。）

- [ ] **Step 10: 改 `game_repository.py`**

读取 Game 列表的 Cypher（约 49-51 行）去掉 `g.confidence` / `g.quality_status`：

```python
        result = tx.run(
            "MATCH (g:Game) RETURN g.id AS id, g.title AS title, "
            "g.short_description AS short_description ORDER BY g.title"
        )
```

若该文件还有写入 `confidence`/`quality_status`/`evidence_json` 到节点或边的 Cypher（搜索 `confidence`、`evidence` 确认），一并去掉对应 SET/属性。

- [ ] **Step 11: 改 `fixture_pipeline.py`**

`build_graph_relations_from_claims` 去掉 `evidence`/`confidence`/`quality_status` 三个传参：

```python
def build_graph_relations_from_claims(claims: list[DesignClaim]) -> list[GraphRelation]:
    return [
        GraphRelation(
            id=f"rel_{claim.id}",
            source_node=claim.subject,
            relation=claim.relation,
            target_node=claim.object,
            claim_id=claim.id,
        )
        for claim in claims
    ]
```

（`validate_opportunity_frame` 里的 `evidence_path` / `evidence_ids` 是按 claim/relation **id** 校验推理路径，**保留不动**。）

- [ ] **Step 12: 写并运行 fixture 批处理脚本**

创建 `backend/strip_fixtures.py`：

```python
import json
import pathlib

GAMES_DIR = pathlib.Path("app/fixtures/games")
GOLDEN = pathlib.Path("app/fixtures/golden_flow.json")


def strip_claim(claim: dict) -> dict:
    for key in ("evidence", "confidence", "quality_status"):
        claim.pop(key, None)
    return claim


def strip_game_fixture(doc: dict) -> dict:
    doc.get("candidate", {}).pop("source_refs", None)
    profile = doc.get("profile", {})
    for key in ("evidence", "confidence", "quality_status"):
        profile.pop(key, None)
    tags = profile.get("reference_value_tags")
    if isinstance(tags, list):
        profile["reference_value_tags"] = [
            t["tag"] if isinstance(t, dict) else t for t in tags
        ]
    for claim in doc.get("claims", []):
        strip_claim(claim)
    return doc


def strip_golden_flow(doc: dict) -> dict:
    for seed_game in doc.get("seed_games", []):
        seed_game.pop("source_refs", None)
    for claim in doc.get("design_claims", []):
        strip_claim(claim)
    return doc


def write(path: pathlib.Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    count = 0
    for path in sorted(GAMES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        write(path, strip_game_fixture(data))
        count += 1
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    write(GOLDEN, strip_golden_flow(golden))
    print(f"stripped {count} game fixtures + golden_flow.json")


if __name__ == "__main__":
    main()
```

Run（在 `backend/` 目录）：

```bash
cd backend
python strip_fixtures.py
```

Expected: `stripped <N> game fixtures + golden_flow.json`（N≈200）。

跑完后删除脚本：

```bash
rm backend/strip_fixtures.py
```

- [ ] **Step 13: 更新后端测试**

`cd backend; pytest` 会暴露所有引用已删字段的测试。逐个失败修复——删除测试里对 `confidence` / `quality_status` / `evidence` / `source_refs` 的构造与断言；`reference_value_tags` 断言从 `[{"tag": ...}]` 改为字符串。已知需要改的测试文件（来自 grep）：

- `backend/tests/test_artifact_contracts.py`（构造 DesignClaim/GraphRelation/ReferenceValueTag/GameDesignProfile/SeedGame 的 kwargs 去掉删除字段；删除 ReferenceValueTag 专项断言或改为字符串标签；删除针对 ConfidenceLevel/QualityStatus/EvidenceRef 的用例）
- `backend/tests/test_developer_profile_contracts.py`（ProfileFieldSource 去掉 confidence）
- `backend/tests/test_developer_profile_parser.py`（断言 field_sources 不再有 confidence）
- `backend/tests/test_profile_parse_service.py`、`backend/tests/test_profile_llm.py`、`backend/tests/test_profile_api.py`（ExtractedSource/ProfileFieldSource 去 confidence）
- `backend/tests/test_import_service.py`、`backend/tests/test_game_import_document.py`（节点/边属性断言去掉 confidence/quality_status/source_refs_json/evidence_json；tag 断言用字符串；构造的 import 文档去掉这些字段）
- `backend/tests/test_graph_query.py`（GraphEdgeDTO 去 confidence/quality_status/evidence）
- `backend/tests/test_games_list_api.py`（GameSummary 去 confidence/quality_status）
- `backend/tests/test_fixture_pipeline.py`（golden_flow 相关断言去掉删除字段）

修复模式示例（构造 kwargs 去字段）：

```python
# 改前
DesignClaim(id="c1", subject="a", relation="creates", object="b",
            explanation="x", evidence=[ref], confidence="high", quality_status="draft")
# 改后
DesignClaim(id="c1", subject="a", relation="creates", object="b", explanation="x")
```

- [ ] **Step 14: 跑后端测试到全绿**

Run:

```bash
cd backend
pytest
```

Expected: PASS，0 失败。若有红，回到 Step 13 继续修，直到全绿。

- [ ] **Step 15: 提交**

```bash
git add backend/
git commit -m "refactor(backend): remove confidence/evidence/quality_status from contracts, services, fixtures"
```

确认 `git status` 中 `backend/strip_fixtures.py` 不存在（已删）。

---

## Task 2: 前端整层移除（types + 组件 + 页面 + fixture + 前端测试）

**Files:**
- Modify: `frontend/lib/types/index.ts`
- Delete: `frontend/components/artifacts/confidence-badge.tsx`
- Delete: `frontend/components/artifacts/quality-badge.tsx`
- Delete: `frontend/components/artifacts/evidence-list.tsx`
- Modify: `frontend/components/artifacts/claim-row.tsx`
- Modify: `frontend/components/graph/edge-style.ts` + `edge-style.test.ts`
- Modify: `frontend/lib/data/index.ts`
- Modify: `frontend/lib/import/schema.ts`
- Modify: `frontend/components/import/import-preview.tsx`
- Modify: `frontend/lib/fixtures/golden-flow.ts`
- Modify: `frontend/lib/profile/parser.ts`
- Modify: `frontend/app/(workbench)/games/page.tsx`、`games/[id]/page.tsx`、`graph/page.tsx`
- Test: `frontend/**/*.test.ts(x)`（更新引用点）

- [ ] **Step 1: 改 `lib/types/index.ts`**

- 删 `CONFIDENCE_LEVELS` / `ConfidenceLevel`、`QUALITY_STATUSES` / `QualityStatus`、`EvidenceRef` 接口。
- `SeedGame` 删 `source_refs`。
- `DesignClaim`、`GraphRelation` 删 `evidence`、`confidence`、`quality_status`。
- `ProfileFieldSource` 删 `confidence`。
- `GameDesignProfile` 删 `evidence`、`confidence`、`quality_status`（`reference_value_tags: string[]` 保留）。
- `GameSummary` 删 `confidence`、`quality_status`。
- `ConceptEvaluation` 删 `evidence_quality_score`。

- [ ] **Step 2: 删除三个组件文件**

```bash
git rm frontend/components/artifacts/confidence-badge.tsx \
       frontend/components/artifacts/quality-badge.tsx \
       frontend/components/artifacts/evidence-list.tsx
```

- [ ] **Step 3: 改 `claim-row.tsx`**

```tsx
import type { DesignClaim } from "@/lib/types";

export function ClaimRow({ claim }: { claim: DesignClaim }) {
  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="font-medium">
          {claim.subject} · {claim.relation} · {claim.object}
        </span>
      </div>
      <p className="text-sm text-muted-foreground">{claim.explanation}</p>
    </div>
  );
}
```

- [ ] **Step 4: 改 `edge-style.ts`**

```ts
import type { GraphEdge } from "@/lib/data";

const DEFAULT_EDGE_COLOR = "#94a3b8";

export function edgeColor(_edge: GraphEdge): string {
  return DEFAULT_EDGE_COLOR;
}

export function edgeSize(_edge: GraphEdge): number {
  return 2;
}
```

`edge-style.test.ts`：删除针对 `isDowngraded`、低置信度/弱证据降级颜色与线宽的用例，保留/调整为「边返回默认色与固定线宽」。

- [ ] **Step 5: 改 `lib/data/index.ts`**

在 `GraphEdge` 类型（及任何从后端 DTO 映射边的代码）里删除 `confidence`、`quality_status`、`evidence` 字段与映射。搜索该文件中 `confidence`/`quality_status`/`evidence` 全部清除。

- [ ] **Step 6: 改 `lib/import/schema.ts`**

```ts
import { z } from "zod";

const nonEmpty = z.string().trim().min(1);
const nonEmptyList = z.array(nonEmpty).min(1);

const seedGame = z
  .object({
    id: nonEmpty,
    title: nonEmpty,
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
    reference_value_tags: nonEmptyList,
  })
  .strict();

const claim = z
  .object({
    id: nonEmpty,
    subject: nonEmpty,
    relation: nonEmpty,
    object: nonEmpty,
    explanation: nonEmpty,
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

- [ ] **Step 7: 改 `import-preview.tsx`**

删除展示 `source_refs` / `evidence` / `confidence` / `quality_status` / `reference_value_tags` 子字段的 JSX；`reference_value_tags` 改为直接渲染字符串列表。搜索该文件中上述字段全部清除/调整。

- [ ] **Step 8: 改 `lib/fixtures/golden-flow.ts`**

该文件是 TS 字面量。删除每个 `seed_games[*].source_refs`、`design_claims[*]` 与 `graph_relations[*]` 的 `evidence`/`confidence`/`quality_status`、`game_design_profiles[*]` 的 `evidence`/`confidence`/`quality_status`，并把 `reference_value_tags` 保持/改为字符串数组。改到与新 `lib/types` 接口一致、TS 编译通过。

- [ ] **Step 9: 改 `lib/profile/parser.ts`**

删除 `ProfileFieldSource` 的 `confidence` 相关构造/类型引用。搜索 `confidence` 清除。

- [ ] **Step 10: 改三个页面**

`app/(workbench)/games/page.tsx`、`games/[id]/page.tsx`、`graph/page.tsx`：删除对 `<ConfidenceBadge>` / `<QualityBadge>` / `<EvidenceList>` 的 import 与使用，以及对 `confidence` / `quality_status` / `evidence` / `source_refs` 字段的读取与渲染。搜索这些标识符逐一清除。

- [ ] **Step 11: 更新前端测试**

`vitest --pool=threads` 会暴露引用点。需改的测试（来自 grep）：`frontend/lib/types/types.test.ts`、`frontend/components/artifacts/artifacts.test.tsx`、`frontend/components/graph/edge-style.test.ts`、`frontend/components/import/import-preview.test.tsx`、`frontend/lib/import/schema.test.ts`、`frontend/app/(workbench)/games/games-page.test.tsx`、`frontend/app/(workbench)/graph/graph-page.test.tsx`、`frontend/lib/fixtures/golden-flow.ts` 的消费方测试。删除/调整对已删字段、已删组件（ConfidenceBadge/QualityBadge/EvidenceList）的断言与渲染；fixture 构造去掉删除字段。

- [ ] **Step 12: 跑前端测试到全绿**

Run:

```bash
cd frontend
npx vitest run --pool=threads
```

Expected: PASS，0 失败。红则回 Step 11 继续修。

- [ ] **Step 13: 提交**

```bash
git add frontend/
git commit -m "refactor(frontend): remove confidence/evidence/quality_status from types, components, fixtures"
```

---

## Task 3: 更新导入 skill 与文档

**Files:**
- Modify: `.claude/skills/researching-games-for-import/SKILL.md`
- Modify: `.claude/skills/researching-games-for-import/preferred-terms.md`
- Modify: `docs/superpowers/import-guide/game-import-prompt.md`

- [ ] **Step 1: 改 import skill / prompt**

在以上三个文件中，删除指示 LLM 产出 `confidence` / `evidence` / `quality_status` / `source_refs` 的段落与字段说明；更新内嵌的示例 JSON / schema，使其与新 `GameImportDocument` 契约一致（candidate 无 source_refs；profile 无 evidence/confidence/quality_status、`reference_value_tags` 为字符串数组；claims 项无 evidence/confidence/quality_status）。逐文件搜索这四个字段名清除/改写。

- [ ] **Step 2: 提交**

```bash
git add .claude/skills/researching-games-for-import/ docs/superpowers/import-guide/
git commit -m "docs(import): drop confidence/evidence/quality_status from import skill and prompt"
```

---

## 收尾

- [ ] 全量复跑：`cd backend; pytest` 全绿 + `cd frontend; npx vitest run --pool=threads` 全绿。
- [ ] `git status` 干净（无 `strip_fixtures.py` 残留、无未跟踪文件）。
- [ ] 通过 `superpowers:finishing-a-development-branch` 决定合并/PR。开 PR 前先确认 main 已同步 origin（项目约定：并发开发，开 PR 前核对 main 进度）。

## 自检备注

- **spec 覆盖**：confidence/evidence/quality_status 三类型删除（T1S1-S4）、ProfileFieldSource.confidence（T1S5-S7、T2S1/S9）、ConceptEvaluation.evidence_quality_score（T2S1）、reference_value_tags 拍扁（T1S3/S8/S12、T2S1/S6/S8）、fixture 批处理（T1S12）、保留 OpportunityEvidence/evidence_path（T1S11 备注）、文档/skill（T3）、验证口径（收尾）——均有对应任务。
- **保留项**：`opportunity.py`、`concept_llm.py`、`opportunity_llm.py` 不在改动文件列表，符合「保留结构性 evidence」决策。
