# 功能角色 × 协同规则 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 6.5 机会枚举上叠加「功能角色协同」质量先验：把核心四段（Mechanic/GameFeel/Theme/Genre）受控词分类到 20 个 `FunctionalRole`，由一张手工协同规则表把「锚点已有角色 × 借入机制补的角色」点亮为带预测体验的 `SynergyRationale`，让命中协同的候选在排序中优先于纯稀缺候选，并写入机会框架证据链。

**Architecture:** 叠加层，非替换。角色/规则只待在旁路 fixture，由 `services/synergy.py` 在服务层查表推导；**图谱结构、import 路径、GameDesignProfile schema、既有 fixture 全部零改动**。角色覆盖完全由游戏既有四段取值推导，无需逐局标注。排序改动以 feature flag 包裹，flag 关时 6.5/6.6 行为不变。

**Tech Stack:** Python 3.12 / Pydantic v2(`StrictBaseModel`)/ Neo4j Python driver / pytest。

**Spec:** `docs/superpowers/specs/2026-06-12-functional-role-synergy-design.zh-CN.md`

所有命令在 `backend/` 下执行：`cd D:\Files\GameGraph\.claude\worktrees\functional-role-synergy\backend`（worktree 里跑测试必须 cd 到 backend/，否则 import 主仓库 editable 旧 app）。

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `backend/app/schemas/opportunity.py` | 加 `FunctionalRole`(20) / `SynergyRule` / `SynergyRationale`；`CandidateOpportunityArea` 加可选 `synergy` | Modify |
| `backend/app/fixtures/element_roles.json` | 角色 → 核心四段词分类表（见 spec §4） | Create |
| `backend/app/fixtures/synergy_rules.json` | 20 条协同规则（见 spec §5） | Create |
| `backend/app/services/synergy.py` | 加载/校验 + `roles_for_elements` + `find_synergy` + `rationale_for` | Create |
| `backend/app/services/opportunity_service.py` | `GameDimensions` 加 `theme`/`game_feel`；枚举标注 synergy；`rank_candidates` synergy 优先（flag） | Modify |
| `backend/app/graph/opportunity_repository.py` | 取数查询补 `theme`/`game_feel`；构造 `GameDimensions` 带新字段 | Modify |
| `backend/app/services/opportunity_frame_service.py` | `_evidence_path` 写入协同推理行 | Modify |
| `backend/tests/test_synergy.py` | 加载/分类/推导/命中 单测 | Create |
| `backend/tests/test_opportunity_schemas.py` | `synergy` 字段往返 + 枚举 | Modify |
| `backend/tests/test_opportunity_enumeration.py` | 枚举标注 + 排序优先 | Modify |
| `backend/tests/test_opportunity_repository_integration.py` | `GameDimensions` 含 theme/game_feel | Modify |
| `backend/tests/test_opportunity_frame_service.py` | 框架证据含协同行 | Modify |

---

## Task 1: Schema —— `FunctionalRole` / `SynergyRule` / `SynergyRationale` / 候选 `synergy` 字段

**Files:** Modify `app/schemas/opportunity.py`；Modify `tests/test_opportunity_schemas.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_opportunity_schemas.py` 追加：
```python
from app.schemas.opportunity import (
    FunctionalRole, SynergyRule, SynergyRationale,
)

def test_functional_role_has_twenty_members() -> None:
    assert len(list(FunctionalRole)) == 20
    assert FunctionalRole.HIGH_VARIANCE_FAILURE == "高方差失败源"
    assert FunctionalRole.EMOTIONAL_BOND == "情感羁绊"

def test_synergy_rule_round_trips() -> None:
    rule = SynergyRule(
        id="r1", role_a=FunctionalRole.HIGH_VARIANCE_FAILURE,
        role_b=FunctionalRole.SOCIAL_AMPLIFIER, experience="欢乐混乱",
        evidence_games=["game_gamble_with_your_friends"],
    )
    assert SynergyRule.model_validate_json(rule.model_dump_json()) == rule

def test_candidate_synergy_defaults_none_and_accepts(_candidate=None) -> None:
    c = _candidate()  # 复用本文件既有 _candidate()
    assert c.synergy is None
    rationale = SynergyRationale(
        rule_id="r1", anchor_role=FunctionalRole.SOCIAL_AMPLIFIER,
        borrowed_role=FunctionalRole.HIGH_VARIANCE_FAILURE, predicted_experience="欢乐混乱",
    )
    c2 = _candidate(synergy=rationale)
    assert c2.synergy.rule_id == "r1"
```
（`_candidate()` 已在该文件，给它支持 `synergy=` 透传即可；若签名不便，直接 `CandidateOpportunityArea(**_candidate().model_dump(), synergy=...)`。）

- [ ] **Step 2: 跑测试确认失败** — `python -m pytest tests/test_opportunity_schemas.py -q`，预期 ImportError（无 `FunctionalRole`）。

- [ ] **Step 3: 实现** —— 在 `app/schemas/opportunity.py` 的 `OpportunityEvidence` 之后、`CandidateOpportunityArea` 之前插入 `FunctionalRole`(20 值，分组见 spec §4)、`SynergyRule`、`SynergyRationale`；给 `CandidateOpportunityArea` 末尾加 `synergy: SynergyRationale | None = None`。

`FunctionalRole` 值（顺序/分组照 spec §4）：高方差失败源 / 恐惧张力 / 节奏压缩器 / 竞技对抗 / 掌握曲线 / 操作快感 / 系统优化 / 解题洞察 / 认知降负载 / 涌现源 / 资源张力 / 成长权力 / 收集驱动 / 社交放大器 / 探索驱动 / 沉浸氛围 / 叙事钩子 / 创造表达 / 放松抚慰 / 情感羁绊。

```python
class SynergyRule(StrictBaseModel):
    id: str = Field(min_length=1)
    role_a: FunctionalRole
    role_b: FunctionalRole
    experience: str = Field(min_length=1)
    evidence_games: list[NonEmptyStr] = Field(default_factory=list)

class SynergyRationale(StrictBaseModel):
    rule_id: str = Field(min_length=1)
    anchor_role: FunctionalRole
    borrowed_role: FunctionalRole
    predicted_experience: str = Field(min_length=1)
```

- [ ] **Step 4: 跑测试确认通过** + `python -m pytest tests/test_opportunity_schemas.py -q`
- [ ] **Step 5: 提交** — `feat(backend): add FunctionalRole/SynergyRule schema + optional candidate synergy`

---

## Task 2: 数据表 + 加载/推导模块 `services/synergy.py`

**Files:** Create `app/fixtures/element_roles.json`、`app/fixtures/synergy_rules.json`、`app/services/synergy.py`、`tests/test_synergy.py`

- [ ] **Step 1: 写失败测试** —— `tests/test_synergy.py`：
```python
from app.schemas.opportunity import FunctionalRole, SynergyRule
from app.services import synergy

def test_element_roles_classify_known_terms() -> None:
    table = synergy.load_element_roles()
    assert FunctionalRole.HIGH_VARIANCE_FAILURE in table["老虎机"]
    assert FunctionalRole.COGNITIVE_OFFLOAD in table["老虎机"]
    assert FunctionalRole.SOCIAL_AMPLIFIER in table["共享账户"]
    assert FunctionalRole.DREAD_SOURCE in table["生存恐怖"]      # Theme/Genre 来源
    assert FunctionalRole.VISCERAL_EXECUTION in table["爽快射击"]  # GameFeel 来源

def test_roles_for_elements_unions_four_dims() -> None:
    roles = synergy.roles_for_elements(["老虎机", "共享账户", "轻松休闲", "生存恐怖"])
    assert {FunctionalRole.HIGH_VARIANCE_FAILURE, FunctionalRole.SOCIAL_AMPLIFIER,
            FunctionalRole.COZY_COMFORT, FunctionalRole.DREAD_SOURCE} <= roles
    assert synergy.roles_for_elements(["不存在的词"]) == set()

def test_synergy_rules_load_and_cover_all_roles() -> None:
    rules = synergy.load_synergy_rules()
    assert all(isinstance(r, SynergyRule) for r in rules)
    covered = {r.role_a for r in rules} | {r.role_b for r in rules}
    assert covered == set(FunctionalRole)   # 每个角色至少被一条规则覆盖

def test_find_synergy_symmetric_hit() -> None:
    hit = synergy.find_synergy({FunctionalRole.HIGH_VARIANCE_FAILURE},
                               {FunctionalRole.SOCIAL_AMPLIFIER})
    assert hit is not None
    rule, anchor_role, borrowed_role = hit
    assert anchor_role == FunctionalRole.HIGH_VARIANCE_FAILURE
    assert borrowed_role == FunctionalRole.SOCIAL_AMPLIFIER
    # 反方向也命中
    rev = synergy.find_synergy({FunctionalRole.SOCIAL_AMPLIFIER},
                               {FunctionalRole.HIGH_VARIANCE_FAILURE})
    assert rev is not None and rev[1] == FunctionalRole.SOCIAL_AMPLIFIER

def test_find_synergy_miss() -> None:
    assert synergy.find_synergy({FunctionalRole.NARRATIVE_HOOK},
                                {FunctionalRole.COGNITIVE_OFFLOAD}) is None

def test_rationale_for_combine() -> None:
    r = synergy.rationale_for(["共享账户"], "老虎机")
    assert r is not None and r.predicted_experience == "欢乐混乱"
    assert synergy.rationale_for(["分支叙事"], "回合制") is None
```

- [ ] **Step 2: 跑测试确认失败** — ModuleNotFoundError `app.services.synergy`。

- [ ] **Step 3: 实现**
  - `element_roles.json`：`{"version":1,"description":…,"roles":{角色值:[四段词…]}}`，内容照 spec §4 各角色「主来源」分类填充（Mechanic 为主，补 GameFeel/Theme/Genre）。**关键校验词**（测试依赖）：`老虎机`∈{高方差失败源,认知降负载}、`共享账户`∈{社交放大器}、`生存恐怖`∈{恐惧张力}、`爽快射击`∈{操作快感}、`轻松休闲`∈{放松抚慰}。
  - `synergy_rules.json`：照 spec §5 的 20 条；规则覆盖全部 20 角色（测试 `covered == set(FunctionalRole)` 强制）。
  - `services/synergy.py`：
```python
from __future__ import annotations
import json
from collections import defaultdict
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from app.schemas.opportunity import FunctionalRole, SynergyRationale, SynergyRule

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

@lru_cache(maxsize=1)
def load_element_roles() -> dict[str, frozenset[FunctionalRole]]:
    raw = json.loads((_FIXTURES / "element_roles.json").read_text(encoding="utf-8"))
    table: dict[str, set[FunctionalRole]] = defaultdict(set)
    for role_value, terms in raw["roles"].items():
        role = FunctionalRole(role_value)           # 非法角色键响亮失败
        for term in terms:
            table[term].add(role)
    return {term: frozenset(roles) for term, roles in table.items()}

@lru_cache(maxsize=1)
def load_synergy_rules() -> tuple[SynergyRule, ...]:
    raw = json.loads((_FIXTURES / "synergy_rules.json").read_text(encoding="utf-8"))
    return tuple(SynergyRule.model_validate(r) for r in raw["rules"])

def roles_for_elements(elements, table=None) -> set[FunctionalRole]:
    lookup = load_element_roles() if table is None else table
    out: set[FunctionalRole] = set()
    for e in elements:
        out |= lookup.get(e, frozenset())
    return out

def find_synergy(anchor_roles, borrowed_roles, rules=None):
    for rule in (load_synergy_rules() if rules is None else rules):
        if rule.role_a in anchor_roles and rule.role_b in borrowed_roles:
            return rule, rule.role_a, rule.role_b
        if rule.role_b in anchor_roles and rule.role_a in borrowed_roles:
            return rule, rule.role_b, rule.role_a
    return None

def rationale_for(anchor_elements, borrowed_mechanic, *, table=None, rules=None) -> SynergyRationale | None:
    lookup = load_element_roles() if table is None else table
    hit = find_synergy(roles_for_elements(anchor_elements, lookup),
                       set(lookup.get(borrowed_mechanic, frozenset())), rules)
    if hit is None:
        return None
    rule, a_role, b_role = hit
    return SynergyRationale(rule_id=rule.id, anchor_role=a_role,
                            borrowed_role=b_role, predicted_experience=rule.experience)
```

- [ ] **Step 4: 跑测试确认通过** — `python -m pytest tests/test_synergy.py -q`
- [ ] **Step 5: 提交** — `feat(backend): add element_roles + synergy_rules tables and synergy service`

---

## Task 3: `GameDimensions` 携带 theme/game_feel + 取数扩展

**Files:** Modify `app/services/opportunity_service.py`、`app/graph/opportunity_repository.py`、`tests/test_opportunity_repository_integration.py`

- [ ] **Step 1: 写失败测试（集成，默认 deselect）** —— 在仓库集成测试追加：入库一款 fixture 后 `fetch_game_dimensions()` 返回的对象 `.theme` 与 `.game_feel` 非空 set。

- [ ] **Step 2: 跑测试确认失败/skip** — 无 `NEO4J_PASSWORD` → SKIP；有活库 → `AttributeError`（无 `theme`）。

- [ ] **Step 3: 实现**
  - `GameDimensions` **末位**新增 `theme: set[str] = field(default_factory=set)`、`game_feel: set[str] = field(default_factory=set)`（末位带默认 → 既有 positional 构造 `GameDimensions("g","s",{..},{..},{..},{..})` 不破）。
  - `_FETCH_QUERY` 增两行：`[(g)-[:HAS_THEME]->(x)|x.name] AS theme`、`[(g)-[:HAS_GAME_FEEL]->(x)|x.name] AS game_feel`；`_read_dimensions` 构造时带上。

- [ ] **Step 4: 跑测试确认通过/skip** + 全量 `python -m pytest -q`（无 neo4j 时集成 SKIP，其余全绿）。
- [ ] **Step 5: 提交** — `feat(backend): fetch theme/game_feel into GameDimensions for role derivation`

---

## Task 4: 枚举标注 synergy + `rank_candidates` 协同优先

**Files:** Modify `app/services/opportunity_service.py`、`tests/test_opportunity_enumeration.py`

- [ ] **Step 1: 写失败测试** ——
```python
# 锚点含「共享账户」，库里有游戏带「老虎机」可借入 → 该 COMBINE 候选应带 synergy
def test_combine_candidate_annotated_with_synergy() -> None:
    games = [
        GameDimensions("g_party","派对", {"派对游戏"}, set(), set(), {"共享账户"}, set(), set()),
        GameDimensions("g_slot","赌场", {"派对游戏"}, set(), set(), {"老虎机"}, set(), set()),
    ]
    cands = enumerate_candidates(games)
    borrow = next(c for c in cands if c.anchor_game_id=="g_party"
                  and c.transformation.to_value=="老虎机")
    assert borrow.synergy is not None
    assert borrow.synergy.predicted_experience == "欢乐混乱"

def test_rank_prioritizes_synergy_over_pure_scarcity() -> None:
    # 构造：A 命中 synergy 但 existing=1；B 无 synergy 但 existing=0
    ranked = rank_candidates([_cand_syn("A", existing=1), _cand("B", existing=0, target=1)])
    assert ranked[0].id == "A"   # synergy 优先于更稀缺
```
（`GameDimensions` 现在 8 位：注意补 theme/game_feel 两个 set 占位。`_cand_syn` 为带 `synergy` 的工厂。）

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现**
  - `_combine_candidates`：构造候选后，用 `synergy.rationale_for(anchor 的四段元素, target_mechanic)` 求理由并赋给候选 `synergy`。锚点四段元素 = `anchor.mechanics | anchor.game_feel | anchor.theme | anchor.genre`。
  - `rank_candidates`：主排序键前置「`c.synergy is None`」（False 即命中排前），其后沿用 `(existing_combination_count, -len(target), id)`；配额/兜底第二遍不变。以 `os.environ.get("SYNERGY_RANKING","1")!="0"` 控制：flag 关时回退为原排序且不标 synergy（保证零回归）。

- [ ] **Step 4: 跑测试确认通过** + `python -m pytest tests/test_opportunity_enumeration.py tests/test_opportunity_service.py -q`
- [ ] **Step 5: 提交** — `feat(backend): annotate combine candidates with synergy and rank synergy-first`

---

## Task 5: 框架证据接入 + 全量回归

**Files:** Modify `app/services/opportunity_frame_service.py`、`tests/test_opportunity_frame_service.py`

- [ ] **Step 1: 写失败测试** —— `build_frame` 输入一个带 `synergy` 的 area，`evidence_path` 含一行包含 `predicted_experience` 与两个角色名的协同推理。

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** —— `_evidence_path(area)`：若 `area.synergy` 非 None，追加：
`f"协同：锚点提供「{r.anchor_role}」，借入补「{r.borrowed_role}」，模式预测「{r.predicted_experience}」"`。

- [ ] **Step 4: 全量回归** —— `python -m pytest -q`（flag 默认开），预期 0 failed；再 `SYNERGY_RANKING=0 python -m pytest -q` 验证 flag 关时零回归。
- [ ] **Step 5: 提交** — `feat(backend): surface synergy rationale in opportunity frame evidence path`

---

## Self-Review

- **Spec 覆盖**：§3 契约→Task1/2；§4 角色表→Task2 element_roles；§5 规则表→Task2 synergy_rules（`covered==set(FunctionalRole)` 强制全覆盖）；§6.1 取数→Task3；§6.2 推导→Task2；§6.3 标注→Task4；§6.4 排序→Task4（flag）；§6.5 框架→Task5；§8 测试逐条对应。
- **零改动边界自检**：无 `GameDesignProfile` 改动、无 `import_service`/`game_repository` 写路径改动、无 fixture 回填、无图谱结构改动。Task3 仅扩只读取数。✓
- **类型一致**：`GameDimensions` 增至 8 字段（末位带默认，positional 兼容）；`rationale_for` 签名 Task2 定义、Task4 调用一致；`CandidateOpportunityArea.synergy` Task1 定义、Task4 赋值、Task5 读取一致。
- **回归保护**：flag `SYNERGY_RANKING=0` 时不标 synergy、排序回退原键 → 既有 6.5/6.6 测试不变；Task5 Step4 显式双跑验证。
- **已知局限**（spec §10）：三薄角色、角色内在属性简化、SUBSTITUTE 暂不协同——均为预期，非缺陷。
