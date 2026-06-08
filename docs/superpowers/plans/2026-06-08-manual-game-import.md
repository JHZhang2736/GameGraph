# 手动游戏导入（6.1/6.2）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让人工挑选的游戏经 Claude 生成的单游戏 JSON，通过 FastAPI 端点校验后写入 Neo4j，成为可遍历的设计知识图谱。

**Architecture:** 在现有 `backend/` 上扩展。新增完整 `GameDesignProfile` 与 `GameImportDocument` schema；导入服务把文档翻译成「图写入计划」（纯数据，可脱库测试）；Neo4j repository 执行写入并支持幂等重导入；FastAPI 暴露 `POST /import/game` 与 `GET /games/{id}`。现有 fixture pipeline 及其测试保持不变。

**Tech Stack:** Python 3.11+、Pydantic v2、FastAPI、Neo4j 官方 driver、pytest、httpx（TestClient）、Docker Compose。

---

## 设计参考

- Spec：`docs/superpowers/specs/2026-06-08-manual-game-import-design.zh-CN.md`
- 复用的现有代码：
  - `backend/app/schemas/common.py`：`StrictBaseModel`、`NonEmptyStr`、`ConfidenceLevel`、`QualityStatus`、`EvidenceRef`
  - `backend/app/schemas/artifacts.py`：`SeedGame`、`DesignClaim`
  - 测试约定：`Path(__file__).resolve().parents[1] / "app" / "fixtures" / ...`，`pydantic.ValidationError`，`ContractViolation`

## 文件结构

新建/修改：

- 修改 `backend/pyproject.toml` — 增加 fastapi/uvicorn/neo4j/httpx 依赖与 `integration` marker
- 修改 `backend/app/schemas/artifacts.py` — 新增 `ReferenceValueTag`、`GameDesignProfile`
- 新建 `backend/app/schemas/import_document.py` — `GameImportDocument`
- 新建 `backend/app/services/import_service.py` — 校验 + 图写入计划 + 计数
- 新建 `backend/app/graph/__init__.py`
- 新建 `backend/app/graph/connection.py` — Neo4j driver 设置与工厂
- 新建 `backend/app/graph/game_repository.py` — 执行图写入、读回
- 新建 `backend/app/api/__init__.py`
- 新建 `backend/app/api/routes_import.py` — 端点
- 新建 `backend/app/main.py` — FastAPI app 装配 + 异常处理
- 新建 `backend/app/fixtures/games/balatro.json` — 真实样例导入文档
- 新建 `backend/docker-compose.yml`、`backend/.env.example`
- 新建测试：`test_game_import_document.py`、`test_import_service.py`、`test_import_api.py`、`test_game_repository_integration.py`
- 新建 `docs/superpowers/import-guide/game-import-prompt.md`

---

## Task 1: 依赖与测试 marker

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: 更新 pyproject.toml**

把文件整体改为：

```toml
[project]
name = "gamegraph-backend"
version = "0.1.0"
description = "Backend contract slice for the GameGraph fixture pipeline"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.7,<3",
  "fastapi>=0.111,<1",
  "uvicorn[standard]>=0.30,<1",
  "neo4j>=5.20,<6",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2,<9",
  "httpx>=0.27,<1",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
markers = [
  "integration: tests that require a running Neo4j instance (deselected by default)",
]
addopts = "-m 'not integration'"
```

- [ ] **Step 2: 安装依赖**

Run（在 `backend/` 目录）：`pip install -e ".[dev]"`
Expected: 成功安装 fastapi、uvicorn、neo4j、httpx。

- [ ] **Step 3: 验证现有测试仍通过**

Run（在 `backend/` 目录）：`pytest -v`
Expected: 现有 `test_artifact_contracts.py` / `test_fixture_pipeline.py` / `test_project_structure.py` 全部 PASS；integration 测试默认被 `-m 'not integration'` 跳过（此时还没有）。

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore: add fastapi/neo4j/httpx deps and integration marker

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: ReferenceValueTag 与 GameDesignProfile schema

**Files:**
- Modify: `backend/app/schemas/artifacts.py`
- Test: `backend/tests/test_game_import_document.py`（本任务先建文件，写 schema 级测试）

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_game_import_document.py`：

```python
import pytest
from pydantic import ValidationError

from app.schemas.artifacts import GameDesignProfile, ReferenceValueTag
from app.schemas.common import ConfidenceLevel, EvidenceRef, QualityStatus


def evidence() -> EvidenceRef:
    return EvidenceRef(
        title="Design summary",
        quote_or_summary="Abstract card UI keeps art load low.",
        notes="Curated design interpretation.",
    )


def valid_profile_kwargs() -> dict:
    return {
        "game_id": "game_balatro",
        "one_sentence_summary": "Poker-hand roguelike deckbuilder built on score multipliers.",
        "core_loop": "Play poker hands, buy jokers that rewrite scoring, beat escalating blinds.",
        "progression_model": "Run-based economy buying jokers and upgrades between blinds.",
        "failure_model": "Failing to reach the blind score ends the run.",
        "content_structure": "Procedural run with a fixed escalating blind ladder.",
        "main_player_actions": ["select cards for a hand", "buy and arrange jokers"],
        "main_player_decisions": ["which hand to build", "which joker synergy to chase"],
        "main_player_experiences": ["snowballing payoff", "combo discovery"],
        "main_mechanics": ["poker hand building", "score multiplier engine"],
        "replayability_sources": ["randomized joker pools", "deck variety"],
        "production_constraints": ["abstract card UI", "no character animation"],
        "innovation_patterns": ["familiar rules as on-ramp to systemic depth"],
        "reusable_reference_patterns": ["score multiplier engine", "familiar rule vocabulary"],
        "non_replicable_risks": ["balancing exponential scoring is hard"],
        "reference_value_tags": [
            ReferenceValueTag(
                tag="low art cost reference",
                confidence=ConfidenceLevel.HIGH,
                quality_status=QualityStatus.REVIEWED,
                evidence=[evidence()],
            )
        ],
        "evidence": [evidence()],
        "confidence": ConfidenceLevel.HIGH,
        "quality_status": QualityStatus.REVIEWED,
    }


def test_reference_value_tag_allows_empty_evidence() -> None:
    tag = ReferenceValueTag(
        tag="high systemic depth reference",
        confidence=ConfidenceLevel.MEDIUM,
        quality_status=QualityStatus.DRAFT,
    )
    assert tag.evidence == []


def test_game_design_profile_accepts_valid_payload() -> None:
    profile = GameDesignProfile(**valid_profile_kwargs())
    assert profile.game_id == "game_balatro"
    assert profile.confidence == ConfidenceLevel.HIGH
    assert len(profile.main_mechanics) == 2


def test_game_design_profile_rejects_empty_list_field() -> None:
    kwargs = valid_profile_kwargs()
    kwargs["main_mechanics"] = []
    with pytest.raises(ValidationError):
        GameDesignProfile(**kwargs)


def test_game_design_profile_rejects_unknown_field() -> None:
    kwargs = valid_profile_kwargs()
    kwargs["extra_field"] = "nope"
    with pytest.raises(ValidationError):
        GameDesignProfile(**kwargs)
```

- [ ] **Step 2: 运行测试确认失败**

Run（`backend/`）：`pytest tests/test_game_import_document.py -v`
Expected: FAIL，`ImportError: cannot import name 'GameDesignProfile'`。

- [ ] **Step 3: 实现 schema**

在 `backend/app/schemas/artifacts.py` 末尾追加（文件顶部已 import `ConfidenceLevel, ConstraintType, EvidenceRef, NonEmptyStr, QualityStatus, StrictBaseModel`，无需改 import）：

```python
class ReferenceValueTag(StrictBaseModel):
    tag: str = Field(min_length=1)
    confidence: ConfidenceLevel
    quality_status: QualityStatus
    evidence: list[EvidenceRef] = Field(default_factory=list)


class GameDesignProfile(StrictBaseModel):
    game_id: str = Field(min_length=1)
    one_sentence_summary: str = Field(min_length=1)
    core_loop: str = Field(min_length=1)
    progression_model: str = Field(min_length=1)
    failure_model: str = Field(min_length=1)
    content_structure: str = Field(min_length=1)
    main_player_actions: list[NonEmptyStr] = Field(min_length=1)
    main_player_decisions: list[NonEmptyStr] = Field(min_length=1)
    main_player_experiences: list[NonEmptyStr] = Field(min_length=1)
    main_mechanics: list[NonEmptyStr] = Field(min_length=1)
    replayability_sources: list[NonEmptyStr] = Field(min_length=1)
    production_constraints: list[NonEmptyStr] = Field(min_length=1)
    innovation_patterns: list[NonEmptyStr] = Field(min_length=1)
    reusable_reference_patterns: list[NonEmptyStr] = Field(min_length=1)
    non_replicable_risks: list[NonEmptyStr] = Field(min_length=1)
    reference_value_tags: list[ReferenceValueTag] = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)
    confidence: ConfidenceLevel
    quality_status: QualityStatus
```

- [ ] **Step 4: 运行测试确认通过**

Run（`backend/`）：`pytest tests/test_game_import_document.py -v`
Expected: 4 个测试 PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/artifacts.py backend/tests/test_game_import_document.py
git commit -m "feat: add ReferenceValueTag and full GameDesignProfile schema

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: GameImportDocument schema

**Files:**
- Create: `backend/app/schemas/import_document.py`
- Test: `backend/tests/test_game_import_document.py`（追加）

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_game_import_document.py` 顶部 import 处追加：

```python
from app.schemas.artifacts import DesignClaim
from app.schemas.import_document import GameImportDocument
```

在文件末尾追加：

```python
def valid_candidate_kwargs() -> dict:
    return {
        "id": "game_balatro",
        "title": "Balatro",
        "source_refs": [evidence()],
        "short_description": "Poker-inspired roguelike deckbuilder.",
        "selection_reason": "Strong sample for familiar rules into systemic depth.",
    }


def valid_document_kwargs() -> dict:
    return {
        "candidate": valid_candidate_kwargs(),
        "profile": valid_profile_kwargs(),
        "claims": [],
    }


def test_import_document_accepts_zero_claims() -> None:
    document = GameImportDocument(**valid_document_kwargs())
    assert document.claims == []
    assert document.candidate.id == "game_balatro"
    assert document.profile.game_id == "game_balatro"


def test_import_document_defaults_claims_to_empty_list() -> None:
    kwargs = valid_document_kwargs()
    del kwargs["claims"]
    document = GameImportDocument(**kwargs)
    assert document.claims == []


def test_import_document_accepts_claims() -> None:
    kwargs = valid_document_kwargs()
    kwargs["claims"] = [
        DesignClaim(
            id="claim_balatro_familiar_rules",
            subject="Balatro",
            relation="reduces",
            object="new player learning cost",
            explanation="Players already know poker hands.",
            evidence=[evidence()],
            confidence=ConfidenceLevel.HIGH,
            quality_status=QualityStatus.REVIEWED,
        ).model_dump()
    ]
    document = GameImportDocument(**kwargs)
    assert len(document.claims) == 1
    assert document.claims[0].subject == "Balatro"
```

- [ ] **Step 2: 运行测试确认失败**

Run（`backend/`）：`pytest tests/test_game_import_document.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'app.schemas.import_document'`。

- [ ] **Step 3: 实现 schema**

新建 `backend/app/schemas/import_document.py`：

```python
from __future__ import annotations

from pydantic import Field

from app.schemas.artifacts import DesignClaim, GameDesignProfile, SeedGame
from app.schemas.common import StrictBaseModel


class GameImportDocument(StrictBaseModel):
    candidate: SeedGame
    profile: GameDesignProfile
    claims: list[DesignClaim] = Field(default_factory=list)
```

- [ ] **Step 4: 运行测试确认通过**

Run（`backend/`）：`pytest tests/test_game_import_document.py -v`
Expected: 全部 PASS（含 Task 2 的 4 个 + 新 3 个）。

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/import_document.py backend/tests/test_game_import_document.py
git commit -m "feat: add GameImportDocument schema with optional claims

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: 导入契约校验

**Files:**
- Create: `backend/app/services/import_service.py`
- Test: `backend/tests/test_import_service.py`

校验 `profile.game_id == candidate.id`，失败抛 `ContractViolation`。复用 `fixture_pipeline.ContractViolation` 以保持单一错误类型。

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_import_service.py`：

```python
import pytest
from pydantic import ValidationError

from app.schemas.common import ConfidenceLevel, EvidenceRef, QualityStatus
from app.services.fixture_pipeline import ContractViolation
from app.services.import_service import validate_import_document


def evidence() -> dict:
    return {
        "title": "Design summary",
        "quote_or_summary": "Abstract card UI keeps art load low.",
        "notes": "Curated design interpretation.",
    }


def profile_payload() -> dict:
    return {
        "game_id": "game_balatro",
        "one_sentence_summary": "Poker-hand roguelike deckbuilder built on score multipliers.",
        "core_loop": "Play poker hands, buy jokers that rewrite scoring, beat escalating blinds.",
        "progression_model": "Run-based economy buying jokers between blinds.",
        "failure_model": "Failing to reach the blind score ends the run.",
        "content_structure": "Procedural run with a fixed escalating blind ladder.",
        "main_player_actions": ["select cards for a hand", "buy and arrange jokers"],
        "main_player_decisions": ["which hand to build", "which joker synergy to chase"],
        "main_player_experiences": ["snowballing payoff", "combo discovery"],
        "main_mechanics": ["poker hand building", "score multiplier engine"],
        "replayability_sources": ["randomized joker pools", "deck variety"],
        "production_constraints": ["abstract card UI", "no character animation"],
        "innovation_patterns": ["familiar rules as on-ramp to systemic depth"],
        "reusable_reference_patterns": ["score multiplier engine", "familiar rule vocabulary"],
        "non_replicable_risks": ["balancing exponential scoring is hard"],
        "reference_value_tags": [
            {
                "tag": "low art cost reference",
                "confidence": "high",
                "quality_status": "reviewed",
                "evidence": [evidence()],
            }
        ],
        "evidence": [evidence()],
        "confidence": "high",
        "quality_status": "reviewed",
    }


def document_payload() -> dict:
    return {
        "candidate": {
            "id": "game_balatro",
            "title": "Balatro",
            "source_refs": [evidence()],
            "short_description": "Poker-inspired roguelike deckbuilder.",
            "selection_reason": "Strong sample for familiar rules into systemic depth.",
        },
        "profile": profile_payload(),
        "claims": [],
    }


def test_validate_import_document_returns_typed_document() -> None:
    document = validate_import_document(document_payload())
    assert document.candidate.id == "game_balatro"
    assert document.profile.game_id == "game_balatro"


def test_validate_import_document_rejects_mismatched_game_id() -> None:
    payload = document_payload()
    payload["profile"]["game_id"] = "game_other"
    with pytest.raises(ContractViolation, match="profile.game_id must match candidate.id"):
        validate_import_document(payload)


def test_validate_import_document_raises_validation_error_on_bad_schema() -> None:
    payload = document_payload()
    payload["profile"]["main_mechanics"] = []
    with pytest.raises(ValidationError):
        validate_import_document(payload)
```

- [ ] **Step 2: 运行测试确认失败**

Run（`backend/`）：`pytest tests/test_import_service.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'app.services.import_service'`。

- [ ] **Step 3: 实现 validate 部分**

新建 `backend/app/services/import_service.py`：

```python
from __future__ import annotations

from typing import Any

from app.schemas.import_document import GameImportDocument
from app.services.fixture_pipeline import ContractViolation


def check_import_contracts(document: GameImportDocument) -> None:
    if document.profile.game_id != document.candidate.id:
        raise ContractViolation("profile.game_id must match candidate.id")


def validate_import_document(raw: dict[str, Any]) -> GameImportDocument:
    document = GameImportDocument.model_validate(raw)
    check_import_contracts(document)
    return document
```

- [ ] **Step 4: 运行测试确认通过**

Run（`backend/`）：`pytest tests/test_import_service.py -v`
Expected: 3 个测试 PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/import_service.py backend/tests/test_import_service.py
git commit -m "feat: add import document contract validation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: 图写入计划与计数

**Files:**
- Modify: `backend/app/services/import_service.py`
- Test: `backend/tests/test_import_service.py`（追加）

把文档翻译成 `GraphWritePlan`（纯数据，可脱库断言），并提供 `summarize` 计数。`EvidenceRef` 列表序列化为 JSON 字符串属性，整个文档另存 `document_json` 供精确读回。

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_import_service.py` import 区追加：

```python
from app.services.import_service import build_graph_write_plan, summarize
```

文件末尾追加：

```python
def test_build_graph_write_plan_creates_game_node_with_document_json() -> None:
    document = validate_import_document(document_payload())
    plan = build_graph_write_plan(document)

    assert plan.game_id == "game_balatro"
    game_nodes = [node for node in plan.nodes if node.label == "Game"]
    assert len(game_nodes) == 1
    game = game_nodes[0]
    assert game.key == {"id": "game_balatro"}
    assert game.properties["title"] == "Balatro"
    assert game.properties["core_loop"].startswith("Play poker hands")
    # 嵌套证据被序列化为 JSON 字符串
    assert game.properties["evidence_json"].startswith("[")
    assert game.properties["document_json"].startswith("{")


def test_build_graph_write_plan_creates_mechanic_and_tag_edges() -> None:
    document = validate_import_document(document_payload())
    plan = build_graph_write_plan(document)

    mechanic_edges = [edge for edge in plan.edges if edge.rel_type == "HAS_MECHANIC"]
    assert {edge.to_key["name"] for edge in mechanic_edges} == {
        "poker hand building",
        "score multiplier engine",
    }

    tag_edges = [edge for edge in plan.edges if edge.rel_type == "TAGGED"]
    assert len(tag_edges) == 1
    assert tag_edges[0].to_key["name"] == "low art cost reference"
    assert tag_edges[0].properties["confidence"] == "high"
    assert tag_edges[0].properties["evidence_json"].startswith("[")


def test_build_graph_write_plan_with_zero_claims_has_no_claim_edges() -> None:
    document = validate_import_document(document_payload())
    plan = build_graph_write_plan(document)
    assert [edge for edge in plan.edges if edge.rel_type == "CLAIM"] == []


def test_build_graph_write_plan_creates_claim_edges() -> None:
    payload = document_payload()
    payload["claims"] = [
        {
            "id": "claim_balatro_familiar_rules",
            "subject": "Balatro",
            "relation": "reduces",
            "object": "new player learning cost",
            "explanation": "Players already know poker hands.",
            "evidence": [evidence()],
            "confidence": "high",
            "quality_status": "reviewed",
        }
    ]
    document = validate_import_document(payload)
    plan = build_graph_write_plan(document)

    claim_edges = [edge for edge in plan.edges if edge.rel_type == "CLAIM"]
    assert len(claim_edges) == 1
    edge = claim_edges[0]
    assert edge.from_key == {"id": "game_balatro"}
    assert edge.to_label == "Concept"
    assert edge.to_key == {"name": "new player learning cost"}
    assert edge.properties["claim_id"] == "claim_balatro_familiar_rules"
    assert edge.properties["relation"] == "reduces"
    assert edge.properties["confidence"] == "high"


def test_summarize_counts_written_elements() -> None:
    document = validate_import_document(document_payload())
    summary = summarize(document)
    assert summary.game_id == "game_balatro"
    assert summary.mechanics_written == 2
    assert summary.experiences_written == 2
    assert summary.tags_written == 1
    assert summary.claims_written == 0
    assert summary.concepts_written == 0
```

- [ ] **Step 2: 运行测试确认失败**

Run（`backend/`）：`pytest tests/test_import_service.py -v`
Expected: FAIL，`ImportError: cannot import name 'build_graph_write_plan'`。

- [ ] **Step 3: 实现图写入计划**

把 `backend/app/services/import_service.py` 整体改为：

```python
from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from app.schemas.common import EvidenceRef, StrictBaseModel
from app.schemas.import_document import GameImportDocument
from app.services.fixture_pipeline import ContractViolation


_EVIDENCE_LIST_ADAPTER = TypeAdapter(list[EvidenceRef])

# profile 列表字段 -> (边类型, 目标节点 label)
PROFILE_LIST_EDGES: dict[str, tuple[str, str]] = {
    "main_mechanics": ("HAS_MECHANIC", "Mechanic"),
    "main_player_actions": ("TAKES_ACTION", "PlayerAction"),
    "main_player_decisions": ("MAKES_DECISION", "PlayerDecision"),
    "main_player_experiences": ("DELIVERS_EXPERIENCE", "Experience"),
    "production_constraints": ("CONSTRAINED_BY", "ProductionConstraint"),
    "innovation_patterns": ("USES_INNOVATION", "InnovationPattern"),
    "reusable_reference_patterns": ("REUSABLE_PATTERN", "ReferencePattern"),
    "non_replicable_risks": ("NON_REPLICABLE_RISK", "Risk"),
    "replayability_sources": ("HAS_REPLAYABILITY_SOURCE", "ReplayabilitySource"),
}


class NodeMerge(StrictBaseModel):
    label: str
    key: dict[str, str]
    properties: dict[str, str]


class EdgeMerge(StrictBaseModel):
    rel_type: str
    from_label: str
    from_key: dict[str, str]
    to_label: str
    to_key: dict[str, str]
    properties: dict[str, str]


class GraphWritePlan(StrictBaseModel):
    game_id: str
    nodes: list[NodeMerge]
    edges: list[EdgeMerge]


class ImportSummary(StrictBaseModel):
    game_id: str
    mechanics_written: int
    experiences_written: int
    tags_written: int
    concepts_written: int
    claims_written: int


def check_import_contracts(document: GameImportDocument) -> None:
    if document.profile.game_id != document.candidate.id:
        raise ContractViolation("profile.game_id must match candidate.id")


def validate_import_document(raw: dict[str, Any]) -> GameImportDocument:
    document = GameImportDocument.model_validate(raw)
    check_import_contracts(document)
    return document


def _evidence_json(evidence: list[EvidenceRef]) -> str:
    return _EVIDENCE_LIST_ADAPTER.dump_json(evidence).decode("utf-8")


def _game_node(document: GameImportDocument) -> NodeMerge:
    candidate = document.candidate
    profile = document.profile
    properties = {
        "title": candidate.title,
        "short_description": candidate.short_description,
        "selection_reason": candidate.selection_reason,
        "one_sentence_summary": profile.one_sentence_summary,
        "core_loop": profile.core_loop,
        "progression_model": profile.progression_model,
        "failure_model": profile.failure_model,
        "content_structure": profile.content_structure,
        "confidence": profile.confidence.value,
        "quality_status": profile.quality_status.value,
        "source_refs_json": _evidence_json(candidate.source_refs),
        "evidence_json": _evidence_json(profile.evidence),
        "document_json": document.model_dump_json(),
    }
    return NodeMerge(label="Game", key={"id": candidate.id}, properties=properties)


def _profile_list_edges(document: GameImportDocument) -> list[EdgeMerge]:
    edges: list[EdgeMerge] = []
    game_key = {"id": document.candidate.id}
    for field_name, (rel_type, label) in PROFILE_LIST_EDGES.items():
        for name in getattr(document.profile, field_name):
            edges.append(
                EdgeMerge(
                    rel_type=rel_type,
                    from_label="Game",
                    from_key=game_key,
                    to_label=label,
                    to_key={"name": name},
                    properties={},
                )
            )
    return edges


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
                to_key={"name": tag.tag},
                properties={
                    "confidence": tag.confidence.value,
                    "quality_status": tag.quality_status.value,
                    "evidence_json": _evidence_json(tag.evidence),
                },
            )
        )
    return edges


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
                    "evidence_json": _evidence_json(claim.evidence),
                    "confidence": claim.confidence.value,
                    "quality_status": claim.quality_status.value,
                },
            )
        )
    return edges


def build_graph_write_plan(document: GameImportDocument) -> GraphWritePlan:
    edges = [
        *_profile_list_edges(document),
        *_tag_edges(document),
        *_claim_edges(document),
    ]
    return GraphWritePlan(
        game_id=document.candidate.id,
        nodes=[_game_node(document)],
        edges=edges,
    )


def summarize(document: GameImportDocument) -> ImportSummary:
    return ImportSummary(
        game_id=document.candidate.id,
        mechanics_written=len(document.profile.main_mechanics),
        experiences_written=len(document.profile.main_player_experiences),
        tags_written=len(document.profile.reference_value_tags),
        concepts_written=len(document.claims),
        claims_written=len(document.claims),
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run（`backend/`）：`pytest tests/test_import_service.py -v`
Expected: 全部 PASS（Task 4 的 3 个 + 新 6 个）。

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/import_service.py backend/tests/test_import_service.py
git commit -m "feat: translate import document into graph write plan and summary

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Balatro 样例导入文档

**Files:**
- Create: `backend/app/fixtures/games/balatro.json`
- Test: `backend/tests/test_game_import_document.py`（追加）

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_game_import_document.py` 顶部 import 追加：

```python
import json
from pathlib import Path
```

文件末尾追加：

```python
def test_balatro_fixture_is_a_valid_import_document() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "app" / "fixtures" / "games" / "balatro.json"
    )
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    document = GameImportDocument.model_validate(raw)

    assert document.candidate.id == "game_balatro"
    assert document.profile.game_id == document.candidate.id
    assert len(document.profile.reference_value_tags) >= 1
    # 至少一条 claim，且不存在 high 置信度的纯模型分析（诚实示范）
    assert len(document.claims) >= 1
```

- [ ] **Step 2: 运行测试确认失败**

Run（`backend/`）：`pytest tests/test_game_import_document.py::test_balatro_fixture_is_a_valid_import_document -v`
Expected: FAIL，`FileNotFoundError`。

- [ ] **Step 3: 创建样例文档**

新建 `backend/app/fixtures/games/balatro.json`：

```json
{
  "candidate": {
    "id": "game_balatro",
    "title": "Balatro",
    "source_refs": [
      {
        "title": "Balatro store page",
        "url": "https://store.steampowered.com/app/2379780/Balatro/",
        "notes": "Primary reference for the game candidate."
      }
    ],
    "short_description": "Poker-inspired roguelike deckbuilder built around familiar card semantics.",
    "selection_reason": "Strong sample for transforming familiar rules into systemic depth at low art cost."
  },
  "profile": {
    "game_id": "game_balatro",
    "one_sentence_summary": "A poker-hand roguelike deckbuilder where score multipliers, not direct combat, drive a snowballing run.",
    "core_loop": "Play poker hands, buy and arrange jokers that rewrite scoring, then beat escalating blind targets.",
    "progression_model": "Run-based economy where the player spends winnings on jokers and upgrades between blinds.",
    "failure_model": "Failing to reach a blind's score threshold ends the current run.",
    "content_structure": "Procedural run over a fixed escalating ladder of blinds with shop phases between them.",
    "main_player_actions": [
      "select cards to form a poker hand",
      "buy jokers and consumables in the shop",
      "arrange joker order for scoring"
    ],
    "main_player_decisions": [
      "which poker hand to commit to this round",
      "which joker synergy to invest in",
      "when to reroll or save money"
    ],
    "main_player_experiences": [
      "snowballing scoring payoff",
      "combo discovery",
      "tense threshold pushing"
    ],
    "main_mechanics": [
      "poker hand building",
      "score multiplier engine",
      "joker synergies"
    ],
    "replayability_sources": [
      "randomized joker pools",
      "deck and stake variety",
      "emergent scoring combos"
    ],
    "production_constraints": [
      "abstract card UI",
      "no character animation",
      "text and number driven feedback"
    ],
    "innovation_patterns": [
      "familiar rules as an on-ramp to systemic depth",
      "scoring engine as the core toy"
    ],
    "reusable_reference_patterns": [
      "score multiplier engine",
      "familiar rule vocabulary",
      "shop-driven run economy"
    ],
    "non_replicable_risks": [
      "balancing exponential scoring is difficult",
      "depth depends on a large tuned joker set"
    ],
    "reference_value_tags": [
      {
        "tag": "low art cost reference",
        "confidence": "high",
        "quality_status": "reviewed",
        "evidence": [
          {
            "title": "Balatro presentation",
            "quote_or_summary": "The game communicates almost entirely through cards, text, and numbers rather than animation.",
            "notes": "Observable from store media."
          }
        ]
      },
      {
        "tag": "high systemic depth reference",
        "confidence": "medium",
        "quality_status": "draft",
        "evidence": [
          {
            "title": "Design interpretation",
            "quote_or_summary": "Joker combinations create deep emergent scoring strategies.",
            "notes": "Model analysis, not externally cited."
          }
        ]
      }
    ],
    "evidence": [
      {
        "title": "Balatro design summary",
        "quote_or_summary": "Starts from recognizable poker hand logic and layers score modifiers over it.",
        "notes": "Curated design interpretation."
      }
    ],
    "confidence": "high",
    "quality_status": "reviewed"
  },
  "claims": [
    {
      "id": "claim_balatro_familiar_rules",
      "subject": "Balatro",
      "relation": "reduces",
      "object": "new player learning cost",
      "explanation": "Players already understand poker hands, so the systemic depth layers onto known rules instead of new ones.",
      "evidence": [
        {
          "title": "Balatro design summary",
          "quote_or_summary": "Recognizable poker hands give an immediate rules vocabulary before modifiers add depth.",
          "notes": "Curated design interpretation."
        }
      ],
      "confidence": "high",
      "quality_status": "reviewed"
    },
    {
      "id": "claim_balatro_abstract_ui_low_art",
      "subject": "abstract card UI",
      "relation": "reduces",
      "object": "solo developer art production burden",
      "explanation": "Card, text, and number feedback avoids animation and bespoke art, lowering production load for a small team.",
      "evidence": [
        {
          "title": "Design interpretation",
          "quote_or_summary": "Pure card and number presentation needs no animation pipeline.",
          "notes": "Model analysis, not externally cited."
        }
      ],
      "confidence": "medium",
      "quality_status": "draft"
    }
  ]
}
```

- [ ] **Step 4: 运行测试确认通过**

Run（`backend/`）：`pytest tests/test_game_import_document.py -v`
Expected: 全部 PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/app/fixtures/games/balatro.json backend/tests/test_game_import_document.py
git commit -m "test: add Balatro sample import document fixture

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Neo4j 连接层

**Files:**
- Create: `backend/app/graph/__init__.py`
- Create: `backend/app/graph/connection.py`
- Test: `backend/tests/test_import_service.py`（追加，仅测试设置解析，不连库）

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_import_service.py` import 区追加：

```python
from app.graph.connection import Neo4jSettings
```

文件末尾追加：

```python
def test_neo4j_settings_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret-password")

    settings = Neo4jSettings.from_env()

    assert settings.uri == "bolt://localhost:7687"
    assert settings.user == "neo4j"
    assert settings.password == "secret-password"


def test_neo4j_settings_defaults_uri(monkeypatch) -> None:
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret-password")

    settings = Neo4jSettings.from_env()

    assert settings.uri == "bolt://localhost:7687"
```

- [ ] **Step 2: 运行测试确认失败**

Run（`backend/`）：`pytest tests/test_import_service.py -k neo4j_settings -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'app.graph'`。

- [ ] **Step 3: 实现连接层**

新建 `backend/app/graph/__init__.py`（空文件）。

新建 `backend/app/graph/connection.py`：

```python
from __future__ import annotations

import os
from dataclasses import dataclass

from neo4j import Driver, GraphDatabase


@dataclass(frozen=True)
class Neo4jSettings:
    uri: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "Neo4jSettings":
        return cls(
            uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            user=os.environ.get("NEO4J_USER", "neo4j"),
            password=os.environ["NEO4J_PASSWORD"],
        )


def create_driver(settings: Neo4jSettings | None = None) -> Driver:
    resolved = settings or Neo4jSettings.from_env()
    return GraphDatabase.driver(resolved.uri, auth=(resolved.user, resolved.password))
```

- [ ] **Step 4: 运行测试确认通过**

Run（`backend/`）：`pytest tests/test_import_service.py -k neo4j_settings -v`
Expected: 2 个测试 PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/app/graph/__init__.py backend/app/graph/connection.py backend/tests/test_import_service.py
git commit -m "feat: add Neo4j connection settings and driver factory

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: GameRepository（写入 + 读回）

**Files:**
- Create: `backend/app/graph/game_repository.py`

repository 把 `GraphWritePlan` 翻译成 Cypher 并在一个事务里执行（先删该 Game 全部出边，再 MERGE 节点与边）；`get_game` 读 `document_json` 精确还原。Cypher 的 label/rel_type 来自固定白名单，避免注入。本任务不含单元测试（执行逻辑由 Task 10 的 integration 测试覆盖；纯逻辑已在 Task 5 覆盖）。

- [ ] **Step 1: 实现 repository**

新建 `backend/app/graph/game_repository.py`：

```python
from __future__ import annotations

import json

from neo4j import Driver

from app.schemas.import_document import GameImportDocument
from app.services.import_service import (
    EdgeMerge,
    GraphWritePlan,
    ImportSummary,
    NodeMerge,
    PROFILE_LIST_EDGES,
    build_graph_write_plan,
    summarize,
)

# 允许写入的 (rel_type -> 目标 label) 白名单，防止动态 Cypher 注入
_ALLOWED_EDGES: dict[str, str] = {
    rel_type: label for rel_type, label in PROFILE_LIST_EDGES.values()
}
_ALLOWED_EDGES["TAGGED"] = "ReferenceTag"
_ALLOWED_EDGES["CLAIM"] = "Concept"

_ALLOWED_NODE_LABELS = {"Game", *_ALLOWED_EDGES.values()}


class GameRepository:
    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def upsert_game(self, document: GameImportDocument) -> ImportSummary:
        plan = build_graph_write_plan(document)
        with self._driver.session() as session:
            session.execute_write(self._write_plan, plan)
        return summarize(document)

    def get_game(self, game_id: str) -> GameImportDocument | None:
        with self._driver.session() as session:
            record = session.execute_read(self._read_game, game_id)
        if record is None:
            return None
        return GameImportDocument.model_validate_json(record)

    @staticmethod
    def _write_plan(tx, plan: GraphWritePlan) -> None:
        # 1) 幂等：先删该 Game 的全部出边
        tx.run(
            "MATCH (g:Game {id: $game_id})-[r]->() DELETE r",
            game_id=plan.game_id,
        )
        # 2) MERGE 节点
        for node in plan.nodes:
            _validate_node(node)
            (key_field, key_value), = node.key.items()
            tx.run(
                f"MERGE (n:{node.label} {{{key_field}: $key}}) SET n += $props",
                key=key_value,
                props=node.properties,
            )
        # 3) MERGE 边
        for edge in plan.edges:
            _validate_edge(edge)
            (from_field, from_value), = edge.from_key.items()
            (to_field, to_value), = edge.to_key.items()
            tx.run(
                f"MATCH (a:{edge.from_label} {{{from_field}: $from_value}}) "
                f"MERGE (b:{edge.to_label} {{{to_field}: $to_value}}) "
                f"MERGE (a)-[r:{edge.rel_type}]->(b) SET r += $props",
                from_value=from_value,
                to_value=to_value,
                props=edge.properties,
            )

    @staticmethod
    def _read_game(tx, game_id: str) -> str | None:
        result = tx.run(
            "MATCH (g:Game {id: $game_id}) RETURN g.document_json AS document_json",
            game_id=game_id,
        )
        record = result.single()
        if record is None:
            return None
        return record["document_json"]


def _validate_node(node: NodeMerge) -> None:
    if node.label not in _ALLOWED_NODE_LABELS:
        raise ValueError(f"Unexpected node label: {node.label}")
    if len(node.key) != 1:
        raise ValueError("NodeMerge.key must contain exactly one field")


def _validate_edge(edge: EdgeMerge) -> None:
    if edge.from_label not in _ALLOWED_NODE_LABELS:
        raise ValueError(f"Unexpected from_label: {edge.from_label}")
    if _ALLOWED_EDGES.get(edge.rel_type) != edge.to_label:
        raise ValueError(f"Unexpected edge: {edge.rel_type} -> {edge.to_label}")
    if len(edge.from_key) != 1 or len(edge.to_key) != 1:
        raise ValueError("Edge keys must contain exactly one field")
```

- [ ] **Step 2: 验证导入无语法错误**

Run（`backend/`）：`python -c "import app.graph.game_repository"`
Expected: 无输出、无报错（neo4j 已安装，模块可导入）。

- [ ] **Step 3: 运行全部非 integration 测试确认未破坏**

Run（`backend/`）：`pytest -v`
Expected: 现有全部 PASS，无新失败。

- [ ] **Step 4: Commit**

```bash
git add backend/app/graph/game_repository.py
git commit -m "feat: add Neo4j game repository with idempotent upsert and read-back

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: FastAPI 应用与端点

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/routes_import.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_import_api.py`

端点用依赖注入获取 repository，测试时用 fake repo 覆盖。字段级 schema 错误由 FastAPI 自动 422；`ContractViolation` 经异常处理器映射 409。

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_import_api.py`：

```python
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes_import import get_repository
from app.schemas.import_document import GameImportDocument
from app.services.import_service import ImportSummary, summarize


class FakeRepository:
    def __init__(self) -> None:
        self.saved: dict[str, GameImportDocument] = {}

    def upsert_game(self, document: GameImportDocument) -> ImportSummary:
        self.saved[document.candidate.id] = document
        return summarize(document)

    def get_game(self, game_id: str) -> GameImportDocument | None:
        return self.saved.get(game_id)


@pytest.fixture()
def fake_repo() -> FakeRepository:
    return FakeRepository()


@pytest.fixture()
def client(fake_repo: FakeRepository) -> TestClient:
    app.dependency_overrides[get_repository] = lambda: fake_repo
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def balatro_payload() -> dict:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "app" / "fixtures" / "games" / "balatro.json"
    )
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_import_game_returns_summary(client: TestClient) -> None:
    response = client.post("/import/game", json=balatro_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["game_id"] == "game_balatro"
    assert body["mechanics_written"] == 3
    assert body["tags_written"] == 2
    assert body["claims_written"] == 2


def test_import_game_rejects_invalid_schema_with_422(client: TestClient) -> None:
    payload = balatro_payload()
    payload["profile"]["main_mechanics"] = []
    response = client.post("/import/game", json=payload)
    assert response.status_code == 422


def test_import_game_rejects_contract_violation_with_409(client: TestClient) -> None:
    payload = balatro_payload()
    payload["profile"]["game_id"] = "game_other"
    response = client.post("/import/game", json=payload)
    assert response.status_code == 409
    assert "profile.game_id must match candidate.id" in response.json()["detail"]


def test_get_game_returns_imported_document(client: TestClient) -> None:
    client.post("/import/game", json=balatro_payload())
    response = client.get("/games/game_balatro")
    assert response.status_code == 200
    assert response.json()["candidate"]["id"] == "game_balatro"


def test_get_game_returns_404_when_missing(client: TestClient) -> None:
    response = client.get("/games/game_unknown")
    assert response.status_code == 404
```

- [ ] **Step 2: 运行测试确认失败**

Run（`backend/`）：`pytest tests/test_import_api.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'app.main'`。

- [ ] **Step 3: 实现路由**

新建 `backend/app/api/__init__.py`（空文件）。

新建 `backend/app/api/routes_import.py`：

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.graph.connection import create_driver
from app.graph.game_repository import GameRepository
from app.schemas.import_document import GameImportDocument
from app.services.import_service import ImportSummary, check_import_contracts

router = APIRouter()

_driver = None


def get_repository() -> GameRepository:
    # 默认 provider：惰性创建单例 driver。测试通过 dependency_overrides 覆盖本函数。
    global _driver
    if _driver is None:
        _driver = create_driver()
    return GameRepository(_driver)


@router.post("/import/game", response_model=ImportSummary)
def import_game(
    document: GameImportDocument,
    repository: GameRepository = Depends(get_repository),
) -> ImportSummary:
    check_import_contracts(document)
    return repository.upsert_game(document)


@router.get("/games/{game_id}", response_model=GameImportDocument)
def get_game(
    game_id: str,
    repository: GameRepository = Depends(get_repository),
) -> GameImportDocument:
    document = repository.get_game(game_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")
    return document
```

新建 `backend/app/main.py`：

```python
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes_import import router
from app.services.fixture_pipeline import ContractViolation

app = FastAPI(title="GameGraph Import API")
app.include_router(router)


@app.exception_handler(ContractViolation)
async def contract_violation_handler(
    request: Request, exc: ContractViolation
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})
```

- [ ] **Step 4: 运行测试确认通过**

Run（`backend/`）：`pytest tests/test_import_api.py -v`
Expected: 5 个测试 PASS。

- [ ] **Step 5: 运行全部非 integration 测试**

Run（`backend/`）：`pytest -v`
Expected: 全部 PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/__init__.py backend/app/api/routes_import.py backend/app/main.py backend/tests/test_import_api.py
git commit -m "feat: add FastAPI import endpoint and game read endpoint

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 10: Docker Compose、环境样例与 integration 测试

**Files:**
- Create: `backend/docker-compose.yml`
- Create: `backend/.env.example`
- Test: `backend/tests/test_game_repository_integration.py`

integration 测试默认被 `addopts = -m 'not integration'` 跳过，仅在显式 `-m integration` 且有真实 Neo4j 时运行。

- [ ] **Step 1: 创建 docker-compose.yml**

新建 `backend/docker-compose.yml`：

```yaml
services:
  neo4j:
    image: neo4j:5.20
    container_name: gamegraph-neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/devpassword
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

- [ ] **Step 2: 创建 .env.example**

新建 `backend/.env.example`：

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=devpassword
```

- [ ] **Step 3: 写 integration 测试**

新建 `backend/tests/test_game_repository_integration.py`：

```python
import json
import os
from pathlib import Path

import pytest

from app.graph.connection import Neo4jSettings, create_driver
from app.graph.game_repository import GameRepository
from app.schemas.import_document import GameImportDocument

pytestmark = pytest.mark.integration


def balatro_document() -> GameImportDocument:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "app" / "fixtures" / "games" / "balatro.json"
    )
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    return GameImportDocument.model_validate(raw)


@pytest.fixture()
def driver():
    if "NEO4J_PASSWORD" not in os.environ:
        pytest.skip("NEO4J_PASSWORD not set; skipping Neo4j integration test")
    drv = create_driver(Neo4jSettings.from_env())
    try:
        drv.verify_connectivity()
    except Exception:
        pytest.skip("Neo4j is not reachable; skipping integration test")
    yield drv
    # 清理本测试写入的数据
    with drv.session() as session:
        session.run(
            "MATCH (g:Game {id: $id}) DETACH DELETE g", id="game_balatro"
        )
    drv.close()


def test_upsert_then_read_round_trips(driver) -> None:
    repo = GameRepository(driver)
    document = balatro_document()

    summary = repo.upsert_game(document)
    assert summary.game_id == "game_balatro"

    read = repo.get_game("game_balatro")
    assert read is not None
    assert read.candidate.id == "game_balatro"
    assert read.profile.game_id == "game_balatro"


def test_reimport_is_idempotent(driver) -> None:
    repo = GameRepository(driver)
    document = balatro_document()

    repo.upsert_game(document)
    repo.upsert_game(document)

    with driver.session() as session:
        record = session.run(
            "MATCH (g:Game {id: $id})-[r]->() RETURN count(r) AS edge_count",
            id="game_balatro",
        ).single()
    # profile 列表边 + 2 个 tag 边 + 2 条 claim 边；重导入后不翻倍
    mechanic_count = len(document.profile.main_mechanics)
    assert record["edge_count"] > 0
    # 再次确认机制边没有重复
    with driver.session() as session:
        mech = session.run(
            "MATCH (:Game {id: $id})-[r:HAS_MECHANIC]->() RETURN count(r) AS c",
            id="game_balatro",
        ).single()
    assert mech["c"] == mechanic_count
```

- [ ] **Step 4: 验证默认跳过**

Run（`backend/`）：`pytest -v`
Expected: integration 测试**不出现**在运行列表里（被 `-m 'not integration'` 排除），其余全部 PASS。

- [ ] **Step 5: （可选，需 Docker）验证真实图行为**

Run（`backend/`）：
```bash
docker compose up -d neo4j
# 等待 Neo4j 就绪（约 10-20 秒）
NEO4J_PASSWORD=devpassword pytest -m integration -v
```
Expected: 2 个 integration 测试 PASS（或在 Neo4j 未就绪时 skip）。完成后可 `docker compose down`。

> 注意：Windows PowerShell 下设环境变量用 `$env:NEO4J_PASSWORD="devpassword"; pytest -m integration -v`。

- [ ] **Step 6: Commit**

```bash
git add backend/docker-compose.yml backend/.env.example backend/tests/test_game_repository_integration.py
git commit -m "test: add Neo4j docker-compose and integration round-trip tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 11: Claude 生成指令指南

**Files:**
- Create: `docs/superpowers/import-guide/game-import-prompt.md`

这是你手动操作时复制给 Claude 的产物。无代码测试，完成后人工核对内容完整。

- [ ] **Step 1: 创建指南**

新建 `docs/superpowers/import-guide/game-import-prompt.md`：

````markdown
# 游戏导入 JSON 生成指南

把下面的「指令模板」连同一个游戏名（或商店链接）发给 Claude，得到一个 `GameImportDocument` JSON，再 `POST /import/game` 导入。

## 指令模板（直接复制）

> 你是游戏设计标注员。请为我给定的游戏产出**单个合法 JSON**，符合下方 `GameImportDocument` 结构，不要输出 JSON 以外的任何文字。
>
> 硬规则：
> - `candidate` 只写入库理由与来源，**不要**写设计判断或机制推断。
> - `profile` 必须填满全部字段，列表字段不得为空。
> - `claims` 可选（0 条也行）；只为「非显而易见、可跨概念复用」的设计因果写，形如 `主体 - 关系 - 客体`，能落成图的一条边。
> - 仅凭你自身知识、没有外部出处的论断，`confidence` **不得**标 `high`，应标 `medium` 或 `low`，并在 `quality_status` 用 `draft` 或 `weak_evidence`。
> - 区分可观察事实与解释性判断；不确定就如实降置信度，不要假装确定。
> - 不要断言这款游戏「好玩」或「会商业成功」。
> - `confidence` 取值：`low` / `medium` / `high`。`quality_status` 取值：`draft` / `reviewed` / `weak_evidence` / `conflicting`。
> - 每个 `EvidenceRef` 必须有 `title` 与 `notes`，并且 `url` 与 `quote_or_summary` 至少有一个；没有外部链接时填 `quote_or_summary`。

## JSON 骨架（字段说明见注释）

```jsonc
{
  "candidate": {
    "id": "game_<slug>",                  // 唯一 id，与 profile.game_id 一致
    "title": "<游戏标题>",
    "source_refs": [
      { "title": "...", "url": "...", "notes": "..." }
    ],
    "short_description": "<一句话客观描述>",
    "selection_reason": "<为什么值得进种子库>"
  },
  "profile": {
    "game_id": "game_<slug>",             // 必须等于 candidate.id
    "one_sentence_summary": "...",
    "core_loop": "...",
    "progression_model": "...",
    "failure_model": "...",
    "content_structure": "...",
    "main_player_actions": ["..."],
    "main_player_decisions": ["..."],
    "main_player_experiences": ["..."],
    "main_mechanics": ["..."],
    "replayability_sources": ["..."],
    "production_constraints": ["..."],
    "innovation_patterns": ["..."],
    "reusable_reference_patterns": ["..."],
    "non_replicable_risks": ["..."],
    "reference_value_tags": [
      {
        "tag": "...",
        "confidence": "high|medium|low",
        "quality_status": "reviewed|draft|weak_evidence|conflicting",
        "evidence": [ { "title": "...", "quote_or_summary": "...", "notes": "..." } ]
      }
    ],
    "evidence": [ { "title": "...", "quote_or_summary": "...", "notes": "..." } ],
    "confidence": "high|medium|low",
    "quality_status": "reviewed|draft|weak_evidence|conflicting"
  },
  "claims": [
    {
      "id": "claim_<slug>",
      "subject": "<主体，可为游戏名或某机制>",
      "relation": "<关系动词，如 reduces / creates>",
      "object": "<客体概念>",
      "explanation": "...",
      "evidence": [ { "title": "...", "quote_or_summary": "...", "notes": "..." } ],
      "confidence": "high|medium|low",
      "quality_status": "reviewed|draft|weak_evidence|conflicting"
    }
  ]
}
```

## 真实样例

见 `backend/app/fixtures/games/balatro.json`，可照着改游戏名复用。

## 导入流程

```bash
# 1) 起本地 Neo4j（首次）
cd backend && docker compose up -d neo4j

# 2) 起后端
cd backend && uvicorn app.main:app --reload

# 3) 导入某个游戏 JSON
curl -X POST http://localhost:8000/import/game \
  -H "Content-Type: application/json" \
  -d @path/to/your-game.json

# 4) 读回核对
curl http://localhost:8000/games/game_<slug>
```
````

- [ ] **Step 2: 人工核对**

确认指南包含：指令模板、JSON 骨架、样例指引、导入流程四部分，且枚举取值与 `common.py` 一致。

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/import-guide/game-import-prompt.md
git commit -m "docs: add Claude game-import JSON generation guide

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 完成校验

全部任务完成后：

- [ ] Run（`backend/`）：`pytest -v` — 全部非 integration 测试 PASS。
- [ ] （可选，需 Docker）Run：`docker compose up -d neo4j` 后 `$env:NEO4J_PASSWORD="devpassword"; pytest -m integration -v` — integration 测试 PASS。
- [ ] 现有 `test_fixture_pipeline.py` / `test_artifact_contracts.py` / `test_project_structure.py` 未被改动且仍 PASS。
- [ ] 手动走一遍 `docs/superpowers/import-guide/game-import-prompt.md` 的导入流程，确认 `POST /import/game` 与 `GET /games/{id}` 行为符合预期。
