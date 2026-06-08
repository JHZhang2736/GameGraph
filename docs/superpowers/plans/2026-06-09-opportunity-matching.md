# 6.5 Opportunity Matching Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 6.5 机会匹配模块——从设计知识图谱中确定性地枚举「锚点×变形」候选机会区域、计算稀缺度，再由 LLM 判断层做硬约束过滤、可行性判定与风险分档，最终通过 `POST /opportunity/match` 返回。

**Architecture:** 确定性图谱引擎产出有证据的候选（锚点游戏 + 一个维度变形 + 图谱稀缺度计数），LLM 判断层只在有界候选集上做判断（不发明、不判稀缺度）。纯枚举/排序逻辑与 Cypher 取数分离，便于无 Neo4j 单测；LLM 客户端仿 `profile_llm.py`、可选依赖、未配置则降级。

**Tech Stack:** Python 3.11、Pydantic v2、FastAPI、neo4j-python-driver、httpx、pytest。

设计依据：`docs/superpowers/specs/2026-06-09-opportunity-matching-design.zh-CN.md`。

---

## File Structure

- Create `backend/app/schemas/opportunity.py` — 所有 schema（Transformation / Candidate / OpportunityArea / 结果）。
- Create `backend/app/services/opportunity_service.py` — `GameDimensions`、纯枚举 `enumerate_candidates`、排序 `rank_candidates`、编排 `match_opportunities` + 降级/映射。
- Create `backend/app/graph/opportunity_repository.py` — 只读 Cypher 取 `GameDimensions`。
- Create `backend/app/services/opportunity_llm.py` — LLM 判断客户端（仿 `profile_llm.py`）。
- Create `backend/app/api/routes_opportunity.py` — 路由。
- Modify `backend/app/main.py` — 注册 router。
- Create `backend/tests/test_opportunity_schemas.py`、`test_opportunity_enumeration.py`、`test_opportunity_repository_integration.py`、`test_opportunity_llm.py`、`test_opportunity_service.py`、`test_opportunity_api.py`。

所有命令在 `backend/` 目录下运行（`pyproject.toml` 设了 `pythonpath=["."]`，集成测试默认被 `-m 'not integration'` 排除）。

---

## Task 1: Schemas

**Files:**
- Create: `backend/app/schemas/opportunity.py`
- Test: `backend/tests/test_opportunity_schemas.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_opportunity_schemas.py
import pytest
from pydantic import ValidationError

from app.schemas.opportunity import (
    CandidateOpportunityArea,
    OpportunityArea,
    OpportunityEvidence,
    OpportunityMatchResult,
    RejectedOpportunity,
    RiskPosture,
    Transformation,
    TransformationType,
)


def _candidate(**overrides) -> CandidateOpportunityArea:
    data = dict(
        id="opp_1",
        anchor_game_id="game_a",
        anchor_summary="一句话概括",
        transformation=Transformation(
            type=TransformationType.SUBSTITUTE,
            dimension="Perspective",
            from_value="横版2D",
            to_value="第一人称",
        ),
        novelty_count=0,
        evidence=OpportunityEvidence(
            anchor_game_id="game_a",
            target_value_game_ids=["game_b"],
            combination_game_ids=[],
        ),
    )
    data.update(overrides)
    return CandidateOpportunityArea(**data)


def test_candidate_round_trips() -> None:
    candidate = _candidate()
    dumped = candidate.model_dump_json()
    restored = CandidateOpportunityArea.model_validate_json(dumped)
    assert restored == candidate
    assert restored.transformation.type == TransformationType.SUBSTITUTE


def test_opportunity_area_extends_candidate_with_judgment_fields() -> None:
    area = OpportunityArea(
        **_candidate().model_dump(),
        risk_posture=RiskPosture.CHALLENGING,
        fit_reason="契合开发者对探索的偏好",
        risk_reason="3D 视角抬高美术成本",
    )
    assert area.risk_posture == RiskPosture.CHALLENGING
    assert area.anchor_game_id == "game_a"


def test_combine_transformation_allows_null_from_value() -> None:
    t = Transformation(
        type=TransformationType.COMBINE,
        dimension="Mechanic",
        from_value=None,
        to_value="护符定制",
    )
    assert t.from_value is None


def test_result_collects_areas_rejected_and_warnings() -> None:
    result = OpportunityMatchResult(
        profile_id="profile_1",
        areas=[
            OpportunityArea(
                **_candidate().model_dump(),
                risk_posture=RiskPosture.BALANCED,
                fit_reason="ok",
                risk_reason="ok",
            )
        ],
        rejected=[
            RejectedOpportunity(candidate_id="opp_2", rejection_reason="违反硬约束：不做联网多人")
        ],
        warnings=["匹配结果稀疏"],
    )
    assert result.areas[0].risk_posture == RiskPosture.BALANCED
    assert result.rejected[0].candidate_id == "opp_2"


def test_empty_fit_reason_is_rejected() -> None:
    with pytest.raises(ValidationError):
        OpportunityArea(
            **_candidate().model_dump(),
            risk_posture=RiskPosture.SAFE,
            fit_reason="",
            risk_reason="ok",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_opportunity_schemas.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.schemas.opportunity'`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/schemas/opportunity.py
from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from app.schemas.common import NonEmptyStr, StrictBaseModel


class TransformationType(StrEnum):
    SUBSTITUTE = "substitute"   # 替代：换一个维度值
    COMBINE = "combine"         # 组合：借入一个机制


class Transformation(StrictBaseModel):
    type: TransformationType
    dimension: str = Field(min_length=1)          # "Perspective"/"ArtStyle"/"Genre"/"Mechanic"
    from_value: str | None = Field(default=None, min_length=1)  # 替代=原值；组合=None
    to_value: str = Field(min_length=1)           # 替代=新值；组合=借入机制名


class OpportunityEvidence(StrictBaseModel):
    anchor_game_id: str = Field(min_length=1)
    target_value_game_ids: list[NonEmptyStr] = Field(min_length=1)
    combination_game_ids: list[NonEmptyStr] = Field(default_factory=list)


class CandidateOpportunityArea(StrictBaseModel):
    id: str = Field(min_length=1)
    anchor_game_id: str = Field(min_length=1)
    anchor_summary: str = Field(min_length=1)
    transformation: Transformation
    novelty_count: int = Field(ge=0)
    evidence: OpportunityEvidence


class RiskPosture(StrEnum):
    SAFE = "safe"            # 稳妥
    BALANCED = "balanced"   # 平衡
    CHALLENGING = "challenging"  # 挑战


class OpportunityArea(CandidateOpportunityArea):
    risk_posture: RiskPosture
    fit_reason: str = Field(min_length=1)
    risk_reason: str = Field(min_length=1)


class RejectedOpportunity(StrictBaseModel):
    candidate_id: str = Field(min_length=1)
    rejection_reason: str = Field(min_length=1)


class OpportunityMatchResult(StrictBaseModel):
    profile_id: str = Field(min_length=1)
    areas: list[OpportunityArea] = Field(default_factory=list)
    rejected: list[RejectedOpportunity] = Field(default_factory=list)
    warnings: list[NonEmptyStr] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_opportunity_schemas.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/opportunity.py backend/tests/test_opportunity_schemas.py
git commit -m "feat: add opportunity matching schemas"
```

---

## Task 2: Deterministic enumeration

`GameDimensions` 是引擎的纯输入（每款游戏在 4 个维度上的取值），`enumerate_candidates` 是纯函数，无需 Neo4j 即可单测。

**Files:**
- Modify: `backend/app/services/opportunity_service.py` (create)
- Test: `backend/tests/test_opportunity_enumeration.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_opportunity_enumeration.py
from app.schemas.opportunity import TransformationType
from app.services.opportunity_service import GameDimensions, enumerate_candidates


def _games() -> list[GameDimensions]:
    return [
        GameDimensions(
            game_id="game_vs",
            summary="横版割草幸存者",
            genres={"类肉鸽"},
            perspectives={"横版2D"},
            art_styles={"像素美术"},
            mechanics={"护符定制"},
        ),
        GameDimensions(
            game_id="game_fps",
            summary="第一人称射击",
            genres={"射击"},
            perspectives={"第一人称"},
            art_styles={"低多边形"},
            mechanics={"能力树"},
        ),
    ]


def test_substitute_borrows_target_value_from_other_game() -> None:
    candidates = enumerate_candidates(_games())
    subs = [
        c for c in candidates
        if c.anchor_game_id == "game_vs"
        and c.transformation.type == TransformationType.SUBSTITUTE
        and c.transformation.dimension == "Perspective"
    ]
    assert any(c.transformation.to_value == "第一人称" for c in subs)
    picked = next(c for c in subs if c.transformation.to_value == "第一人称")
    assert picked.transformation.from_value == "横版2D"
    assert picked.evidence.target_value_game_ids == ["game_fps"]
    # 锚点(类肉鸽) + 第一人称 这个组合在图谱里不存在
    assert picked.novelty_count == 0
    assert picked.evidence.combination_game_ids == []


def test_combine_borrows_mechanic_anchor_lacks() -> None:
    candidates = enumerate_candidates(_games())
    combines = [
        c for c in candidates
        if c.anchor_game_id == "game_vs"
        and c.transformation.type == TransformationType.COMBINE
    ]
    assert any(c.transformation.to_value == "能力树" for c in combines)
    picked = next(c for c in combines if c.transformation.to_value == "能力树")
    assert picked.transformation.from_value is None
    assert picked.transformation.dimension == "Mechanic"
    assert picked.evidence.target_value_game_ids == ["game_fps"]


def test_no_candidate_for_value_anchor_already_has() -> None:
    candidates = enumerate_candidates(_games())
    # game_vs 已有 像素美术，不应对自身 ArtStyle 生成 像素美术 候选
    assert not any(
        c.anchor_game_id == "game_vs"
        and c.transformation.dimension == "ArtStyle"
        and c.transformation.to_value == "像素美术"
        for c in candidates
    )


def test_novelty_count_counts_genre_sharing_games_with_target_value() -> None:
    games = [
        GameDimensions("g1", "s1", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, set()),
        GameDimensions("g2", "s2", {"类肉鸽"}, {"第一人称"}, {"低多边形"}, set()),
        GameDimensions("g3", "s3", {"类肉鸽"}, {"第一人称"}, {"低多边形"}, set()),
    ]
    candidates = enumerate_candidates(games)
    # 锚点 g1(类肉鸽) 替代视角为 第一人称：g2、g3 都是类肉鸽且第一人称 → 组合已存在 2 次
    picked = next(
        c for c in candidates
        if c.anchor_game_id == "g1"
        and c.transformation.dimension == "Perspective"
        and c.transformation.to_value == "第一人称"
    )
    assert picked.novelty_count == 2
    assert set(picked.evidence.combination_game_ids) == {"g2", "g3"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_opportunity_enumeration.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.opportunity_service'`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/opportunity_service.py
from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.opportunity import (
    CandidateOpportunityArea,
    OpportunityEvidence,
    Transformation,
    TransformationType,
)

# 替代作用的维度 label -> GameDimensions 属性名
_SUBSTITUTE_DIMENSIONS: dict[str, str] = {
    "Perspective": "perspectives",
    "ArtStyle": "art_styles",
    "Genre": "genres",
}


@dataclass
class GameDimensions:
    game_id: str
    summary: str
    genres: set[str] = field(default_factory=set)
    perspectives: set[str] = field(default_factory=set)
    art_styles: set[str] = field(default_factory=set)
    mechanics: set[str] = field(default_factory=set)


def _candidate_id(anchor: str, kind: str, dimension: str, to_value: str) -> str:
    return f"opp_{anchor}_{kind}_{dimension}_{to_value}"


def _games_with_value(games: list[GameDimensions], attr: str, value: str) -> list[str]:
    return sorted(g.game_id for g in games if value in getattr(g, attr))


def _combination_game_ids(
    games: list[GameDimensions], anchor: GameDimensions, attr: str, value: str
) -> list[str]:
    return sorted(
        g.game_id
        for g in games
        if value in getattr(g, attr) and (g.genres & anchor.genres)
    )


def enumerate_candidates(games: list[GameDimensions]) -> list[CandidateOpportunityArea]:
    candidates: list[CandidateOpportunityArea] = []
    for anchor in games:
        candidates.extend(_substitute_candidates(games, anchor))
        candidates.extend(_combine_candidates(games, anchor))
    return candidates


def _substitute_candidates(
    games: list[GameDimensions], anchor: GameDimensions
) -> list[CandidateOpportunityArea]:
    out: list[CandidateOpportunityArea] = []
    for dimension, attr in _SUBSTITUTE_DIMENSIONS.items():
        anchor_values = getattr(anchor, attr)
        all_values = {v for g in games for v in getattr(g, attr)}
        from_value = sorted(anchor_values)[0] if anchor_values else None
        for target in sorted(all_values - anchor_values):
            target_games = _games_with_value(games, attr, target)
            combo = _combination_game_ids(games, anchor, attr, target)
            out.append(
                CandidateOpportunityArea(
                    id=_candidate_id(anchor.game_id, "sub", dimension, target),
                    anchor_game_id=anchor.game_id,
                    anchor_summary=anchor.summary,
                    transformation=Transformation(
                        type=TransformationType.SUBSTITUTE,
                        dimension=dimension,
                        from_value=from_value,
                        to_value=target,
                    ),
                    novelty_count=len(combo),
                    evidence=OpportunityEvidence(
                        anchor_game_id=anchor.game_id,
                        target_value_game_ids=target_games,
                        combination_game_ids=combo,
                    ),
                )
            )
    return out


def _combine_candidates(
    games: list[GameDimensions], anchor: GameDimensions
) -> list[CandidateOpportunityArea]:
    out: list[CandidateOpportunityArea] = []
    all_mechanics = {m for g in games for m in g.mechanics}
    for target in sorted(all_mechanics - anchor.mechanics):
        target_games = _games_with_value(games, "mechanics", target)
        combo = _combination_game_ids(games, anchor, "mechanics", target)
        out.append(
            CandidateOpportunityArea(
                id=_candidate_id(anchor.game_id, "comb", "Mechanic", target),
                anchor_game_id=anchor.game_id,
                anchor_summary=anchor.summary,
                transformation=Transformation(
                    type=TransformationType.COMBINE,
                    dimension="Mechanic",
                    from_value=None,
                    to_value=target,
                ),
                novelty_count=len(combo),
                evidence=OpportunityEvidence(
                    anchor_game_id=anchor.game_id,
                    target_value_game_ids=target_games,
                    combination_game_ids=combo,
                ),
            )
        )
    return out
```

注：`OpportunityEvidence.target_value_game_ids` 要求非空（min_length=1）。本枚举中 `target`/机制都来自语料里某款游戏，故 `target_games` 恒非空，约束自然满足。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_opportunity_enumeration.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/opportunity_service.py backend/tests/test_opportunity_enumeration.py
git commit -m "feat: enumerate anchor-by-transformation opportunity candidates"
```

---

## Task 3: Ranking + validity threshold + top-N

**Files:**
- Modify: `backend/app/services/opportunity_service.py`
- Test: `backend/tests/test_opportunity_enumeration.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_opportunity_enumeration.py
from app.schemas.opportunity import (
    CandidateOpportunityArea,
    OpportunityEvidence,
    Transformation,
    TransformationType,
)
from app.services.opportunity_service import rank_candidates


def _cand(cid: str, novelty: int, target_count: int) -> CandidateOpportunityArea:
    return CandidateOpportunityArea(
        id=cid,
        anchor_game_id="a",
        anchor_summary="s",
        transformation=Transformation(
            type=TransformationType.COMBINE,
            dimension="Mechanic",
            from_value=None,
            to_value=cid,
        ),
        novelty_count=novelty,
        evidence=OpportunityEvidence(
            anchor_game_id="a",
            target_value_game_ids=[f"g{i}" for i in range(target_count)] or ["g0"],
            combination_game_ids=[f"c{i}" for i in range(novelty)],
        ),
    )


def test_rank_filters_out_candidates_above_novelty_ceiling() -> None:
    ranked = rank_candidates(
        [_cand("keep", 1, 2), _cand("drop", 5, 2)], novelty_ceiling=2, top_n=10
    )
    ids = [c.id for c in ranked]
    assert "keep" in ids
    assert "drop" not in ids


def test_rank_sorts_by_novelty_then_target_attestation() -> None:
    ranked = rank_candidates(
        [
            _cand("novel_weak", 0, 1),
            _cand("novel_strong", 0, 3),
            _cand("less_novel", 1, 5),
        ],
        novelty_ceiling=2,
        top_n=10,
    )
    assert [c.id for c in ranked] == ["novel_strong", "novel_weak", "less_novel"]


def test_rank_truncates_to_top_n() -> None:
    ranked = rank_candidates(
        [_cand(f"c{i}", 0, 1) for i in range(40)], novelty_ceiling=2, top_n=30
    )
    assert len(ranked) == 30
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_opportunity_enumeration.py -q`
Expected: FAIL with `ImportError: cannot import name 'rank_candidates'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to backend/app/services/opportunity_service.py
NOVELTY_CEILING = 2   # 组合现存次数超过该阈值视为不够稀缺，丢弃
TOP_N = 30            # 送 LLM 判断的最大候选数


def rank_candidates(
    candidates: list[CandidateOpportunityArea],
    novelty_ceiling: int = NOVELTY_CEILING,
    top_n: int = TOP_N,
) -> list[CandidateOpportunityArea]:
    viable = [c for c in candidates if c.novelty_count <= novelty_ceiling]
    viable.sort(
        key=lambda c: (c.novelty_count, -len(c.evidence.target_value_game_ids), c.id)
    )
    return viable[:top_n]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_opportunity_enumeration.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/opportunity_service.py backend/tests/test_opportunity_enumeration.py
git commit -m "feat: rank and threshold opportunity candidates by novelty"
```

---

## Task 4: Graph repository (Cypher → GameDimensions)

**Files:**
- Create: `backend/app/graph/opportunity_repository.py`
- Test: `backend/tests/test_opportunity_repository_integration.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_opportunity_repository_integration.py
import json
import os
from pathlib import Path

import pytest

from app.graph.connection import Neo4jSettings, create_driver
from app.graph.game_repository import GameRepository
from app.graph.opportunity_repository import OpportunityRepository
from app.schemas.import_document import GameImportDocument

pytestmark = pytest.mark.integration


def _document(name: str) -> GameImportDocument:
    path = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "games" / f"{name}.json"
    return GameImportDocument.model_validate(json.loads(path.read_text(encoding="utf-8")))


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
    with drv.session() as session:
        session.run("MATCH (g:Game {id: $id}) DETACH DELETE g", id="game_animal_well")
    drv.close()


def test_fetch_game_dimensions_returns_anchor_values(driver) -> None:
    GameRepository(driver).upsert_game(_document("animal_well"))
    rows = OpportunityRepository(driver).fetch_game_dimensions()
    aw = next(r for r in rows if r.game_id == "game_animal_well")
    assert aw.summary
    assert aw.genres   # 非空
    assert isinstance(aw.mechanics, set)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_opportunity_repository_integration.py -q -m integration`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.graph.opportunity_repository'`（若本机无 Neo4j 则 SKIP——仍说明模块缺失，先建模块再说）。

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/graph/opportunity_repository.py
from __future__ import annotations

from neo4j import Driver

from app.services.opportunity_service import GameDimensions

_FETCH_QUERY = """
MATCH (g:Game)
RETURN g.id AS game_id,
       coalesce(g.one_sentence_summary, '') AS summary,
       [(g)-[:HAS_GENRE]->(x) | x.name] AS genres,
       [(g)-[:HAS_PERSPECTIVE]->(x) | x.name] AS perspectives,
       [(g)-[:HAS_ART_STYLE]->(x) | x.name] AS art_styles,
       [(g)-[:HAS_MECHANIC]->(x) | x.name] AS mechanics
"""


class OpportunityRepository:
    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def fetch_game_dimensions(self) -> list[GameDimensions]:
        with self._driver.session() as session:
            return session.execute_read(self._read_dimensions)

    @staticmethod
    def _read_dimensions(tx) -> list[GameDimensions]:
        result = tx.run(_FETCH_QUERY)
        return [
            GameDimensions(
                game_id=record["game_id"],
                summary=record["summary"],
                genres=set(record["genres"]),
                perspectives=set(record["perspectives"]),
                art_styles=set(record["art_styles"]),
                mechanics=set(record["mechanics"]),
            )
            for record in result
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_opportunity_repository_integration.py -q -m integration`
Expected: PASS if Neo4j 可达（设置 `NEO4J_PASSWORD` 并 `docker compose up` 起库后入库 fixture）；否则 SKIP。无 Neo4j 时该任务以「模块可导入 + 默认套件不回归」为准：`python -m pytest -q` 应仍全绿。

- [ ] **Step 5: Commit**

```bash
git add backend/app/graph/opportunity_repository.py backend/tests/test_opportunity_repository_integration.py
git commit -m "feat: read game design dimensions from graph for matching"
```

---

## Task 5: LLM judgment client

仿 `app/services/profile_llm.py`：OpenAI 兼容 tool-calling、env 配置、`get_opportunity_llm_client()` 未配置返回 `None`。

**Files:**
- Create: `backend/app/services/opportunity_llm.py`
- Test: `backend/tests/test_opportunity_llm.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_opportunity_llm.py
import json

import httpx
import pytest

from app.schemas.opportunity import (
    CandidateOpportunityArea,
    OpportunityEvidence,
    Transformation,
    TransformationType,
)
from app.schemas.artifacts import DeveloperConstraint, DeveloperProfile
from app.schemas.common import ConstraintType
from app.services.opportunity_llm import (
    LlmSettings,
    OpportunityJudgmentBatch,
    OpportunityLlmClient,
    build_tool_schema,
    get_opportunity_llm_client,
)


def _settings() -> LlmSettings:
    return LlmSettings(base_url="https://example.test/v1", api_key="secret", model="m", timeout=5.0)


def _profile() -> DeveloperProfile:
    return DeveloperProfile(
        id="profile_1",
        team_size="solo",
        time_budget="三个月",
        programming_ability="强",
        art_ability="弱",
        audio_ability="弱",
        content_production_ability="有限",
        liked_references=["Hades"],
        disliked_references_or_mechanics=["联网多人"],
        desired_player_experiences=["短局"],
        constraints=[
            DeveloperConstraint(id="c1", type=ConstraintType.HARD, statement="不做联网多人")
        ],
    )


def _candidate() -> CandidateOpportunityArea:
    return CandidateOpportunityArea(
        id="opp_1",
        anchor_game_id="game_vs",
        anchor_summary="横版割草",
        transformation=Transformation(
            type=TransformationType.SUBSTITUTE,
            dimension="Perspective",
            from_value="横版2D",
            to_value="第一人称",
        ),
        novelty_count=0,
        evidence=OpportunityEvidence(
            anchor_game_id="game_vs", target_value_game_ids=["game_fps"], combination_game_ids=[]
        ),
    )


def _arguments() -> str:
    return json.dumps(
        {
            "judgments": [
                {
                    "candidate_id": "opp_1",
                    "decision": "keep",
                    "risk_posture": "challenging",
                    "fit_reason": "契合短局快节奏",
                    "risk_reason": "3D 抬高美术成本",
                }
            ],
            "warnings": [],
        }
    )


def test_build_tool_schema_exposes_function_name() -> None:
    tools = build_tool_schema()
    assert tools[0]["function"]["name"] == "emit_opportunity_judgments"
    assert "parameters" in tools[0]["function"]


def test_judge_posts_request_and_parses_batch() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"tool_calls": [
                        {"function": {"name": "emit_opportunity_judgments", "arguments": _arguments()}}
                    ]}}
                ]
            },
        )

    client = OpportunityLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    batch = client.judge(_profile(), [_candidate()])

    assert isinstance(batch, OpportunityJudgmentBatch)
    assert batch.judgments[0].candidate_id == "opp_1"
    assert batch.judgments[0].decision == "keep"
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["body"]["tool_choice"]["function"]["name"] == "emit_opportunity_judgments"


def test_judge_raises_when_no_tool_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    client = OpportunityLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError, match="tool_call"):
        client.judge(_profile(), [_candidate()])


def test_get_client_returns_none_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    assert get_opportunity_llm_client() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_opportunity_llm.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.opportunity_llm'`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/opportunity_llm.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import ConfigDict, Field

from app.schemas.artifacts import DeveloperProfile
from app.schemas.common import StrictBaseModel
from app.schemas.opportunity import CandidateOpportunityArea, RiskPosture

TOOL_NAME = "emit_opportunity_judgments"

SYSTEM_PROMPT = (
    "你是独立游戏创意系统的机会匹配判断器。"
    "给你开发者画像和一组『锚点×变形』候选机会区域（每个含图谱证据与稀缺度）。"
    "对每个候选给出判断：尊重硬约束(hard)，违反者 decision=reject 并说明；"
    "强偏好(strong_preference)可保留但 risk_posture=challenging 并在 risk_reason 写明警告；"
    "看似新颖但不自洽/做不出的候选 decision=reject 并说明为何行不通；"
    "尽量让保留的候选覆盖稳妥/平衡/挑战多种风险姿态。"
    "你不得修改候选的锚点、变形或稀缺度，只做判断。"
)


@dataclass(frozen=True)
class LlmSettings:
    base_url: str
    api_key: str
    model: str
    timeout: float

    @classmethod
    def from_env(cls) -> "LlmSettings":
        return cls(
            base_url=os.environ.get("LLM_BASE_URL", "").strip(),
            api_key=os.environ.get("LLM_API_KEY", "").strip(),
            model=os.environ.get("LLM_MODEL", "").strip(),
            timeout=float(os.environ.get("LLM_TIMEOUT", "30")),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)


class OpportunityJudgment(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")

    candidate_id: str = Field(min_length=1)
    decision: Literal["keep", "reject"]
    risk_posture: RiskPosture | None = None
    fit_reason: str | None = None
    risk_reason: str | None = None
    rejection_reason: str | None = None


class OpportunityJudgmentBatch(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")

    judgments: list[OpportunityJudgment] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def build_tool_schema() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": "Return keep/reject judgments for the supplied opportunity candidates.",
                "parameters": OpportunityJudgmentBatch.model_json_schema(),
            },
        }
    ]


def _profile_block(profile: DeveloperProfile) -> str:
    lines = [
        f"团队:{profile.team_size} 时间:{profile.time_budget}",
        f"能力 程序:{profile.programming_ability} 美术:{profile.art_ability} "
        f"音频:{profile.audio_ability} 内容:{profile.content_production_ability}",
        f"喜欢:{', '.join(profile.liked_references)}",
        f"讨厌:{', '.join(profile.disliked_references_or_mechanics)}",
        f"期望体验:{', '.join(profile.desired_player_experiences)}",
        "约束:",
    ]
    for c in profile.constraints:
        lines.append(f"  - [{c.type.value}] {c.statement}")
    return "\n".join(lines)


def _candidate_block(candidates: list[CandidateOpportunityArea]) -> str:
    out = []
    for c in candidates:
        t = c.transformation
        change = f"{t.from_value}->{t.to_value}" if t.from_value else f"+{t.to_value}"
        out.append(
            f"[{c.id}] 锚点={c.anchor_summary} 变形={t.type.value}:{t.dimension}({change}) "
            f"稀缺度={c.novelty_count}"
        )
    return "\n".join(out)


class OpportunityLlmClient:
    def __init__(self, settings: LlmSettings, http_client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout)

    def judge(
        self, profile: DeveloperProfile, candidates: list[CandidateOpportunityArea]
    ) -> OpportunityJudgmentBatch:
        user = f"开发者画像：\n{_profile_block(profile)}\n\n候选机会：\n{_candidate_block(candidates)}"
        payload = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            "tools": build_tool_schema(),
            "tool_choice": {"type": "function", "function": {"name": TOOL_NAME}},
        }
        response = self._client.post(
            f"{self._settings.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self._settings.api_key}"},
            json=payload,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise ValueError(
                f"LLM request failed with {error.response.status_code}: {error.response.text}"
            ) from error
        data = response.json()
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError(f"Unexpected LLM response shape: {data}") from error
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            raise ValueError("LLM response missing tool_call")
        return OpportunityJudgmentBatch.model_validate_json(tool_calls[0]["function"]["arguments"])


def get_opportunity_llm_client() -> OpportunityLlmClient | None:
    settings = LlmSettings.from_env()
    if not settings.is_configured:
        return None
    return OpportunityLlmClient(settings)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_opportunity_llm.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/opportunity_llm.py backend/tests/test_opportunity_llm.py
git commit -m "feat: add opportunity judgment LLM client"
```

---

## Task 6: Orchestrator (match + fallback + judgment mapping + sparse warning)

`match_opportunities` 串起取数→枚举→排序→LLM 判断→映射结果；定义 repo/llm 的 `Protocol` 便于 stub 单测。

**Files:**
- Modify: `backend/app/services/opportunity_service.py`
- Test: `backend/tests/test_opportunity_service.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_opportunity_service.py
from app.schemas.artifacts import DeveloperConstraint, DeveloperProfile
from app.schemas.common import ConstraintType
from app.schemas.opportunity import CandidateOpportunityArea, RiskPosture
from app.services.opportunity_llm import OpportunityJudgment, OpportunityJudgmentBatch
from app.services.opportunity_service import GameDimensions, match_opportunities


class StubRepo:
    def __init__(self, games: list[GameDimensions]) -> None:
        self._games = games

    def fetch_game_dimensions(self) -> list[GameDimensions]:
        return self._games


class StubLlm:
    def __init__(self, batch: OpportunityJudgmentBatch) -> None:
        self._batch = batch
        self.seen: list[CandidateOpportunityArea] = []

    def judge(self, profile, candidates):
        self.seen = candidates
        return self._batch


def _profile() -> DeveloperProfile:
    return DeveloperProfile(
        id="profile_1", team_size="solo", time_budget="三个月",
        programming_ability="强", art_ability="弱", audio_ability="弱",
        content_production_ability="有限", liked_references=["Hades"],
        disliked_references_or_mechanics=["联网多人"], desired_player_experiences=["短局"],
        constraints=[DeveloperConstraint(id="c1", type=ConstraintType.HARD, statement="不做联网多人")],
    )


def _games() -> list[GameDimensions]:
    return [
        GameDimensions("game_vs", "横版割草", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, {"护符定制"}),
        GameDimensions("game_fps", "第一人称射击", {"射击"}, {"第一人称"}, {"低多边形"}, {"能力树"}),
    ]


def test_match_keeps_and_rejects_per_judgment() -> None:
    repo = StubRepo(_games())
    # 对全部候选给判断：第一个 reject，其余 keep（避免未判定候选混入断言）
    from app.services.opportunity_service import enumerate_candidates, rank_candidates
    ranked = rank_candidates(enumerate_candidates(_games()))
    reject_id = ranked[0].id
    judgments = [
        OpportunityJudgment(candidate_id=reject_id, decision="reject",
                            rejection_reason="违反硬约束：不做联网多人")
    ]
    for c in ranked[1:]:
        judgments.append(
            OpportunityJudgment(candidate_id=c.id, decision="keep",
                                risk_posture=RiskPosture.BALANCED,
                                fit_reason="契合", risk_reason="可控")
        )
    batch = OpportunityJudgmentBatch(judgments=judgments, warnings=[])
    result = match_opportunities(_profile(), repo, StubLlm(batch))
    assert result.profile_id == "profile_1"
    assert [r.candidate_id for r in result.rejected] == [reject_id]
    area_ids = [a.id for a in result.areas]
    assert reject_id not in area_ids
    assert all(a.risk_posture == RiskPosture.BALANCED for a in result.areas)
    assert area_ids  # 其余候选都保留为机会区域


def test_match_without_llm_returns_balanced_areas_with_warning() -> None:
    result = match_opportunities(_profile(), StubRepo(_games()), None)
    assert result.areas
    assert all(a.risk_posture == RiskPosture.BALANCED for a in result.areas)
    assert any("未配置 LLM" in w for w in result.warnings)
    assert result.rejected == []


def test_match_warns_on_sparse_result() -> None:
    # 单游戏 → 几乎无候选，触发稀疏警告
    repo = StubRepo([GameDimensions("g1", "s", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, set())])
    result = match_opportunities(_profile(), repo, None)
    assert any("稀疏" in w for w in result.warnings)


def test_unjudged_candidate_is_kept_balanced_with_warning() -> None:
    repo = StubRepo(_games())
    batch = OpportunityJudgmentBatch(judgments=[], warnings=[])  # LLM 什么都没判
    result = match_opportunities(_profile(), repo, StubLlm(batch))
    assert result.areas  # 候选未被静默丢弃
    assert all(a.risk_posture == RiskPosture.BALANCED for a in result.areas)
    assert any("未判定" in w for w in result.warnings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_opportunity_service.py -q`
Expected: FAIL with `ImportError: cannot import name 'match_opportunities'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to backend/app/services/opportunity_service.py
import logging
from typing import Protocol

from app.schemas.artifacts import DeveloperProfile
from app.schemas.opportunity import (
    OpportunityArea,
    OpportunityMatchResult,
    RejectedOpportunity,
    RiskPosture,
)

logger = logging.getLogger(__name__)

SPARSE_AREA_THRESHOLD = 3
_NO_LLM_WARNING = "未配置 LLM，未做约束过滤与可行性判定。"


class SupportsGameDimensions(Protocol):
    def fetch_game_dimensions(self) -> list[GameDimensions]: ...


class SupportsOpportunityJudgment(Protocol):
    def judge(self, profile: DeveloperProfile, candidates): ...


def _area_from_candidate(
    candidate: CandidateOpportunityArea,
    posture: RiskPosture,
    fit_reason: str,
    risk_reason: str,
) -> OpportunityArea:
    return OpportunityArea(
        **candidate.model_dump(),
        risk_posture=posture,
        fit_reason=fit_reason,
        risk_reason=risk_reason,
    )


def _fallback_result(
    profile_id: str, candidates: list[CandidateOpportunityArea], warnings: list[str]
) -> OpportunityMatchResult:
    areas = [
        _area_from_candidate(c, RiskPosture.BALANCED, _NO_LLM_WARNING, _NO_LLM_WARNING)
        for c in candidates
    ]
    return _finalize(profile_id, areas, [], [_NO_LLM_WARNING, *warnings])


def _finalize(
    profile_id: str,
    areas: list[OpportunityArea],
    rejected: list[RejectedOpportunity],
    warnings: list[str],
) -> OpportunityMatchResult:
    final_warnings = list(warnings)
    if len(areas) < SPARSE_AREA_THRESHOLD:
        final_warnings.append(
            "匹配结果稀疏：当前图谱规模或约束压窄了可用机会，可继续入库更多游戏以拓宽。"
        )
    return OpportunityMatchResult(
        profile_id=profile_id, areas=areas, rejected=rejected, warnings=final_warnings
    )


def match_opportunities(
    profile: DeveloperProfile,
    repository: SupportsGameDimensions,
    llm_client: SupportsOpportunityJudgment | None,
) -> OpportunityMatchResult:
    games = repository.fetch_game_dimensions()
    candidates = rank_candidates(enumerate_candidates(games))

    if llm_client is None:
        return _fallback_result(profile.id, candidates, [])

    try:
        batch = llm_client.judge(profile, candidates)
    except Exception:
        logger.warning("Opportunity LLM judge failed; falling back", exc_info=True)
        return _fallback_result(profile.id, candidates, ["LLM 判断失败，已降级。"])

    by_id = {j.candidate_id: j for j in batch.judgments}
    areas: list[OpportunityArea] = []
    rejected: list[RejectedOpportunity] = []
    warnings = list(batch.warnings)
    unjudged: list[str] = []

    for candidate in candidates:
        judgment = by_id.get(candidate.id)
        if judgment is None:
            unjudged.append(candidate.id)
            areas.append(
                _area_from_candidate(
                    candidate, RiskPosture.BALANCED, "LLM 未判定，默认保留。", "未判定。"
                )
            )
        elif judgment.decision == "reject":
            rejected.append(
                RejectedOpportunity(
                    candidate_id=candidate.id,
                    rejection_reason=judgment.rejection_reason or "未说明拒绝理由。",
                )
            )
        else:
            areas.append(
                _area_from_candidate(
                    candidate,
                    judgment.risk_posture or RiskPosture.BALANCED,
                    judgment.fit_reason or "LLM 未给出适配理由。",
                    judgment.risk_reason or "LLM 未给出风险说明。",
                )
            )

    if unjudged:
        warnings.append(f"以下候选未被 LLM 判定，已默认保留：{', '.join(unjudged)}")
    return _finalize(profile.id, areas, rejected, warnings)
```

注：Task 2/3 已在文件顶部定义 `enumerate_candidates` / `rank_candidates` / `CandidateOpportunityArea` 导入；本段新增的 imports 追加到文件已有 import 区即可（避免重复导入 `CandidateOpportunityArea` 等已导入名）。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_opportunity_service.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/opportunity_service.py backend/tests/test_opportunity_service.py
git commit -m "feat: orchestrate opportunity matching with LLM judgment and fallback"
```

---

## Task 7: API route + registration

**Files:**
- Create: `backend/app/api/routes_opportunity.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_opportunity_api.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_opportunity_api.py
from fastapi.testclient import TestClient

from app.api.routes_opportunity import get_opportunity_repository, get_opportunity_llm
from app.main import app
from app.schemas.opportunity import RiskPosture
from app.services.opportunity_llm import OpportunityJudgment, OpportunityJudgmentBatch
from app.services.opportunity_service import GameDimensions


class StubRepo:
    def fetch_game_dimensions(self) -> list[GameDimensions]:
        return [
            GameDimensions("game_vs", "横版割草", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, {"护符定制"}),
            GameDimensions("game_fps", "第一人称射击", {"射击"}, {"第一人称"}, {"低多边形"}, {"能力树"}),
        ]


class StubLlm:
    def judge(self, profile, candidates):
        return OpportunityJudgmentBatch(
            judgments=[
                OpportunityJudgment(
                    candidate_id=candidates[0].id, decision="keep",
                    risk_posture=RiskPosture.BALANCED, fit_reason="契合", risk_reason="可控",
                )
            ],
            warnings=[],
        )


def _profile_payload() -> dict:
    return {
        "id": "profile_1", "team_size": "solo", "time_budget": "三个月",
        "programming_ability": "强", "art_ability": "弱", "audio_ability": "弱",
        "content_production_ability": "有限", "liked_references": ["Hades"],
        "disliked_references_or_mechanics": ["联网多人"], "desired_player_experiences": ["短局"],
        "constraints": [{"id": "c1", "type": "hard", "statement": "不做联网多人"}],
    }


def test_match_endpoint_returns_areas() -> None:
    app.dependency_overrides[get_opportunity_repository] = lambda: StubRepo()
    app.dependency_overrides[get_opportunity_llm] = lambda: StubLlm()
    try:
        client = TestClient(app)
        response = client.post("/opportunity/match", json=_profile_payload())
        assert response.status_code == 200
        body = response.json()
        assert body["profile_id"] == "profile_1"
        assert len(body["areas"]) >= 1
        assert body["areas"][0]["risk_posture"] == "balanced"
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_opportunity_api.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.api.routes_opportunity'`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/api/routes_opportunity.py
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.graph.connection import create_driver
from app.graph.opportunity_repository import OpportunityRepository
from app.schemas.artifacts import DeveloperProfile
from app.schemas.opportunity import OpportunityMatchResult
from app.services.opportunity_llm import (
    OpportunityLlmClient,
    get_opportunity_llm_client,
)
from app.services.opportunity_service import match_opportunities

router = APIRouter()

_driver = None


def get_opportunity_repository() -> OpportunityRepository:
    global _driver
    if _driver is None:
        _driver = create_driver()
    return OpportunityRepository(_driver)


def get_opportunity_llm() -> OpportunityLlmClient | None:
    return get_opportunity_llm_client()


@router.post("/opportunity/match", response_model=OpportunityMatchResult)
def match_endpoint(
    profile: DeveloperProfile,
    repository: OpportunityRepository = Depends(get_opportunity_repository),
    llm_client: OpportunityLlmClient | None = Depends(get_opportunity_llm),
) -> OpportunityMatchResult:
    return match_opportunities(profile, repository, llm_client)
```

```python
# backend/app/main.py — 增加注册（在已有 include_router 之后）
from app.api.routes_opportunity import router as opportunity_router
app.include_router(opportunity_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_opportunity_api.py -q`
Expected: PASS (1 passed)。

- [ ] **Step 5: Run full suite + commit**

Run: `python -m pytest -q`
Expected: 全绿（既有 96 + 新增；集成测试默认 deselected）。

```bash
git add backend/app/api/routes_opportunity.py backend/app/main.py backend/tests/test_opportunity_api.py
git commit -m "feat: expose POST /opportunity/match endpoint"
```

---

## Self-Review 结论（写计划时已核对）

- **Spec 覆盖**：§2 锚点×变形→Task2；§3.2 可行性闸/死区→Task5 system prompt + Task6 reject 映射；§5 schema→Task1；§6 枚举+稀缺度+排序→Task2/3；Cypher 取数→Task4；§7 LLM 判断+降级→Task5/6；§8 API→Task7；§9 测试逐条对应（硬约束剔除/强偏好挑战型/稀疏警告/适配理由必填/拒绝可解释）。
- **类型一致**：`GameDimensions`、`CandidateOpportunityArea`、`OpportunityJudgmentBatch`、`match_opportunities`、`fetch_game_dimensions`、`judge` 在各 Task 间签名一致；依赖注入函数名 `get_opportunity_repository`/`get_opportunity_llm` 在 Task7 测试与实现一致。
- **无占位符**：每个代码步骤均为完整可运行代码。
- **已知局限**（spec §11）：小库下稀疏警告会频繁触发——这是预期行为，非缺陷。
