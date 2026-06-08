# 6.6 机会框架模块 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把单个被选中的 `OpportunityArea`(6.5 产物)深挖成一个完整、可独立阅读的 `OpportunityFrame`(创意简报),作为 6.7 概念生成的输入。

**Architecture:** 沿用 6.5 的「确定性引擎 + LLM 综合层」两层。确定性引擎按 area 的 anchor + 证据游戏查图谱拿 `related_*`、复用 6.5 枚举产「同证据次变形池」、组装证据闭包/evidence_path/硬约束禁止基底;LLM 只做叙述综合(主题标签、次变形挑选叙述、dead-zone 禁止、fit/risk 理由),且 `recommended_transformations[0]` 由服务确定性置为主变形。未配置/失败 LLM 时降级为确定性证据组装(沿用 area 自带 fit/risk 理由)。

**Tech Stack:** Python 3.12 / FastAPI / Pydantic v2(`StrictBaseModel`)/ Neo4j Python driver / httpx(OpenAI 兼容 tool-calling)/ pytest。

**Spec:** `docs/superpowers/specs/2026-06-09-opportunity-frame-design.zh-CN.md`

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `backend/app/schemas/artifacts.py` | `OpportunityFrame` 加可选 `warnings` 字段 | Modify |
| `backend/app/services/opportunity_service.py` | 新增 `GameDesignFacts` 数据类(与 `GameDimensions` 同处) | Modify |
| `backend/app/graph/opportunity_repository.py` | 新增 `fetch_game_design_facts(game_ids)` 只读图查询 | Modify |
| `backend/app/services/opportunity_frame_llm.py` | `FrameInputs` / `FrameSynthesis` / `OpportunityFrameLlmClient` / `get_opportunity_frame_llm_client`(仿 `opportunity_llm`) | Create |
| `backend/app/services/opportunity_frame_service.py` | 确定性组装 + `build_frame` 编排 + 降级 | Create |
| `backend/app/api/routes_opportunity.py` | `OpportunityFrameRequest` + `POST /opportunity/frame` + LLM provider | Modify |
| `backend/tests/test_opportunity_frame_service.py` | 确定性 helper + `build_frame` 单测(stub repo/llm) | Create |
| `backend/tests/test_opportunity_frame_llm.py` | LLM 客户端 `MockTransport` 行为测试 | Create |
| `backend/tests/test_opportunity_frame_api.py` | 契约往返 + 422 + 降级端到端 | Create |
| `backend/tests/test_opportunity_repository_integration.py` | `fetch_game_design_facts` 集成测试 | Modify |

**关键不变量(实现可依赖):** 任何已导入的 Game 节点,因 `GameDesignProfile` 的 `main_mechanics / main_player_experiences / production_constraints / innovation_patterns` 均 `min_length=1`,故必有 ≥1 条 `HAS_MECHANIC / DELIVERS_EXPERIENCE / CONSTRAINED_BY / USES_INNOVATION` 边。`source_game_ids` 必含 anchor(来自图谱),故 `related_*` 并集必非空,满足 `OpportunityFrame` 的 `min_length=1`。

所有命令均在 `backend/` 目录下执行:`cd D:\Files\GameGraph\.claude\worktrees\opportunity-frame\backend`。

---

## Task 1: `OpportunityFrame` 加 `warnings` 可选字段

**Files:**
- Modify: `backend/app/schemas/artifacts.py:65-78`
- Test: `backend/tests/test_opportunity_frame_service.py`(本任务先建文件,只放 schema 往返测试)

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_opportunity_frame_service.py`,内容:

```python
from app.schemas.artifacts import OpportunityFrame


def _frame_kwargs() -> dict:
    return dict(
        id="frame|opp_1",
        developer_profile_id="profile_1",
        opportunity_area="基于横版割草的机会",
        source_game_ids=["game_vs", "game_fps"],
        related_mechanics=["护符定制"],
        related_player_experiences=["紧张刺激"],
        related_constraints=["低美术成本"],
        related_innovation_patterns=["规则编辑"],
        recommended_transformations=["将 Perspective 从「横版2D」替代为「第一人称」"],
        forbidden_directions=["违反硬约束：不做联网多人"],
        evidence_path=["锚点 game_vs 提供成熟配方"],
        fit_reason="契合短局",
        risk_reason="3D 抬高美术成本",
    )


def test_opportunity_frame_warnings_defaults_to_empty() -> None:
    frame = OpportunityFrame(**_frame_kwargs())
    assert frame.warnings == []


def test_opportunity_frame_accepts_warnings() -> None:
    frame = OpportunityFrame(**_frame_kwargs(), warnings=["未配置 LLM"])
    assert frame.warnings == ["未配置 LLM"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_opportunity_frame_service.py -q`
Expected: FAIL —— `test_opportunity_frame_accepts_warnings` 报 `extra="forbid"` 拒绝未知字段 `warnings`(`ValidationError`)。

- [ ] **Step 3: 加字段**

在 `backend/app/schemas/artifacts.py` 的 `OpportunityFrame` 类,`risk_reason` 字段下方新增一行(类内最后一个字段):

```python
class OpportunityFrame(StrictBaseModel):
    id: str = Field(min_length=1)
    developer_profile_id: str = Field(min_length=1)
    opportunity_area: str = Field(min_length=1)
    source_game_ids: list[NonEmptyStr] = Field(min_length=1)
    related_mechanics: list[NonEmptyStr] = Field(min_length=1)
    related_player_experiences: list[NonEmptyStr] = Field(min_length=1)
    related_constraints: list[NonEmptyStr] = Field(min_length=1)
    related_innovation_patterns: list[NonEmptyStr] = Field(min_length=1)
    recommended_transformations: list[NonEmptyStr] = Field(min_length=1)
    forbidden_directions: list[NonEmptyStr] = Field(min_length=1)
    evidence_path: list[NonEmptyStr] = Field(min_length=1)
    fit_reason: str = Field(min_length=1)
    risk_reason: str = Field(min_length=1)
    warnings: list[NonEmptyStr] = Field(default_factory=list)
```

(只新增最后一行 `warnings`;其余字段保持原样。)

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_opportunity_frame_service.py -q`
Expected: PASS(2 passed)

- [ ] **Step 5: 提交**

```bash
git add app/schemas/artifacts.py tests/test_opportunity_frame_service.py
git commit -m "feat(backend): add optional warnings field to OpportunityFrame"
```

---

## Task 2: `GameDesignFacts` + `fetch_game_design_facts` 图查询

**Files:**
- Modify: `backend/app/services/opportunity_service.py`(新增 `GameDesignFacts` 数据类,放在 `GameDimensions` 之后)
- Modify: `backend/app/graph/opportunity_repository.py`(新增查询常量 + 方法)
- Test: `backend/tests/test_opportunity_repository_integration.py`(新增集成测试)

- [ ] **Step 1: 写失败测试(集成,默认 deselect)**

在 `backend/tests/test_opportunity_repository_integration.py` 末尾追加:

```python
def test_fetch_game_design_facts_returns_profile_lists(driver) -> None:
    GameRepository(driver).upsert_game(_document("animal_well"))
    facts = OpportunityRepository(driver).fetch_game_design_facts(["game_animal_well"])
    aw = next(f for f in facts if f.game_id == "game_animal_well")
    assert aw.mechanics       # HAS_MECHANIC 非空
    assert aw.experiences     # DELIVERS_EXPERIENCE 非空
    assert aw.constraints     # CONSTRAINED_BY 非空
    assert aw.innovation_patterns  # USES_INNOVATION 非空
```

并在文件顶部 import 处确保 `GameDesignFacts` 可用(本步不需 import,断言用属性即可)。

- [ ] **Step 2: 跑测试确认失败(或 skip)**

Run: `python -m pytest tests/test_opportunity_repository_integration.py -m integration -q`
Expected: 若本地无 `NEO4J_PASSWORD` → SKIP(符合既有约定);若有活库 → FAIL（`AttributeError: 'OpportunityRepository' object has no attribute 'fetch_game_design_facts'`)。

- [ ] **Step 3: 加 `GameDesignFacts` 数据类**

在 `backend/app/services/opportunity_service.py` 的 `GameDimensions` 数据类**之后**新增:

```python
@dataclass
class GameDesignFacts:
    game_id: str
    mechanics: list[str] = field(default_factory=list)
    experiences: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    innovation_patterns: list[str] = field(default_factory=list)
```

(`dataclass`、`field` 已在文件顶部 import。)

- [ ] **Step 4: 加图查询方法**

在 `backend/app/graph/opportunity_repository.py`:顶部 import 改为同时引入新数据类,并新增查询常量与方法。

文件顶部 import 改为:

```python
from app.services.opportunity_service import GameDesignFacts, GameDimensions
```

在 `_FETCH_QUERY` 常量之后新增:

```python
_FACTS_QUERY = """
MATCH (g:Game) WHERE g.id IN $game_ids
RETURN g.id AS game_id,
       [(g)-[:HAS_MECHANIC]->(x)        | x.name] AS mechanics,
       [(g)-[:DELIVERS_EXPERIENCE]->(x) | x.name] AS experiences,
       [(g)-[:CONSTRAINED_BY]->(x)      | x.name] AS constraints,
       [(g)-[:USES_INNOVATION]->(x)     | x.name] AS innovation_patterns
"""
```

在 `OpportunityRepository` 类内、`fetch_game_dimensions` 之后新增:

```python
    def fetch_game_design_facts(self, game_ids: list[str]) -> list[GameDesignFacts]:
        with self._driver.session() as session:
            return session.execute_read(self._read_facts, game_ids)

    @staticmethod
    def _read_facts(tx, game_ids: list[str]) -> list[GameDesignFacts]:
        result = tx.run(_FACTS_QUERY, game_ids=game_ids)
        return [
            GameDesignFacts(
                game_id=record["game_id"],
                mechanics=list(record["mechanics"]),
                experiences=list(record["experiences"]),
                constraints=list(record["constraints"]),
                innovation_patterns=list(record["innovation_patterns"]),
            )
            for record in result
            if record["game_id"] is not None
        ]
```

- [ ] **Step 5: 跑测试确认通过(或仍 skip)+ 全量回归**

Run: `python -m pytest tests/test_opportunity_repository_integration.py -m integration -q`
Expected: 有活库 → PASS;无活库 → SKIP。

Run: `python -m pytest -q`
Expected: 仍全绿(135 passed, 4 deselected;新增的 schema 测试令通过数 +2 = 137 左右,无失败)。

- [ ] **Step 6: 提交**

```bash
git add app/services/opportunity_service.py app/graph/opportunity_repository.py tests/test_opportunity_repository_integration.py
git commit -m "feat(backend): add fetch_game_design_facts graph query for opportunity frame"
```

---

## Task 3: 确定性 helper 函数(无 LLM)

> ⚠️ **执行顺序:先做 Task 4 再做本任务。** 本任务的 `opportunity_frame_service.py` 在 import 阶段就依赖 Task 4 的 `FrameInputs/FrameSynthesis`;若先做本任务,Step 4 的 import 会失败。

**Files:**
- Create: `backend/app/services/opportunity_frame_service.py`
- Test: `backend/tests/test_opportunity_frame_service.py`(在 Task 1 文件基础上追加)

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_opportunity_frame_service.py` 顶部追加 import 与 fixtures,并加 helper 测试:

```python
from app.schemas.artifacts import DeveloperConstraint, DeveloperProfile
from app.schemas.common import ConstraintType
from app.schemas.opportunity import (
    OpportunityArea,
    OpportunityEvidence,
    RiskPosture,
    Transformation,
    TransformationType,
)
from app.services.opportunity_service import GameDesignFacts, GameDimensions
from app.services import opportunity_frame_service as svc


def _profile(constraints=None, disliked=None) -> DeveloperProfile:
    return DeveloperProfile(
        id="profile_1", team_size="solo", time_budget="三个月",
        programming_ability="强", art_ability="弱", audio_ability="弱",
        content_production_ability="有限", liked_references=["Hades"],
        disliked_references_or_mechanics=disliked if disliked is not None else ["联网多人"],
        desired_player_experiences=["短局"],
        constraints=constraints if constraints is not None else [
            DeveloperConstraint(id="c1", type=ConstraintType.HARD, statement="不做联网多人")
        ],
    )


def _area() -> OpportunityArea:
    return OpportunityArea(
        id="opp|game_vs|sub|Perspective|第一人称",
        anchor_game_id="game_vs", anchor_summary="横版割草",
        transformation=Transformation(
            type=TransformationType.SUBSTITUTE, dimension="Perspective",
            from_value="横版2D", to_value="第一人称",
        ),
        existing_combination_count=0,
        evidence=OpportunityEvidence(
            anchor_game_id="game_vs", target_value_game_ids=["game_fps"], combination_game_ids=[],
        ),
        risk_posture=RiskPosture.CHALLENGING, fit_reason="契合短局", risk_reason="3D 抬高美术成本",
    )


def _games() -> list[GameDimensions]:
    return [
        GameDimensions("game_vs", "横版割草", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, {"护符定制"}),
        GameDimensions("game_fps", "第一人称射击", {"类肉鸽"}, {"第一人称"}, {"低多边形"}, {"能力树"}),
    ]


def _facts() -> list[GameDesignFacts]:
    return [
        GameDesignFacts("game_vs", ["护符定制"], ["紧张刺激"], ["低美术成本"], ["数值滚雪球"]),
        GameDesignFacts("game_fps", ["能力树"], ["爽快射击"], ["低多边形可控"], ["快速重开"]),
    ]


def test_source_game_ids_is_dedup_closure() -> None:
    assert svc._source_game_ids(_area()) == ["game_vs", "game_fps"]


def test_union_related_preserves_order_and_dedups() -> None:
    mechanics, experiences, constraints, innovations = svc._union_related(_facts())
    assert mechanics == ["护符定制", "能力树"]
    assert experiences == ["紧张刺激", "爽快射击"]
    assert constraints == ["低美术成本", "低多边形可控"]
    assert innovations == ["数值滚雪球", "快速重开"]


def test_describe_transformation_substitute_and_combine() -> None:
    sub = Transformation(type=TransformationType.SUBSTITUTE, dimension="Perspective",
                         from_value="横版2D", to_value="第一人称")
    comb = Transformation(type=TransformationType.COMBINE, dimension="Mechanic",
                          from_value=None, to_value="卡牌构筑")
    assert svc._describe_transformation(sub) == "将 Perspective 从「横版2D」替代为「第一人称」"
    assert svc._describe_transformation(comb) == "在 Mechanic 维度组合借入「卡牌构筑」"


def test_evidence_path_starts_with_anchor() -> None:
    path = svc._evidence_path(_area())
    assert path[0].startswith("锚点 game_vs")
    assert any("第一人称" in line for line in path)
    assert any("现存游戏数 = 0" in line for line in path)


def test_forbidden_base_includes_hard_constraint_and_dislikes() -> None:
    base = svc._forbidden_base(_profile())
    assert any("违反硬约束：不做联网多人" in x for x in base)
    assert any("联网多人" in x for x in base)


def test_forbidden_base_never_empty_without_constraints() -> None:
    profile = _profile(
        constraints=[DeveloperConstraint(id="c1", type=ConstraintType.SOFT_PREFERENCE, statement="偏好短局")],
        disliked=[],
    )
    base = svc._forbidden_base(profile)
    assert len(base) >= 1
    assert any("证据范围" in x for x in base)


def test_secondary_pool_excludes_selected_and_is_same_anchor() -> None:
    pool = svc._secondary_pool(_StubRepo(_games(), _facts()), _area())
    assert all(c.anchor_game_id == "game_vs" for c in pool)
    assert all(c.id != _area().id for c in pool)


class _StubRepo:
    def __init__(self, games, facts) -> None:
        self._games = games
        self._facts = facts

    def fetch_game_dimensions(self):
        return self._games

    def fetch_game_design_facts(self, game_ids):
        return [f for f in self._facts if f.game_id in game_ids]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_opportunity_frame_service.py -q`
Expected: FAIL —— `ModuleNotFoundError: No module named 'app.services.opportunity_frame_service'`。

- [ ] **Step 3: 写 helper 实现**

新建 `backend/app/services/opportunity_frame_service.py`:

```python
from __future__ import annotations

import logging
from typing import Protocol

from app.schemas.artifacts import DeveloperProfile, OpportunityFrame
from app.schemas.common import ConstraintType
from app.schemas.opportunity import OpportunityArea, Transformation, TransformationType
from app.services.opportunity_frame_llm import FrameInputs, FrameSynthesis
from app.services.opportunity_service import (
    CandidateOpportunityArea,
    GameDesignFacts,
    GameDimensions,
    enumerate_candidates,
    rank_candidates,
)

logger = logging.getLogger(__name__)

_NO_LLM_WARNING = "未配置 LLM，机会框架未做叙述综合与次变形扩展，仅返回确定性证据组装。"
_LLM_FAILED_WARNING = "LLM 综合失败，机会框架已降级为确定性证据组装。"
_NO_EXPLICIT_FORBIDDEN = "不要在框架证据范围之外自由发挥（引入无来源支撑的机制或参考）。"


class SupportsFrameRepository(Protocol):
    def fetch_game_dimensions(self) -> list[GameDimensions]: ...
    def fetch_game_design_facts(self, game_ids: list[str]) -> list[GameDesignFacts]: ...


class SupportsFrameSynthesis(Protocol):
    def synthesize(
        self, profile: DeveloperProfile, area: OpportunityArea, inputs: FrameInputs
    ) -> FrameSynthesis: ...


def _dedup(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out


def _source_game_ids(area: OpportunityArea) -> list[str]:
    return _dedup(
        [area.anchor_game_id, *area.evidence.target_value_game_ids, *area.evidence.combination_game_ids]
    )


def _union_related(facts: list[GameDesignFacts]) -> tuple[list[str], list[str], list[str], list[str]]:
    def union(attr: str) -> list[str]:
        return _dedup([v for f in facts for v in getattr(f, attr)])

    return (
        union("mechanics"),
        union("experiences"),
        union("constraints"),
        union("innovation_patterns"),
    )


def _describe_transformation(t: Transformation) -> str:
    if t.type == TransformationType.SUBSTITUTE:
        return f"将 {t.dimension} 从「{t.from_value}」替代为「{t.to_value}」"
    return f"在 {t.dimension} 维度组合借入「{t.to_value}」"


def _evidence_path(area: OpportunityArea) -> list[str]:
    ev = area.evidence
    path = [f"锚点 {area.anchor_game_id} 提供成熟配方：{area.anchor_summary}"]
    path.append(
        f"目标值「{area.transformation.to_value}」在 {', '.join(ev.target_value_game_ids)} 上有据"
    )
    path.append(
        f"该组合在策展库中的现存游戏数 = {area.existing_combination_count}（越小越新颖）"
    )
    return path


def _forbidden_base(profile: DeveloperProfile) -> list[str]:
    base: list[str] = []
    for c in profile.constraints:
        if c.type == ConstraintType.HARD:
            base.append(f"违反硬约束：{c.statement}")
    for disliked in profile.disliked_references_or_mechanics:
        base.append(f"避免开发者明确反感的方向：{disliked}")
    if not base:
        base.append(_NO_EXPLICIT_FORBIDDEN)
    return _dedup(base)


def _secondary_pool(
    repository: SupportsFrameRepository, area: OpportunityArea
) -> list[CandidateOpportunityArea]:
    games = repository.fetch_game_dimensions()
    pool = [
        c
        for c in enumerate_candidates(games)
        if c.anchor_game_id == area.anchor_game_id and c.id != area.id
    ]
    return rank_candidates(pool)
```

(`build_frame` 在 Task 5 加入;本任务只验证上述 helper。)

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_opportunity_frame_service.py -q`
Expected: PASS（Task 1 的 2 条 + 本任务 7 条 = 9 passed）。
注意:此时 `opportunity_frame_service` import 了尚未存在的 `opportunity_frame_llm` 的 `FrameInputs/FrameSynthesis` —— **这会导致 import 失败**。因此本任务必须与 Task 4 调换顺序,或先建最小占位。**实现顺序见下方说明。**

> **顺序说明:** Task 3 的 service import 依赖 Task 4 的 `FrameInputs/FrameSynthesis`。**先做 Task 4(LLM 模块)再做 Task 3 的实现**,或在 Task 3 Step 3 之前先完成 Task 4 Step 3。本计划按「Task 4 → Task 3」的实际依赖执行;编号保留但执行时先 4 后 3。两者的测试互不依赖,可分别验证。

- [ ] **Step 5: 提交**

```bash
git add app/services/opportunity_frame_service.py tests/test_opportunity_frame_service.py
git commit -m "feat(backend): add deterministic helpers for opportunity frame assembly"
```

---

## Task 4: LLM 综合层(先于 Task 3 实现)

**Files:**
- Create: `backend/app/services/opportunity_frame_llm.py`
- Test: `backend/tests/test_opportunity_frame_llm.py`

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_opportunity_frame_llm.py`:

```python
import json

import httpx
import pytest

from app.schemas.artifacts import DeveloperConstraint, DeveloperProfile
from app.schemas.common import ConstraintType
from app.schemas.opportunity import (
    CandidateOpportunityArea,
    OpportunityArea,
    OpportunityEvidence,
    RiskPosture,
    Transformation,
    TransformationType,
)
from app.services.opportunity_frame_llm import (
    FrameInputs,
    FrameSynthesis,
    OpportunityFrameLlmClient,
    build_frame_tool_schema,
    get_opportunity_frame_llm_client,
)
from app.services.opportunity_llm import LlmSettings


def _settings() -> LlmSettings:
    return LlmSettings(base_url="https://example.test/v1", api_key="secret", model="m", timeout=5.0)


def _profile() -> DeveloperProfile:
    return DeveloperProfile(
        id="profile_1", team_size="solo", time_budget="三个月",
        programming_ability="强", art_ability="弱", audio_ability="弱",
        content_production_ability="有限", liked_references=["Hades"],
        disliked_references_or_mechanics=["联网多人"], desired_player_experiences=["短局"],
        constraints=[DeveloperConstraint(id="c1", type=ConstraintType.HARD, statement="不做联网多人")],
    )


def _area() -> OpportunityArea:
    return OpportunityArea(
        id="opp|game_vs|sub|Perspective|第一人称",
        anchor_game_id="game_vs", anchor_summary="横版割草",
        transformation=Transformation(type=TransformationType.SUBSTITUTE, dimension="Perspective",
                                      from_value="横版2D", to_value="第一人称"),
        existing_combination_count=0,
        evidence=OpportunityEvidence(anchor_game_id="game_vs", target_value_game_ids=["game_fps"],
                                     combination_game_ids=[]),
        risk_posture=RiskPosture.CHALLENGING, fit_reason="契合短局", risk_reason="3D 抬高美术成本",
    )


def _pool() -> list[CandidateOpportunityArea]:
    return [
        CandidateOpportunityArea(
            id="opp|game_vs|comb|Mechanic|能力树",
            anchor_game_id="game_vs", anchor_summary="横版割草",
            transformation=Transformation(type=TransformationType.COMBINE, dimension="Mechanic",
                                          from_value=None, to_value="能力树"),
            existing_combination_count=1,
            evidence=OpportunityEvidence(anchor_game_id="game_vs", target_value_game_ids=["game_fps"],
                                         combination_game_ids=["game_fps"]),
        )
    ]


def _inputs() -> FrameInputs:
    return FrameInputs(
        related_mechanics=["护符定制", "能力树"],
        related_player_experiences=["紧张刺激"],
        related_constraints=["低美术成本"],
        related_innovation_patterns=["数值滚雪球"],
        secondary_pool=_pool(),
    )


def _arguments() -> str:
    return json.dumps(
        {
            "opportunity_area": "第一人称生存割草",
            "secondary_transformations": ["叠加能力树以延长单局成长"],
            "forbidden_directions": ["看似新颖但不可行：实时联网协作割草"],
            "fit_reason": "契合 solo 程序强、短局快节奏",
            "risk_reason": "第一人称抬高美术与运动眩晕风险",
            "warnings": [],
        }
    )


def test_build_frame_tool_schema_exposes_function_name() -> None:
    tools = build_frame_tool_schema()
    assert tools[0]["function"]["name"] == "emit_opportunity_frame"
    assert tools[0]["function"]["parameters"]["properties"]


def test_synthesize_posts_request_and_parses() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"tool_calls": [
            {"function": {"name": "emit_opportunity_frame", "arguments": _arguments()}}
        ]}}]})

    client = OpportunityFrameLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    synth = client.synthesize(_profile(), _area(), _inputs())

    assert isinstance(synth, FrameSynthesis)
    assert synth.opportunity_area == "第一人称生存割草"
    assert synth.secondary_transformations == ["叠加能力树以延长单局成长"]
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["body"]["tool_choice"]["function"]["name"] == "emit_opportunity_frame"
    assert seen["body"]["messages"][0]["role"] == "system"


def test_synthesize_raises_when_no_tool_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    client = OpportunityFrameLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError, match="tool_call"):
        client.synthesize(_profile(), _area(), _inputs())


def test_synthesize_raises_value_error_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid_api_key"}})

    client = OpportunityFrameLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError, match="401"):
        client.synthesize(_profile(), _area(), _inputs())


def test_get_client_returns_none_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    assert get_opportunity_frame_llm_client() is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_opportunity_frame_llm.py -q`
Expected: FAIL —— `ModuleNotFoundError: No module named 'app.services.opportunity_frame_llm'`。

- [ ] **Step 3: 写 LLM 模块**

新建 `backend/app/services/opportunity_frame_llm.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field

import httpx
from pydantic import ConfigDict, Field

from app.schemas.artifacts import DeveloperProfile
from app.schemas.common import StrictBaseModel
from app.schemas.opportunity import CandidateOpportunityArea, OpportunityArea
from app.services.opportunity_llm import (
    LlmSettings,
    _candidate_block,
    _profile_block,
)

TOOL_NAME = "emit_opportunity_frame"

SYSTEM_PROMPT = (
    "你是独立游戏创意系统的机会框架综合器。"
    "给你开发者画像、一个【被选中的机会区域】(锚点×主变形+证据)、一份【同证据次变形候选池】"
    "以及已由图谱确定性取出的相关机制/体验/约束/创新模式。"
    "请只做叙述综合，不得发明：\n"
    "1. opportunity_area：给这个机会一个简洁主题标签。\n"
    "2. secondary_transformations：只能从【次变形候选池】里挑选并叙述，"
    "禁止发明池子之外、图谱零证据的变形;主变形不要重复(它由系统置于首位)。\n"
    "3. forbidden_directions：把候选池里看似新颖但不自洽/做不出的(dead-zone)写成禁止方向并说明为何行不通"
    "(硬约束禁止项由系统自动补，无需重复)。\n"
    "4. fit_reason / risk_reason：适配理由与风险/取舍说明。\n"
    "不得引入相关机制/来源游戏证据之外的机制或参考。"
)


@dataclass
class FrameInputs:
    related_mechanics: list[str] = field(default_factory=list)
    related_player_experiences: list[str] = field(default_factory=list)
    related_constraints: list[str] = field(default_factory=list)
    related_innovation_patterns: list[str] = field(default_factory=list)
    secondary_pool: list[CandidateOpportunityArea] = field(default_factory=list)


class FrameSynthesis(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")

    opportunity_area: str = ""
    secondary_transformations: list[str] = Field(default_factory=list)
    forbidden_directions: list[str] = Field(default_factory=list)
    fit_reason: str = ""
    risk_reason: str = ""
    warnings: list[str] = Field(default_factory=list)


def build_frame_tool_schema() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": "Synthesize the narrative fields of one opportunity frame.",
                "parameters": FrameSynthesis.model_json_schema(),
            },
        }
    ]


def _related_block(inputs: FrameInputs) -> str:
    return (
        f"相关机制:{', '.join(inputs.related_mechanics)}\n"
        f"相关体验:{', '.join(inputs.related_player_experiences)}\n"
        f"相关约束:{', '.join(inputs.related_constraints)}\n"
        f"相关创新模式:{', '.join(inputs.related_innovation_patterns)}"
    )


def _selected_block(area: OpportunityArea) -> str:
    t = area.transformation
    change = f"{t.from_value}->{t.to_value}" if t.from_value else f"+{t.to_value}"
    return f"锚点={area.anchor_summary} 主变形={t.type.value}:{t.dimension}({change})"


def _user_block(profile: DeveloperProfile, area: OpportunityArea, inputs: FrameInputs) -> str:
    pool_text = _candidate_block(inputs.secondary_pool) or "（无同证据次变形）"
    return (
        f"开发者画像：\n{_profile_block(profile)}\n\n"
        f"被选中的机会区域：\n{_selected_block(area)}\n\n"
        f"次变形候选池：\n{pool_text}\n\n"
        f"图谱相关材料：\n{_related_block(inputs)}"
    )


class OpportunityFrameLlmClient:
    def __init__(self, settings: LlmSettings, http_client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout)

    def synthesize(
        self, profile: DeveloperProfile, area: OpportunityArea, inputs: FrameInputs
    ) -> FrameSynthesis:
        payload = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_block(profile, area, inputs)},
            ],
            "tools": build_frame_tool_schema(),
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
        return FrameSynthesis.model_validate_json(tool_calls[0]["function"]["arguments"])


def get_opportunity_frame_llm_client() -> OpportunityFrameLlmClient | None:
    settings = LlmSettings.from_env()
    if not settings.is_configured:
        return None
    return OpportunityFrameLlmClient(settings)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_opportunity_frame_llm.py -q`
Expected: PASS（5 passed）

- [ ] **Step 5: 提交**

```bash
git add app/services/opportunity_frame_llm.py tests/test_opportunity_frame_llm.py
git commit -m "feat(backend): add opportunity frame LLM synthesis client"
```

> 完成 Task 4 后,回到 **Task 3** 完成 service helper 实现与提交(此时 `FrameInputs/FrameSynthesis` 已存在,import 不再失败)。

---

## Task 5: `build_frame` 编排 + 降级

**Files:**
- Modify: `backend/app/services/opportunity_frame_service.py`(追加 `build_frame` 及私有装配函数)
- Test: `backend/tests/test_opportunity_frame_service.py`(追加编排测试)

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_opportunity_frame_service.py` 追加(沿用前面已定义的 `_profile/_area/_games/_facts/_StubRepo`):

```python
from app.services.opportunity_frame_llm import FrameInputs, FrameSynthesis


class _StubLlm:
    def __init__(self, synth: FrameSynthesis) -> None:
        self._synth = synth
        self.seen: FrameInputs | None = None

    def synthesize(self, profile, area, inputs):
        self.seen = inputs
        return self._synth


class _BrokenLlm:
    def synthesize(self, profile, area, inputs):
        raise RuntimeError("boom")


def _synth() -> FrameSynthesis:
    return FrameSynthesis(
        opportunity_area="第一人称生存割草",
        secondary_transformations=["叠加能力树以延长单局成长"],
        forbidden_directions=["看似新颖但不可行：实时联网协作割草"],
        fit_reason="契合 solo 程序强",
        risk_reason="第一人称抬高美术成本",
        warnings=[],
    )


def test_build_frame_with_llm_assembles_full_frame() -> None:
    repo = _StubRepo(_games(), _facts())
    frame = svc.build_frame(_profile(), _area(), repo, _StubLlm(_synth()))
    assert frame.id == "frame|opp|game_vs|sub|Perspective|第一人称"
    assert frame.developer_profile_id == "profile_1"
    assert frame.source_game_ids == ["game_vs", "game_fps"]
    assert frame.related_mechanics == ["护符定制", "能力树"]
    # 主变形恒在首位
    assert frame.recommended_transformations[0] == "将 Perspective 从「横版2D」替代为「第一人称」"
    assert "叠加能力树以延长单局成长" in frame.recommended_transformations
    # 硬约束禁止项 + LLM dead-zone 都在
    assert any("违反硬约束：不做联网多人" in x for x in frame.forbidden_directions)
    assert any("实时联网协作割草" in x for x in frame.forbidden_directions)
    assert frame.fit_reason == "契合 solo 程序强"
    assert frame.opportunity_area == "第一人称生存割草"
    assert frame.warnings == []


def test_build_frame_without_llm_degrades_with_warning() -> None:
    repo = _StubRepo(_games(), _facts())
    frame = svc.build_frame(_profile(), _area(), repo, None)
    assert frame.recommended_transformations == ["将 Perspective 从「横版2D」替代为「第一人称」"]
    assert frame.fit_reason == "契合短局"        # 沿用 area 自带
    assert frame.risk_reason == "3D 抬高美术成本"  # 沿用 area 自带
    assert any("未配置 LLM" in w for w in frame.warnings)
    assert frame.forbidden_directions  # 非空(硬约束基底)


def test_build_frame_falls_back_when_llm_raises() -> None:
    repo = _StubRepo(_games(), _facts())
    frame = svc.build_frame(_profile(), _area(), repo, _BrokenLlm())
    assert any("降级" in w for w in frame.warnings)
    assert not any("未配置 LLM" in w for w in frame.warnings)
    assert frame.fit_reason == "契合短局"


def test_build_frame_forbidden_never_empty_without_constraints() -> None:
    profile = _profile(
        constraints=[DeveloperConstraint(id="c1", type=ConstraintType.SOFT_PREFERENCE, statement="偏好短局")],
        disliked=[],
    )
    repo = _StubRepo(_games(), _facts())
    frame = svc.build_frame(profile, _area(), repo, None)
    assert len(frame.forbidden_directions) >= 1
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_opportunity_frame_service.py -k build_frame -q`
Expected: FAIL —— `AttributeError: module 'app.services.opportunity_frame_service' has no attribute 'build_frame'`。

- [ ] **Step 3: 写 `build_frame` 实现**

在 `backend/app/services/opportunity_frame_service.py` 末尾追加:

```python
def _fallback_area_label(area: OpportunityArea) -> str:
    return f"基于「{area.anchor_summary}」的机会：{_describe_transformation(area.transformation)}"


def _assemble(
    *,
    profile: DeveloperProfile,
    area: OpportunityArea,
    source_ids: list[str],
    related: tuple[list[str], list[str], list[str], list[str]],
    recommended: list[str],
    forbidden: list[str],
    evidence_path: list[str],
    opportunity_area: str,
    fit_reason: str,
    risk_reason: str,
    warnings: list[str],
) -> OpportunityFrame:
    mechanics, experiences, constraints, innovations = related
    return OpportunityFrame(
        id=f"frame|{area.id}",
        developer_profile_id=profile.id,
        opportunity_area=opportunity_area,
        source_game_ids=source_ids,
        related_mechanics=mechanics,
        related_player_experiences=experiences,
        related_constraints=constraints,
        related_innovation_patterns=innovations,
        recommended_transformations=recommended,
        forbidden_directions=forbidden,
        evidence_path=evidence_path,
        fit_reason=fit_reason,
        risk_reason=risk_reason,
        warnings=warnings,
    )


def build_frame(
    profile: DeveloperProfile,
    area: OpportunityArea,
    repository: SupportsFrameRepository,
    llm_client: SupportsFrameSynthesis | None,
) -> OpportunityFrame:
    source_ids = _source_game_ids(area)
    related = _union_related(repository.fetch_game_design_facts(source_ids))
    primary = _describe_transformation(area.transformation)
    evidence_path = _evidence_path(area)
    forbidden_base = _forbidden_base(profile)

    def fallback(warning: str) -> OpportunityFrame:
        return _assemble(
            profile=profile, area=area, source_ids=source_ids, related=related,
            recommended=[primary], forbidden=forbidden_base, evidence_path=evidence_path,
            opportunity_area=_fallback_area_label(area),
            fit_reason=area.fit_reason, risk_reason=area.risk_reason, warnings=[warning],
        )

    if llm_client is None:
        return fallback(_NO_LLM_WARNING)

    inputs = FrameInputs(
        related_mechanics=related[0],
        related_player_experiences=related[1],
        related_constraints=related[2],
        related_innovation_patterns=related[3],
        secondary_pool=_secondary_pool(repository, area),
    )
    try:
        synth = llm_client.synthesize(profile, area, inputs)
    except Exception:
        logger.warning("Opportunity frame LLM synthesize failed; falling back", exc_info=True)
        return fallback(_LLM_FAILED_WARNING)

    recommended = _dedup([primary, *synth.secondary_transformations])
    forbidden = _dedup([*forbidden_base, *synth.forbidden_directions])
    return _assemble(
        profile=profile, area=area, source_ids=source_ids, related=related,
        recommended=recommended, forbidden=forbidden, evidence_path=evidence_path,
        opportunity_area=synth.opportunity_area or _fallback_area_label(area),
        fit_reason=synth.fit_reason or area.fit_reason,
        risk_reason=synth.risk_reason or area.risk_reason,
        warnings=list(synth.warnings),
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_opportunity_frame_service.py -q`
Expected: PASS（全部:Task1 的 2 + Task3 的 7 + 本任务 4 = 13 passed）

- [ ] **Step 5: 提交**

```bash
git add app/services/opportunity_frame_service.py tests/test_opportunity_frame_service.py
git commit -m "feat(backend): orchestrate opportunity frame build with LLM + degradation"
```

---

## Task 6: API 路由 `POST /opportunity/frame`

**Files:**
- Modify: `backend/app/api/routes_opportunity.py`
- Test: `backend/tests/test_opportunity_frame_api.py`

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_opportunity_frame_api.py`:

```python
from fastapi.testclient import TestClient

from app.api.routes_opportunity import (
    get_opportunity_frame_llm,
    get_opportunity_repository,
)
from app.main import app
from app.services.opportunity_frame_llm import FrameSynthesis
from app.services.opportunity_service import GameDesignFacts, GameDimensions


class StubRepo:
    def fetch_game_dimensions(self):
        return [
            GameDimensions("game_vs", "横版割草", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, {"护符定制"}),
            GameDimensions("game_fps", "第一人称射击", {"类肉鸽"}, {"第一人称"}, {"低多边形"}, {"能力树"}),
        ]

    def fetch_game_design_facts(self, game_ids):
        rows = [
            GameDesignFacts("game_vs", ["护符定制"], ["紧张刺激"], ["低美术成本"], ["数值滚雪球"]),
            GameDesignFacts("game_fps", ["能力树"], ["爽快射击"], ["低多边形可控"], ["快速重开"]),
        ]
        return [r for r in rows if r.game_id in game_ids]


class StubLlm:
    def synthesize(self, profile, area, inputs):
        return FrameSynthesis(
            opportunity_area="第一人称生存割草",
            secondary_transformations=["叠加能力树"],
            forbidden_directions=["看似新颖但不可行：实时联网协作"],
            fit_reason="契合", risk_reason="美术成本", warnings=[],
        )


def _profile() -> dict:
    return {
        "id": "profile_1", "team_size": "solo", "time_budget": "三个月",
        "programming_ability": "强", "art_ability": "弱", "audio_ability": "弱",
        "content_production_ability": "有限", "liked_references": ["Hades"],
        "disliked_references_or_mechanics": ["联网多人"], "desired_player_experiences": ["短局"],
        "constraints": [{"id": "c1", "type": "hard", "statement": "不做联网多人"}],
    }


def _area() -> dict:
    return {
        "id": "opp|game_vs|sub|Perspective|第一人称",
        "anchor_game_id": "game_vs", "anchor_summary": "横版割草",
        "transformation": {"type": "substitute", "dimension": "Perspective",
                           "from_value": "横版2D", "to_value": "第一人称"},
        "existing_combination_count": 0,
        "evidence": {"anchor_game_id": "game_vs", "target_value_game_ids": ["game_fps"],
                     "combination_game_ids": []},
        "risk_posture": "challenging", "fit_reason": "契合短局", "risk_reason": "3D 抬高美术成本",
    }


def test_frame_endpoint_returns_frame() -> None:
    app.dependency_overrides[get_opportunity_repository] = lambda: StubRepo()
    app.dependency_overrides[get_opportunity_frame_llm] = lambda: StubLlm()
    try:
        client = TestClient(app)
        response = client.post("/opportunity/frame", json={"profile": _profile(), "area": _area()})
        assert response.status_code == 200
        body = response.json()
        assert body["developer_profile_id"] == "profile_1"
        assert body["recommended_transformations"][0] == "将 Perspective 从「横版2D」替代为「第一人称」"
        assert body["source_game_ids"] == ["game_vs", "game_fps"]
        assert any("违反硬约束" in x for x in body["forbidden_directions"])
    finally:
        app.dependency_overrides.clear()


def test_frame_endpoint_degrades_without_llm() -> None:
    app.dependency_overrides[get_opportunity_repository] = lambda: StubRepo()
    app.dependency_overrides[get_opportunity_frame_llm] = lambda: None
    try:
        client = TestClient(app)
        response = client.post("/opportunity/frame", json={"profile": _profile(), "area": _area()})
        assert response.status_code == 200
        body = response.json()
        assert any("未配置 LLM" in w for w in body["warnings"])
    finally:
        app.dependency_overrides.clear()


def test_frame_endpoint_rejects_malformed_request() -> None:
    app.dependency_overrides[get_opportunity_repository] = lambda: StubRepo()
    app.dependency_overrides[get_opportunity_frame_llm] = lambda: StubLlm()
    try:
        client = TestClient(app)
        response = client.post("/opportunity/frame", json={"profile": _profile()})  # 缺 area
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_opportunity_frame_api.py -q`
Expected: FAIL —— `ImportError: cannot import name 'get_opportunity_frame_llm'`。

- [ ] **Step 3: 写路由实现**

在 `backend/app/api/routes_opportunity.py` 修改:

顶部 import 区追加:

```python
from app.schemas.artifacts import OpportunityFrame
from app.schemas.common import StrictBaseModel
from app.schemas.opportunity import OpportunityArea
from app.services.opportunity_frame_llm import (
    OpportunityFrameLlmClient,
    get_opportunity_frame_llm_client,
)
from app.services.opportunity_frame_service import build_frame
```

(已有的 `from app.schemas.artifacts import DeveloperProfile`、`from app.schemas.opportunity import OpportunityMatchResult` 保留;`DeveloperProfile` 与上面 `OpportunityFrame` 可合并为一行,亦可分行。)

在文件末尾(`match_endpoint` 之后)追加请求模型、provider 与路由:

```python
class OpportunityFrameRequest(StrictBaseModel):
    profile: DeveloperProfile
    area: OpportunityArea


def get_opportunity_frame_llm() -> OpportunityFrameLlmClient | None:
    # 默认 provider：返回可选 frame LLM 客户端。测试通过 dependency_overrides 覆盖。
    return get_opportunity_frame_llm_client()


@router.post("/opportunity/frame", response_model=OpportunityFrame)
def frame_endpoint(
    request: OpportunityFrameRequest,
    repository: OpportunityRepository = Depends(get_opportunity_repository),
    llm_client: OpportunityFrameLlmClient | None = Depends(get_opportunity_frame_llm),
) -> OpportunityFrame:
    return build_frame(request.profile, request.area, repository, llm_client)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_opportunity_frame_api.py -q`
Expected: PASS（3 passed）

- [ ] **Step 5: 全量回归**

Run: `python -m pytest -q`
Expected: 全绿,无失败(基线 135 + 本计划新增约 23 条 ≈ 158 passed, 4 deselected;具体数字以实际为准,关键是 0 failed)。

- [ ] **Step 6: 提交**

```bash
git add app/api/routes_opportunity.py tests/test_opportunity_frame_api.py
git commit -m "feat(backend): add POST /opportunity/frame endpoint"
```

---

## 前端交接(不在本后端分支改动)

`OpportunityFrame.warnings` 是加性可选字段。前端 agent 在 6.6 前端分支自行:
- `frontend/lib/types/index.ts` 的 `OpportunityFrame` 加 `warnings?: string[];`。
- 复用 6.5 既有 warnings 提示条渲染。
- 按约定把 `recommended_transformations[0]` 渲染为 headline(脊梁/主变形),其余作次级。

**本后端 worktree 不触碰任何 `frontend/` 文件**,以免与前端 agent 并发冲突。

---

## Self-Review

**1. Spec coverage(逐节核对):**
- §2 粒度 1:1 → Task 6 端点输入单个 area,build_frame 产单个 frame ✓
- §3 两层 + (a)主变形具象化 / (b)同证据次变形池 → Task 3 `_describe_transformation` + `_secondary_pool`、Task 5 `recommended=[primary, *secondary]` ✓
- §3.1 复用 6.5 枚举 → Task 3 `_secondary_pool` import `enumerate_candidates/rank_candidates` ✓
- §5 schema warnings → Task 1 ✓
- §6.1 证据闭包 → `_source_game_ids` ✓;§6.2 related_* 图查询(边名表)→ Task 2 `_FACTS_QUERY`(`DELIVERS_EXPERIENCE`/`Experience`)✓;§6.3 次变形池 ✓;§6.4 evidence_path ✓;§6.5 硬约束禁止基底 ✓
- §7 LLM 综合 + 降级(沿用 area fit/risk)→ Task 4 + Task 5 fallback ✓
- §8 API 契约 `{profile, area}` → frame → Task 6 ✓
- §9 `recommended_transformations[0]`=主变形 → Task 5 确定性置首 + 测试断言 ✓
- §10 测试映射 → 各任务 TDD ✓
- §13 限制(forbidden 非空)→ `_forbidden_base` 兜底 + 专门测试 ✓

**2. Placeholder scan:** 无 TBD/TODO;每个 code step 含完整代码。✓

**3. Type consistency:**
- `GameDesignFacts(game_id, mechanics, experiences, constraints, innovation_patterns)` 在 Task 2 定义,Task 3/5/6 一致使用 ✓
- `FrameInputs(related_mechanics, related_player_experiences, related_constraints, related_innovation_patterns, secondary_pool)` Task 4 定义,Task 5 构造一致 ✓
- `FrameSynthesis(opportunity_area, secondary_transformations, forbidden_directions, fit_reason, risk_reason, warnings)` Task 4 定义,Task 5/6 stub 一致 ✓
- `build_frame(profile, area, repository, llm_client)` Task 5 定义,Task 6 调用一致 ✓
- 端点 provider 名 `get_opportunity_repository`(复用 6.5)/ `get_opportunity_frame_llm`(新)Task 6 一致 ✓
- frame id 格式 `frame|{area.id}` Task 5 实现与 Task 5/6 测试断言一致 ✓

**已知执行顺序提醒:** Task 3 的 service 模块 import `opportunity_frame_llm`,故**实现顺序为 Task 1 → Task 2 → Task 4 → Task 3 → Task 5 → Task 6**(测试编号保留)。每个任务的测试集互相独立,可分别验证。
