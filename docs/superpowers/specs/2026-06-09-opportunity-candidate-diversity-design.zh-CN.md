# 6.5 候选多样性选择 设计

> 状态:已与用户对齐,待评审。属于 6.5 机会匹配的完善方向 #3(共三项:#1 前端缓存、#2 SSE 流式、#3 候选多样性——本 spec 只做 #3)。

## 1. 目标与动机

当前 `rank_candidates` 把可行候选按「新颖度」确定性排序后硬取 `[:top_n]`,导致**每次必出同一批「最稀缺」候选**,且这批很容易被**同一款锚点游戏的一堆近似变体**或**清一色同种变形**占满,读起来重复、缺乏创意。

目标:在**保持新颖度为主排序信号**的前提下,让单次结果**在种类上铺开**——主轴按锚点游戏、次轴按变形维度分散。这是 diversity-aware 的确定性选择,不引入随机(随机跨次变化是另一项 #1/未来工作)。

**契合系统哲学**:多样性选择仍然只在「确定性枚举出的、有证据支撑的候选」里挑,不让 LLM 自由发明;探索由确定性引擎做,可行性由下游 LLM 判(white-space 保留 / dead-zone 拒绝)。边界不变。

## 2. 范围

- 只改后端一个函数:`backend/app/services/opportunity_service.py` 的 `rank_candidates`。
- **不动**:`enumerate_candidates`(本就是穷举,不抑制)、`match_opportunities`、API 路由、schema、前端、LLM 层。
- 选取顺序即展示顺序,所以多样性也自然让前端头几张卡有变化——无需前端改动。

## 3. 算法(确定性,双重配额 + 放宽兜底)

在现有「过滤可行 + 按新颖度排序」之后,改「硬取 top_n」为「带配额的贪心选取」:

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

要点:
- 新增两个带默认值的参数 `max_per_anchor` / `max_per_dimension`,既可单测注入,又**向后兼容**现有以 `max_existing=`/`top_n=` 调用的测试。
- `dimension` 取 `c.transformation.dimension`(替代:Perspective/ArtStyle/Genre;组合:Mechanic)。

## 4. 参数(模块常量)

```python
MAX_PER_ANCHOR = 2      # 主轴:同一锚点游戏最多 2 条变体
MAX_PER_DIMENSION = 5   # 次轴软护栏:防止一种变形极端霸屏(维度仅 4 种,取 5 仅极端时生效)
```

放在 `TOP_N` 附近。暂用模块常量;若后续想运行期调,可仿 `TOP_N` 提为 `OPP_MAX_PER_ANCHOR` / `OPP_MAX_PER_DIMENSION` 环境变量(本期不做,YAGNI)。

## 5. 行为保证与边界

- **全局最新颖那条永远第一个入选**(贪心从最新颖起步,首条必不被配额挡)→ 质量锚点不丢。
- **选取顺序 = 展示顺序**:多样候选在前、重复变体在后。
- **始终返回 `min(top_n, 可行数)` 条**:放宽兜底保证不会因配额少给。
- **小图谱退化优雅**:可行数 ≤ top_n 或只有单一锚点时,配额基本不绑/触发放宽,退化为原新颖度序,不会比现状更差。
- **确定性**:排序是全序(以 `id` 兜底 tiebreak),无 RNG,同输入恒同输出。

## 6. 测试

新增多样性单测(需要能变 anchor / dimension 的辅助构造器,区别于现有只造 `anchor="a"`/`Mechanic` 的 `_cand`):

1. **per-anchor 配额**:某锚点造 5 条 + 另两个锚点各几条,`top_n` 足够大;断言任一锚点入选数 ≤ `MAX_PER_ANCHOR`(在有其他锚点可替代时)。
2. **per-dimension 配额**:跨多个锚点但同一维度造 ≥6 条,断言该维度入选数 ≤ `MAX_PER_DIMENSION`。
3. **放宽兜底**:只有单一锚点造 5 条、`top_n=5`、`max_per_anchor=2`;断言返回 5 条(配额本会只给 2,放宽补满)。
4. **新颖度优先**:混合造若干,断言 `selected[0]` 是全局最新颖那条。
5. **确定性**:同输入跑两次,断言 id 序列完全一致。

回归:现有 3 个 rank 测试(`test_rank_filters_out_candidates_above_ceiling`、`test_rank_sorts_by_scarcity_then_target_attestation`、`test_rank_truncates_to_top_n`)用的是 `anchor="a"`/`Mechanic` 的均匀夹具,放宽兜底会让它们的断言(成员/顺序/长度)仍然成立——**预期无需修改**,实现时运行确认;若有出入再按新行为更新。

## 7. 不做(YAGNI / 留给其他项)
- 跨次随机(serendipity,#1/#3-A 那条)——本期纯确定性。
- 配额 env 可调、MMR/λ 等更复杂的多样性算法。
- 任何 API / 前端 / schema / LLM 层改动。
