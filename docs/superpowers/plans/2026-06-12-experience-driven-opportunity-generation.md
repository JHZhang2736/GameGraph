# 体验/角色驱动的机会生成重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development。逐任务 TDD，步骤用 `- [ ]`。

**Goal:** 全量替换旧机会生成：以「desired_player_experiences → 协同规则 → 角色配方 → 图谱实例化」为唯一生成入口（`enumerate_opportunities`），角色级新颖度（`role_combination_count`）取代属性值稀缺度，属性稀缺度降级为 wildcard 次级通道。删除 SUBSTITUTE 生成与旧 `enumerate_candidates` 编排；复用 combine/稀缺度机器于 wildcard。无运行时 flag。

**Architecture:** 相位推进，套件每步可控：① 加性引入新生成器（旧码不动，套件绿）→ ② 切 `match_opportunities` + `rank_candidates` 改写 + 改 match 测试 → ③ 删旧（substitute、旧 enumerate）+ 改写枚举/frame 测试 + 修 `_secondary_pool` → ④ 验证 harness + 全绿。

**Tech Stack:** Python 3.12 / Pydantic v2 / pytest。**Spec:** `docs/superpowers/specs/2026-06-12-experience-driven-opportunity-generation-design.zh-CN.md`。

命令在 `backend/` 下；本分支 stacked 在 PR #44 之上。

---

## E-Task 1: `role_combination_count` + `enumerate_opportunities`（加性，不删旧）

**Files:** Modify `app/services/opportunity_service.py`、`tests/test_opportunity_enumeration.py`

- [ ] **Step 1: 失败测试**
```python
def test_role_combination_count_counts_games_covering_both_roles() -> None:
    games = [
        GameDimensions("g1","s1",{"派对游戏"},set(),set(),{"老虎机"},set(),set()),   # 社交?+高方差(老虎机)... 用真实词
        ...]
    # 断言：库内同时覆盖 {高方差失败源, 社交放大器} 的游戏计数正确；无共现=0

def test_enumerate_opportunities_recipe_channel(monkeypatch) -> None:
    # 锚点覆盖高方差失败源，库内有社交放大器源；desired={"欢乐混乱"}
    opps = enumerate_opportunities(games, desired={"欢乐混乱"})
    c = next(o for o in opps if o.synergy and o.synergy.predicted_experience=="欢乐混乱")
    assert c.transformation.type == TransformationType.COMBINE
    assert c.existing_combination_count == role_combination_count(games, c.synergy.anchor_role, c.synergy.borrowed_role)

def test_enumerate_opportunities_default_uses_all_rule_experiences() -> None:
    opps = enumerate_opportunities(games, desired=set())   # 空 → 全规则
    assert opps  # 非空

def test_enumerate_opportunities_wildcard_present_and_capped() -> None:
    # 含一个无规则、稀缺的机制借入 → 进结果，synergy=None，受 MAX_WILDCARD 限
    ...

def test_enumerate_opportunities_no_substitute() -> None:
    opps = enumerate_opportunities(games, desired=set())
    assert all(o.transformation.type == TransformationType.COMBINE for o in opps)
```

- [ ] **Step 2: 实现**（`opportunity_service.py`，新增，不动旧函数）
  - `role_combination_count(games, role_a, role_b) -> int`：`sum(1 for g in games if {role_a, role_b} <= roles_for_elements(g 的来源段元素))`。来源段元素 = `g.mechanics|g.game_feel|g.theme|g.genres`（#44 核心四段；抽一个 `_source_elements(g)` helper 复用）。
  - `MAX_WILDCARD = int(os.environ.get("OPP_MAX_WILDCARD", "3"))`（默认小数，可调）。
  - `enumerate_opportunities(games, desired: set[str]) -> list[CandidateOpportunityArea]`：
    - 主通道按 spec §4.1（target_rules 过滤、对称方向、`load_elements_by_role`、evidence 非空、按 cid 去重、`existing_combination_count=role_combination_count`、带 synergy）。
    - wildcard 通道按 spec §4.2：对每锚点每个 `anchor.mechanics` 之外的机制 `m`，若 `synergy.rationale_for(_source_elements(anchor), m) is None`（无规则），作 `synergy=None` 候选、`existing_combination_count`=属性组合数（`_combination_game_ids`）；全局按稀缺度排序后取前 `MAX_WILDCARD`。
    - 合并：主通道 + wildcard，按 cid 去重（主通道优先保留）。
  - 复用 `_games_with_value`/`_combination_game_ids`/`_candidate_id`/`_DIMENSION_ATTRS`/`synergy.*`。
- [ ] **Step 3: 跑** `tests/test_opportunity_enumeration.py` 绿；全量 `python -m pytest -q` 仍绿（旧码未动）。
- [ ] **Step 4: 提交** `feat(backend): add experience/role recipe opportunity generator (role-combination novelty + wildcard)`

---

## E-Task 2: `rank_candidates` 改写 + `match_opportunities` 切到新生成器

**Files:** Modify `app/services/opportunity_service.py`、`tests/test_opportunity_service.py`、`tests/test_opportunity_api.py`

- [ ] **Step 1: 失败测试** —— `match_opportunities` 用 stub repo（games）+ stub llm，断言其候选来自 recipe（带 synergy/predicted_experience，无 SUBSTITUTE）；画像 `desired_player_experiences` 命中体验的候选排前。改写既有 match/api 测试断言以匹配新候选形态。
- [ ] **Step 2: 实现**
  - `rank_candidates`：主键 `(画像档, existing_combination_count, -len(target_value_game_ids), id)`。画像档：synergy 且 `predicted_experience∈desired`→0；synergy→1；无 synergy(wildcard)→2。沿用多样性配额与两遍贪心。（与 #44 三档同构，去掉 `_synergy_enabled` flag 依赖——新路恒启。）
  - `match_opportunities`：`enumerate_opportunities(games, set(profile.desired_player_experiences))` 替换 `enumerate_candidates(games)`；`seen_ids`/judge/降级/warnings 不变。
- [ ] **Step 3: 跑** `tests/test_opportunity_service.py tests/test_opportunity_api.py` 绿；全量仍绿（旧 `enumerate_candidates` 仍存在但 match 不再用它——其专属枚举测试到 E-Task 3 才清理，此刻仍绿因旧函数还在）。
- [ ] **Step 4: 提交** `feat(backend): rank recipe candidates and wire match_opportunities to experience-driven generation`

---

## E-Task 3: 删旧生成 + 修 `_secondary_pool` + 改写枚举/frame 测试

**Files:** Modify `app/services/opportunity_service.py`、`app/services/opportunity_frame_service.py`、`tests/test_opportunity_enumeration.py`、`tests/test_opportunity_frame_service.py`

- [ ] **Step 1: 改写测试** —— 删除/改写断言旧 `enumerate_candidates`/`_substitute_candidates` 行为的测试为断言 `enumerate_opportunities`；frame `_secondary_pool` 相关测试改为新来源。
- [ ] **Step 2: 实现**
  - **删除** `_substitute_candidates`、旧 `enumerate_candidates` 编排、`_rule_driven_candidates`（其逻辑已并入 `enumerate_opportunities` 主通道——确认无其他引用后删）。**保留** `_combine_candidates`？若 wildcard 已不依赖它（E-Task 1 wildcard 直接用 helpers + `rationale_for`），则一并删 `_combine_candidates`；否则保留供 wildcard。plan 执行时按实际引用决定，删前 `git grep` 确认。
  - **修 `opportunity_frame_service._secondary_pool`**：原先 `enumerate_candidates(games)` 过滤同锚点。改为 `enumerate_opportunities(games, desired=set())` 后过滤 `anchor_game_id==area.anchor_game_id and id!=area.id`（desired=∅ 取全规则空间，保证同锚点次变形池非空）。
  - **微调 `_evidence_path`**：带 synergy 的候选，"现存游戏数=N" 行措辞改为"已有该角色配方的游戏数=N（越小越新颖）"。
- [ ] **Step 3: 跑** 全量 `python -m pytest -q` 绿（改写后）。`git grep enumerate_candidates`/`_substitute_candidates` 确认无残留引用。
- [ ] **Step 4: 提交** `refactor(backend): remove substitute/legacy enumeration, route secondary pool through recipe generator`

---

## E-Task 4: 验证 harness + 全量绿

**Files:** Modify `backend/tests/test_hybrid_validation.py`（或新建 `test_recipe_validation.py`）

- [ ] **Step 1: 验证测试**（spec §6，内存 GameDimensions）
  - **哑候选占比**：recipe Top-N 中 `synergy is None` 占比 ≤ wildcard 配额比例。
  - **画像靶向**：desired={体验} 时 Top-N 命中/相关体验占比高于 desired=∅。
  - **留一法重新发现**：移除某配方代表作后仍生成对应机会并靠前。
  - **wildcard 发现**：≥1 个无规则极稀缺候选。
  - **角色级新颖度**：被多游戏共现的角色组合新颖度更高（值更大→排后）。
  - **无 SUBSTITUTE**：`enumerate_opportunities` 产物无 substitute。
- [ ] **Step 2: 全量** `python -m pytest -q` 绿。
- [ ] **Step 3: 提交** `test(backend): recipe-driven generation validation harness`

---

## Self-Review
- **Spec 覆盖**：§3.1 新颖度→E1；§4.1 主通道→E1；§4.2 wildcard→E1；§4.3 排序→E2；§5 编排→E2；删旧+secondary_pool→E3；§6 验证→E4。
- **相位安全**：E1 加性(套件绿)；E2 切换(改 match 测试)；E3 删旧(改枚举/frame 测试 + 修 secondary_pool)；E4 验证。每步可独立跑绿。
- **替换完整性**：E3 后无 `enumerate_candidates`/substitute 残留引用(grep 守卫)；`match`/`_secondary_pool` 均走 recipe。
- **schema 不变**：复用 `existing_combination_count`，无 schema 改动。
- **已知**：本分支 stacked 在 #44；薄角色多来源段(C)、替换协同(B)为 parked 正交项。
