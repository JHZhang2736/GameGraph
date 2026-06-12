# 混合机会枚举 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development（推荐）或 executing-plans，逐任务实现。步骤用 `- [ ]`。

**Goal:** 在 PR #43 协同层之上，把协同从「只排序」推进到「也参与生成、且对开发者个性化」，严格保持混合（属性枚举不删、角色永不替换属性）。三件事：① `element_roles.json` 按维度重组 + synergy 反查；② 规则驱动跨维度候选生成器（借入 Theme/GameFeel/Genre 完成协同），与属性产物并集去重；③ 画像感知协同加权。

**Architecture:** 纯加性叠加层。规则驱动生成与画像加权全部在 `_synergy_enabled()`（`SYNERGY_RANKING`，默认开）下，关闭即字节级回退到 PR #43 行为。仍不进图谱、不改 import / GameDesignProfile schema / fixture。

**Tech Stack:** Python 3.12 / Pydantic v2 / pytest。

**Spec:** `docs/superpowers/specs/2026-06-12-hybrid-opportunity-enumeration-design.zh-CN.md`（§2 不变量、§4.1 生成器为核心）。

命令在 `backend/` 下执行：`cd D:\Files\GameGraph\.claude\worktrees\hybrid-opportunity-enumeration\backend`（worktree 跑测试必须 cd 到 backend/）。`SYNERGY_RANKING=0` 用于零回归双跑。

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `backend/app/fixtures/element_roles.json` | `role -> [terms]` 重组为 `role -> {dim: [terms]}` | Modify(重写) |
| `backend/app/services/synergy.py` | `load_element_roles` 从新结构 flatten（行为不变）；新增 `load_element_dimensions` / `elements_for_role` | Modify |
| `backend/app/services/opportunity_service.py` | `_DIMENSION_ATTRS`；新增 `_rule_driven_candidates`；`enumerate_candidates` 并集去重；`rank_candidates` 加 `desired_experiences` 三档；`match_opportunities` 传画像 | Modify |
| `backend/tests/test_synergy.py` | 维度反查 + flatten 不变量 | Modify |
| `backend/tests/test_opportunity_enumeration.py` | 跨维度生成 / 去重 / 属性发现不丢 / 画像三档 / 零回归 | Modify |
| `backend/tests/test_opportunity_service.py` | match 传画像加权 | Modify |
| `backend/tests/test_hybrid_validation.py` | 留一法 + 跨维度可达性 + 消融 | Create |

**关键不变量（必须落到测试）：** 重组后 `load_element_roles()` flatten 结果与重组前**逐角色逐词完全一致**；`SYNERGY_RANKING=0` 时 `enumerate_candidates`/`rank_candidates` 输出与 PR #43 逐候选一致；不命中规则的纯稀缺 combine 候选在混合枚举中仍存在。

---

## Task 1: `element_roles.json` 按维度重组 + synergy 反查表

**Files:** Modify `app/fixtures/element_roles.json`、`app/services/synergy.py`、`tests/test_synergy.py`

- [ ] **Step 1: 写失败测试**（append `tests/test_synergy.py`）
```python
def test_element_dimensions_lookup() -> None:
    dims = synergy.load_element_dimensions()
    assert "Mechanic" in dims["老虎机"]
    assert "GameFeel" in dims["爽快射击"]
    assert "Theme" in dims["生存恐怖"]
    assert "Genre" in dims["生存恐怖"]      # 生存恐怖 同属 Theme 与 Genre
    assert dims.get("不存在的词") in (None, set())

def test_elements_for_role_returns_element_dim_pairs() -> None:
    pairs = synergy.elements_for_role(FunctionalRole.DREAD_SOURCE)
    assert ("生存恐怖", "Theme") in pairs
    assert ("紧张节奏", "GameFeel") in pairs
    assert ("理智系统", "Mechanic") in pairs

def test_flatten_unchanged_after_regroup() -> None:
    # 重组只是按维度分桶，flatten 必须和重组前逐角色逐词一致
    table = synergy.load_element_roles()
    assert FunctionalRole.HIGH_VARIANCE_FAILURE in table["老虎机"]
    assert FunctionalRole.COGNITIVE_OFFLOAD in table["老虎机"]
    assert FunctionalRole.SOCIAL_AMPLIFIER in table["共享账户"]
    assert FunctionalRole.VISCERAL_EXECUTION in table["爽快射击"]
    assert FunctionalRole.COZY_COMFORT in table["轻松休闲"]
```
Run `python -m pytest tests/test_synergy.py -q` → FAIL（无 load_element_dimensions）。

- [ ] **Step 2: 重写 `element_roles.json`**（按维度分桶；逐字转写，这是权威授权数据。一个词可出现在多个维度桶——刻意为之，flatten 取并集后与原表一致）：
```json
{
  "version": 2,
  "description": "角色分类表（按核心四段分桶）：role -> {Mechanic|GameFeel|Theme|Genre: [词]}；一个词可属多个角色、也可属多个维度段。游戏角色覆盖 = 其四段取值在此表的并集；跨维度生成据此知道借入元素所属段。键必须是 FunctionalRole 枚举值。",
  "roles": {
    "高方差失败源": {"Mechanic": ["永久死亡","伪永久死亡","死亡惩罚","老虎机","强制抽卡","骰子判定","骰子构筑","骰面编辑","弹幕生存","难度递增","随机道具","随机事件","随机关卡","随机变异","债务清算"], "Genre": ["类肉鸽","大逃杀"]},
    "恐惧张力": {"Mechanic": ["理智系统","追猎者","躲藏潜逃","夜视摄影","压力系统"], "Theme": ["生存恐怖","心理恐怖","宗教恐怖","灵异","人体实验","丧尸末世"], "Genre": ["生存恐怖"], "GameFeel": ["紧张节奏"]},
    "节奏压缩器": {"Mechanic": ["实时计时","限时抉择","限时搜刮","可调时长","撤离机制","逃跑序列","快速反应"]},
    "竞技对抗": {"Mechanic": ["淘汰赛制","异步对战","互动干扰","谈判战斗"], "Genre": ["大逃杀"]},
    "掌握曲线": {"Mechanic": ["连招","招架反击","吸收招架","格挡","耐力管理","牌组构筑","增益构筑","武器构筑","法杖编排","法术合成","法术编程","技能切换","技能多态","道具协同","道具叠加","遗物系统","护符定制","站位战斗","回合制网格战术"], "Genre": ["类魂"]},
    "操作快感": {"GameFeel": ["精准平台","精准近战","精准射击","厚重打击","爽快射击","流畅跑酷","流畅操作","流畅响应","动量","自由操控"], "Mechanic": ["墙面奔跑"], "Genre": ["平台跳跃"]},
    "系统优化": {"Mechanic": ["自动化","引擎构筑","殖民地管理","自动战斗","放置玩法","相邻加成","间接控制","塔防"], "Genre": ["塔防","4X策略","模拟经营","回合制策略","微策略"], "GameFeel": ["规划满足"]},
    "解题洞察": {"Mechanic": ["视角解谜","传送门","合作解谜","点击解谜","物品组合","证据推理","线索调查","可视化编程"], "Genre": ["解谜","解谜平台"]},
    "认知降负载": {"Mechanic": ["二十一点","牌型组合","老虎机","回合制","卡牌战斗","棋盘探索"], "GameFeel": ["桌游质感"]},
    "涌现源": {"Mechanic": ["物理模拟","物理碰撞","物理沙盒平台","物理抓取","智能敌人","拟态敌人","数值篡改","法术编程","无规则约束","地形改造","可破坏地形","炼金反应","传送门","时间操控","时间回溯","现实切换","关卡编辑"], "Genre": ["沙盒","物理沙盒","沉浸模拟"], "GameFeel": ["软弹物理"]},
    "资源张力": {"Mechanic": ["资源管理","债务清算","氧气管理","物资配给","商店经济","压力系统","理智系统","殖民地管理","限时搜刮","撤离机制","法令系统","进贡机制","缺陷增益","警戒度","生存模拟"], "Genre": ["生存"], "GameFeel": ["策略权衡"]},
    "成长权力": {"Mechanic": ["元进度","增益构筑","装备分层","武器构筑","灵魂货币","落败补强","道具叠加"], "Genre": ["刷宝射击"]},
    "收集驱动": {"Mechanic": ["怪物捕捉","怪物狩猎","遗物系统","护符定制","遗传繁育","合成制作","采集","建造","农场种植","装备分层","空间背包","无限背包","配方探索","酿造","顾客经营","工坊经营"], "Genre": ["怪物收集"]},
    "社交放大器": {"Mechanic": ["共享账户","近距语音","非对称协作","友伤","互动干扰","社交推理","合作生存","合作解谜","合作卡牌","同伴协助"], "Genre": ["派对游戏","合作射击"]},
    "探索驱动": {"Mechanic": ["非线性探索","开放世界探索","能力门控探索","分层秘密","翻屏房间","网格探索","棋盘探索","时间循环","区域系统","多元胜利"], "Genre": ["类银河城","开放世界"], "Theme": ["地下探险","考古探险","异星求生","太空采矿"]},
    "沉浸氛围": {"GameFeel": ["沉浸代入"], "Mechanic": ["环境叙事"], "Theme": ["超现实","自然","海洋","森林童话"], "Genre": ["叙事冒险"]},
    "叙事钩子": {"Mechanic": ["分支叙事","环境叙事","死亡叙事","交替章节","现实切换","流程图回看","记忆穿梭","请愿抉择","世代传承"], "Genre": ["叙事冒险","角色扮演","动作角色扮演"], "Theme": ["家庭情感","青春成长","犯罪悬疑","黑色电影"]},
    "创造表达": {"Mechanic": ["关卡编辑","建造","创意工坊","壁纸编辑器","动态壁纸","数值篡改"], "Genre": ["创作工具","实用软件","沙盒"]},
    "放松抚慰": {"GameFeel": ["轻松休闲"], "Theme": ["田园生活","家装","美食","玩具沙盒","公路旅行"], "Mechanic": ["房屋翻新","烹饪模拟","农场种植","顾客经营"], "Genre": ["模拟经营"]},
    "情感羁绊": {"Mechanic": ["好感系统","同伴协助","世代传承"], "Theme": ["家庭情感"]}
  }
}
```

- [ ] **Step 3: 更新 `synergy.py`** —— `load_element_roles` 改为遍历 `raw["roles"][role][dim]` 的所有 dim、union 后建 `element -> set[role]`（flatten 行为不变）。新增：
```python
_DIMENSIONS = ("Mechanic", "GameFeel", "Theme", "Genre")

@lru_cache(maxsize=1)
def load_element_dimensions() -> dict[str, frozenset[str]]:
    raw = json.loads((_FIXTURES / "element_roles.json").read_text(encoding="utf-8"))
    out: dict[str, set[str]] = defaultdict(set)
    for buckets in raw["roles"].values():
        for dim, terms in buckets.items():
            for term in terms:
                out[term].add(dim)
    return {term: frozenset(dims) for term, dims in out.items()}

@lru_cache(maxsize=1)
def elements_for_role() -> dict[FunctionalRole, frozenset[tuple[str, str]]]:
    raw = json.loads((_FIXTURES / "element_roles.json").read_text(encoding="utf-8"))
    out: dict[FunctionalRole, set[tuple[str, str]]] = defaultdict(set)
    for role_value, buckets in raw["roles"].items():
        role = FunctionalRole(role_value)
        for dim, terms in buckets.items():
            for term in terms:
                out[role].add((term, dim))
    return {role: frozenset(pairs) for role, pairs in out.items()}
```
（`elements_for_role` 提供为「角色 -> {(element,dim)}」的全量映射；测试里 `elements_for_role()[FunctionalRole.DREAD_SOURCE]`。若想要按角色取，可加一个便捷 `def elements_for(role)` 包装——按本文件既有风格选其一，测试两种写法都接受，保持签名在 Task 2 引用处一致即可。）

- [ ] **Step 4: 跑测试** `python -m pytest tests/test_synergy.py -q` 绿（含既有 6 条不变）。
- [ ] **Step 5: 提交** `feat(backend): regroup element_roles by dimension + add dimension/role reverse lookups`

---

## Task 2: 规则驱动跨维度候选生成器 + 并集去重

**Files:** Modify `app/services/opportunity_service.py`、`tests/test_opportunity_enumeration.py`

- [ ] **Step 1: 写失败测试**（GameDimensions 现 8 字段：game_id, summary, genres, perspectives, art_styles, mechanics, theme, game_feel）
```python
def test_rule_driven_generates_cross_dimension_candidate(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    # 锚点：肉鸽(高方差失败源)，无恐怖题材；库内另一游戏带 Theme 生存恐怖(恐惧张力)+资源张力
    games = [
        GameDimensions("g_rogue", "肉鸽", {"类肉鸽"}, set(), set(), {"永久死亡"}, set(), set()),
        GameDimensions("g_horror", "生存恐怖游戏", {"生存恐怖"}, set(), set(), {"资源管理"}, {"生存恐怖"}, set()),
    ]
    cands = enumerate_candidates(games)
    # 借入 Theme「生存恐怖」补恐惧张力，和锚点资源张力? —— 这里用 dread×资源 或 dread×节奏规则之一
    borrow_theme = [c for c in cands if c.anchor_game_id == "g_rogue"
                    and c.transformation.dimension == "Theme"
                    and c.transformation.to_value == "生存恐怖"]
    assert borrow_theme and borrow_theme[0].synergy is not None

def test_rule_driven_absent_when_flag_off(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "0")
    games = [...same as above...]
    cands = enumerate_candidates(games)
    assert not any(c.transformation.dimension == "Theme" for c in cands)  # 纯属性枚举生成不出跨维度借入

def test_mechanic_rule_driven_dedups_with_attribute_combine(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    games = [
        GameDimensions("g_party", "派对", {"派对游戏"}, set(), set(), {"共享账户"}, set(), set()),
        GameDimensions("g_slot", "赌场", {"派对游戏"}, set(), set(), {"老虎机"}, set(), set()),
    ]
    cands = enumerate_candidates(games)
    ids = [c.id for c in cands]
    assert len(ids) == len(set(ids))  # 无重复 id
    borrow = [c for c in cands if c.anchor_game_id == "g_party" and c.transformation.to_value == "老虎机"]
    assert len(borrow) == 1 and borrow[0].synergy is not None  # Mechanic 借入只一条且带 synergy

def test_pure_scarcity_combine_still_present(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    # 借入一个不命中任何规则的机制，仍要在枚举里（属性发现不丢）
    games = [
        GameDimensions("g1", "s1", {"解谜"}, set(), set(), {"分支叙事"}, set(), set()),
        GameDimensions("g2", "s2", {"解谜"}, set(), set(), {"回合制"}, set(), set()),
    ]
    cands = enumerate_candidates(games)
    borrow = next(c for c in cands if c.anchor_game_id == "g1" and c.transformation.to_value == "回合制")
    assert borrow.synergy is None
```
Run → FAIL。

- [ ] **Step 2: 实现** in `opportunity_service.py`
  - 新增维度→属性映射：
```python
_DIMENSION_ATTRS: dict[str, str] = {
    "Mechanic": "mechanics", "GameFeel": "game_feel", "Theme": "theme", "Genre": "genres",
}
```
  - 新增 `_rule_driven_candidates(games, anchor)`（仅 `_synergy_enabled()` 时非空）：
```python
def _rule_driven_candidates(games, anchor):
    if not _synergy_enabled():
        return []
    anchor_elements = anchor.mechanics | anchor.game_feel | anchor.theme | anchor.genres
    anchor_roles = synergy.roles_for_elements(anchor_elements)
    by_id: dict[str, CandidateOpportunityArea] = {}
    for rule in synergy.load_synergy_rules():
        for anchor_role, borrow_role in ((rule.role_a, rule.role_b), (rule.role_b, rule.role_a)):
            if anchor_role not in anchor_roles:
                continue
            for element, dim in synergy.elements_for_role()[borrow_role]:
                attr = _DIMENSION_ATTRS[dim]
                if element in getattr(anchor, attr):
                    continue  # 锚点已有
                cid = _candidate_id(anchor.game_id, "comb", dim, element)
                if cid in by_id:
                    continue  # 同候选被多条规则点亮，保留首条
                target_games = _games_with_value(games, attr, element)
                if not target_games:
                    continue  # 借入值必须在库里某游戏出现过（evidence 非空）
                combo = _combination_game_ids(games, anchor, attr, element)
                by_id[cid] = CandidateOpportunityArea(
                    id=cid, anchor_game_id=anchor.game_id, anchor_summary=anchor.summary,
                    transformation=Transformation(type=TransformationType.COMBINE, dimension=dim,
                                                  from_value=None, to_value=element),
                    existing_combination_count=len(combo),
                    evidence=OpportunityEvidence(anchor_game_id=anchor.game_id,
                                                 target_value_game_ids=target_games, combination_game_ids=combo),
                    synergy=SynergyRationale(rule_id=rule.id, anchor_role=anchor_role,
                                             borrowed_role=borrow_role, predicted_experience=rule.experience),
                )
    return list(by_id.values())
```
  （import `SynergyRationale` from `app.schemas.opportunity`。）
  - `enumerate_candidates` 改为并集 + 按 id 去重（重复时优先保留带 synergy 的）：
```python
def enumerate_candidates(games):
    by_id: dict[str, CandidateOpportunityArea] = {}
    def add(c):
        prev = by_id.get(c.id)
        if prev is None or (prev.synergy is None and c.synergy is not None):
            by_id[c.id] = c
    for anchor in games:
        for c in _substitute_candidates(games, anchor): add(c)
        for c in _combine_candidates(games, anchor): add(c)
        for c in _rule_driven_candidates(games, anchor): add(c)
    return list(by_id.values())
```
  注意：Mechanic 维度的 rule-driven 候选与 `_combine_candidates` 同 id → 去重；`_combine_candidates` 先 add（已带 synergy），rule-driven 同 id 被跳过，行为一致。

- [ ] **Step 3: 跑测试** 新测试绿。**零回归双跑**：`python -m pytest tests/test_opportunity_enumeration.py -q` 与 `SYNERGY_RANKING=0 python -m pytest tests/test_opportunity_enumeration.py -q` 均 0 failed。（flag 关时 `enumerate_candidates` 退化为 substitute∪combine，与 PR #43 同——但注意去重改写了顺序：用 dict 保插入序，substitute→combine 顺序与原 list.extend 一致，需确认既有顺序相关断言不破；若破，核对是否语义等价。）
- [ ] **Step 4: 提交** `feat(backend): rule-driven cross-dimension synergy candidate generator with union dedup`

---

## Task 3: 画像感知协同加权

**Files:** Modify `app/services/opportunity_service.py`、`tests/test_opportunity_enumeration.py`、`tests/test_opportunity_service.py`

- [ ] **Step 1: 写失败测试**
```python
def test_rank_profile_match_outranks_plain_synergy(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    # 两个都命中协同：A 预测体验 ∈ desired，B 不在 desired；A 稀缺度更差也应排前
    ranked = rank_candidates([_syn("A","欢乐混乱",existing=1), _syn("B","战斗精通",existing=0)],
                             desired_experiences={"欢乐混乱"})
    assert ranked[0].id == "A"

def test_rank_without_desired_preserves_pr43_order(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    # desired=None：协同优先于非协同，相对序与 PR #43 一致
    ...
```
（`_syn(cid, exp, existing)` 工厂：带 `synergy=SynergyRationale(...,predicted_experience=exp)`。）

- [ ] **Step 2: 实现** —— `rank_candidates` 加可选参数 `desired_experiences: set[str] | None = None`；排序主键升为三档（仅 flag 开时分档）：
```python
def _tier(c, synergy_on, desired):
    if not synergy_on or c.synergy is None:
        return 2
    if desired and c.synergy.predicted_experience in desired:
        return 0
    return 1
# key = (_tier(c, synergy_on, desired_experiences), c.existing_combination_count, -len(...), c.id)
```
  desired=None 时：协同→1、非协同→2（相对序同 PR #43 的 0/1，零回归）。`match_opportunities` 调 `rank_candidates(fresh, desired_experiences=set(profile.desired_player_experiences))`。
- [ ] **Step 3: 跑测试 + 零回归双跑**（`tests/test_opportunity_enumeration.py tests/test_opportunity_service.py`，flag 开/关均 0 failed）。
- [ ] **Step 4: 提交** `feat(backend): profile-aware synergy weighting in rank_candidates`

---

## Task 4: 验证 harness + 全量回归

**Files:** Create `backend/tests/test_hybrid_validation.py`；最后全量双跑

- [ ] **Step 1: 写验证测试**（内存 `GameDimensions` 构造，不依赖活库）
  - **留一法重新发现**：构造一组游戏含一个 PEAK 型（社交放大器 + 高方差失败源 同体），从「锚点池」移除该代表作后，验证「社交放大器 × 高方差失败源」机会区域仍因协同规则被生成并出现在 `rank_candidates(..., desired_experiences)` 的 Top-N。
  - **跨维度可达性**：构造一个只能靠 Theme/GameFeel 完成的协同（恐惧张力来自 Theme），断言混合枚举（flag 开）产出该跨维度候选，而 flag 关时不产出。
  - **消融**：同一组 games + 画像，flag 开 vs 关，断言 Top-N 候选集不同，且开时存在「画像命中(tier0)」候选。
- [ ] **Step 2: 跑** `python -m pytest tests/test_hybrid_validation.py -q` 绿。
- [ ] **Step 3: 全量双跑** `python -m pytest -q` 与 `SYNERGY_RANKING=0 python -m pytest -q` 均 0 failed。
- [ ] **Step 4: 提交** `test(backend): hybrid enumeration validation harness (leave-one-out, cross-dim, ablation)`

---

## Self-Review
- **Spec 覆盖**：§3.1 重组→T1；§3.2 反查→T1；§4.1 生成器→T2；§4.2 并集去重→T2；§4.3 画像加权→T3；§5 验证→T4；§7 测试逐条对应。
- **不变量守卫**：flatten 不变(T1 test)、属性发现不丢(T2 test)、flag 关零回归双跑(T2/T3/T4)、Mechanic 去重(T2 test)。
- **零改动边界**：无图谱/import/GameDesignProfile/fixture(游戏) 改动；`element_roles.json` 仅重组(version→2)，flatten 等价。
- **类型一致**：`_DIMENSION_ATTRS`、`elements_for_role` 返回形态、`rank_candidates` 新签名在 T1/T2/T3 引用一致；`GameDimensions` 8 字段定位。
- **已知顺序风险**：T2 把 `enumerate_candidates` 从 list.extend 改为 dict 去重——保插入序(substitute→combine→rule_driven)，需确认既有顺序相关断言等价；如破，是语义等价的顺序变化，按实际核对。
