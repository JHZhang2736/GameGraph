# 6.5 候选多样性选择 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `rank_candidates` 在保持新颖度为主排序信号的前提下,按锚点游戏(主轴)和变形维度(次轴)做确定性多样性选择,避免单次结果被同一游戏/同一变形的近似变体占满。

**Architecture:** 改后端单个函数 `rank_candidates`:新颖度排序后,改「硬取 top_n」为「双重配额贪心(每锚点 ≤ MAX_PER_ANCHOR、每维度 ≤ MAX_PER_DIMENSION)+ 放宽兜底(凑不满按新颖度补齐)」。纯确定性,无 RNG。仅在已枚举的有证据候选里选,不越界。

**Tech Stack:** Python 3.12、Pydantic v2、pytest(后端,从 `backend/` 跑;默认 `-m 'not integration'`)。

**约定:** 命令从 `backend/` 跑;git 从 worktree 根跑(路径含 `backend/`)。基线:`python -m pytest -q` = 161 passed, 5 deselected。

参考 spec:`docs/superpowers/specs/2026-06-09-opportunity-candidate-diversity-design.zh-CN.md`

---

### Task 1: 双重配额多样性选择

**Files:**
- Modify: `backend/app/services/opportunity_service.py`(新增两个常量;重写 `rank_candidates` 函数体并加两个带默认值的参数)
- Test: `backend/tests/test_opportunity_enumeration.py`(新增多样性夹具 `_dcand` + 5 个测试)

- [ ] **Step 1: 新增配额常量**

在 `backend/app/services/opportunity_service.py` 中,`TOP_N = int(os.environ.get("LLM_MAX_CANDIDATES", "10"))` 这一行**之后**新增:

```python
MAX_PER_ANCHOR = 2      # 多样性主轴:同一锚点游戏最多 2 条变体
MAX_PER_DIMENSION = 5   # 多样性次轴软护栏:防止一种变形维度极端霸屏
```

- [ ] **Step 2: 写失败测试(多样性夹具 + 5 个用例)**

在 `backend/tests/test_opportunity_enumeration.py` 末尾(现有 `test_rank_truncates_to_top_n` 之后)追加。先加一个能变 anchor / dimension / to_value 的夹具(现有 `_cand` 只造 `anchor="a"`/`Mechanic`,不够用),再加 5 个用例:

```python
def _dcand(
    cid: str,
    existing: int,
    target: int,
    anchor: str,
    dimension: str,
    to_value: str | None = None,
) -> CandidateOpportunityArea:
    # 替代类维度必须带 from_value(schema 校验);组合类(Mechanic)from_value 为 None
    is_combine = dimension == "Mechanic"
    return CandidateOpportunityArea(
        id=cid,
        anchor_game_id=anchor,
        anchor_summary="s",
        transformation=Transformation(
            type=TransformationType.COMBINE if is_combine else TransformationType.SUBSTITUTE,
            dimension=dimension,
            from_value=None if is_combine else "x",
            to_value=to_value or cid,
        ),
        existing_combination_count=existing,
        evidence=OpportunityEvidence(
            anchor_game_id=anchor,
            target_value_game_ids=[f"g{i}" for i in range(target)],
            combination_game_ids=[f"c{i}" for i in range(existing)],
        ),
    )


def test_rank_caps_candidates_per_anchor() -> None:
    # 锚点 a 有 5 条同样新颖的候选;b、c 各 2 条。top_n 正好等于配额能给的总数,
    # 放宽兜底不触发,从而验证锚点配额生效(a 本来 5 条,被压到 2 条)。
    cands = (
        [_dcand(f"a{i}", 0, 1, "a", "Mechanic") for i in range(5)]
        + [_dcand(f"b{i}", 0, 1, "b", "Genre") for i in range(2)]
        + [_dcand(f"c{i}", 0, 1, "c", "ArtStyle") for i in range(2)]
    )
    ranked = rank_candidates(
        cands, max_existing=2, top_n=6, max_per_anchor=2, max_per_dimension=5
    )
    anchors = [c.anchor_game_id for c in ranked]
    assert anchors.count("a") == 2
    assert anchors.count("b") == 2
    assert anchors.count("c") == 2


def test_rank_caps_candidates_per_dimension() -> None:
    # 6 条都是 Perspective 维度,但分属 6 个不同锚点,锚点配额永不触发,
    # 只有维度配额能限制 → 取 5 不取 6。
    cands = [
        _dcand(f"p{i}", 0, 1, f"anchor{i}", "Perspective", to_value=f"v{i}")
        for i in range(6)
    ]
    ranked = rank_candidates(
        cands, max_existing=2, top_n=5, max_per_anchor=2, max_per_dimension=5
    )
    persp = [c for c in ranked if c.transformation.dimension == "Perspective"]
    assert len(persp) == 5


def test_rank_relaxes_caps_when_underfilled() -> None:
    # 只有单一锚点 a 的 5 条候选;配额本会只给 2,但 top_n=5 要求放宽兜底补满。
    cands = [_dcand(f"a{i}", 0, 1, "a", "Mechanic") for i in range(5)]
    ranked = rank_candidates(
        cands, max_existing=2, top_n=5, max_per_anchor=2, max_per_dimension=5
    )
    assert len(ranked) == 5
    assert {c.id for c in ranked} == {"a0", "a1", "a2", "a3", "a4"}


def test_rank_keeps_global_most_novel_first() -> None:
    cands = [
        _dcand("most_novel", 0, 5, "b", "Genre"),
        _dcand("mid", 0, 1, "c", "ArtStyle"),
        _dcand("less_novel", 1, 9, "a", "Mechanic"),
    ]
    ranked = rank_candidates(
        cands, max_existing=2, top_n=10, max_per_anchor=2, max_per_dimension=5
    )
    assert ranked[0].id == "most_novel"


def test_rank_diversity_is_deterministic() -> None:
    cands = (
        [_dcand(f"a{i}", 0, 1, "a", "Mechanic") for i in range(4)]
        + [_dcand(f"b{i}", 0, 2, "b", "Genre") for i in range(4)]
        + [_dcand(f"c{i}", 1, 1, "c", "ArtStyle") for i in range(4)]
    )
    r1 = [c.id for c in rank_candidates(cands, max_existing=2, top_n=8)]
    r2 = [c.id for c in rank_candidates(list(reversed(cands)), max_existing=2, top_n=8)]
    assert r1 == r2
```

（`CandidateOpportunityArea`、`Transformation`、`TransformationType`、`OpportunityEvidence`、`rank_candidates` 在该测试文件顶部已 import,无需新增 import。）

- [ ] **Step 3: 运行新测试确认失败**

Run: `python -m pytest tests/test_opportunity_enumeration.py -k "caps or relaxes or most_novel or diversity_is_deterministic" -v`
Expected: 至少 `test_rank_caps_candidates_per_anchor` 与 `test_rank_caps_candidates_per_dimension` FAIL(当前 `rank_candidates` 无配额,会把 a 的 5 条/Perspective 的 6 条全取)。其余几条可能因当前实现恰好满足而通过——无妨,它们是行为护栏。

- [ ] **Step 4: 重写 `rank_candidates`**

把 `backend/app/services/opportunity_service.py` 中现有的 `rank_candidates` 整个函数替换为:

```python
def rank_candidates(
    candidates: list[CandidateOpportunityArea],
    max_existing: int = MAX_EXISTING_COMBINATIONS,
    top_n: int = TOP_N,
    max_per_anchor: int = MAX_PER_ANCHOR,
    max_per_dimension: int = MAX_PER_DIMENSION,
) -> list[CandidateOpportunityArea]:
    viable = [c for c in candidates if c.existing_combination_count <= max_existing]
    viable.sort(
        key=lambda c: (
            c.existing_combination_count,
            -len(c.evidence.target_value_game_ids),
            c.id,
        )
    )

    selected: list[CandidateOpportunityArea] = []
    selected_ids: set[str] = set()
    per_anchor: dict[str, int] = {}
    per_dimension: dict[str, int] = {}

    # 第一遍:带配额贪心(从最新颖往下),主轴锚点、次轴维度
    for c in viable:
        if len(selected) >= top_n:
            break
        anchor = c.anchor_game_id
        dimension = c.transformation.dimension
        if (
            per_anchor.get(anchor, 0) < max_per_anchor
            and per_dimension.get(dimension, 0) < max_per_dimension
        ):
            selected.append(c)
            selected_ids.add(c.id)
            per_anchor[anchor] = per_anchor.get(anchor, 0) + 1
            per_dimension[dimension] = per_dimension.get(dimension, 0) + 1

    # 第二遍:放宽兜底——配额导致没凑满时,用剩余候选按新颖度补齐
    if len(selected) < top_n:
        for c in viable:
            if len(selected) >= top_n:
                break
            if c.id not in selected_ids:
                selected.append(c)
                selected_ids.add(c.id)

    return selected
```

- [ ] **Step 5: 运行新测试确认通过**

Run: `python -m pytest tests/test_opportunity_enumeration.py -k "caps or relaxes or most_novel or diversity_is_deterministic" -v`
Expected: PASS（5 个新用例全绿）。

- [ ] **Step 6: 全量回归(含现有 rank 测试)**

Run: `python -m pytest -q`
Expected: 全绿。现有 `test_rank_filters_out_candidates_above_ceiling` / `test_rank_sorts_by_scarcity_then_target_attestation` / `test_rank_truncates_to_top_n` 用 `anchor="a"`/`Mechanic` 均匀夹具,放宽兜底使其断言(成员/顺序/长度)仍成立,**应无需修改**。若个别因新行为失败,按新行为更新该断言(例如顺序断言改为集合断言)后再次运行至全绿。

- [ ] **Step 7: 提交**

```bash
git add backend/app/services/opportunity_service.py backend/tests/test_opportunity_enumeration.py
git commit -m "feat(opportunity): diversity-aware candidate selection (per-anchor/dimension caps)"
```
提交信息末尾空一行追加:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## 自检结果

**Spec 覆盖:** §3 算法 → Step 4;§4 常量 → Step 1;§5 行为保证(新颖度优先/放宽/确定性)→ Step 2 的对应用例;§6 测试(5 新 + 回归)→ Step 2/5/6。无遗漏。

**占位符扫描:** 无 TBD/TODO;每个改代码的步骤都给了完整代码。

**类型/签名一致性:** `rank_candidates` 新签名 `(candidates, max_existing, top_n, max_per_anchor, max_per_dimension)` 与测试调用一致;`_dcand` 产出的 `Transformation` 满足 schema(替代带 `from_value="x"`,组合为 `None`);`MAX_PER_ANCHOR`/`MAX_PER_DIMENSION` 定义(Step 1)与使用(Step 4 默认值)一致。
