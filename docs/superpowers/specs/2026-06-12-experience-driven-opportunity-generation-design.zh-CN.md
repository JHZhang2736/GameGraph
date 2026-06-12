# 体验/角色驱动的机会生成重构 设计 Spec（定稿）

## 1. 目的与背景

### 1.1 对现有机会生成逻辑的评估（要解决的问题）
当前 `enumerate_candidates`（`opportunity_service.py`）对每个游戏当锚点机械展开 SUBSTITUTE（换视角/美术/类型值）+ COMBINE（借机制）+ rule-driven（#44 跨维度协同借入），按属性稀缺度+协同+画像排序。硬伤：
1. 生成单元是「机械改一格」，不是有意义的设计机会，结构性偏衍生型。
2. 新颖度 = 库内**属性值**稀缺度，粗糙、依赖库规模、把"罕见"等同"新颖"。
3. substitute/combine 维度划分是历史包袱，不成体系。
4. 「全量生成再过滤」方向反了——画像最后才介入。
5. 大部分候选是「哑」的（无 `predicted_experience`/配方），却和优质协同候选混排。

### 1.2 核心理念：把生成倒过来
标签层提供了更好的生成单元——**带预测体验的角色配方**。本重构**全量替换**旧生成，从"枚举属性编辑再过滤"倒转为"从想要的体验出发 → 协同规则 → 角色配方 → 图谱实例化"：

```
desired_player_experiences（为空 → 全体协同规则的体验）
  → 反查协同规则：哪些 roleA × roleB → 这些体验
  → 角色配方
  → 实例化：锚点∈覆盖 roleA 的游戏；借入∈提供 roleB 的元素
  → 机会（天生带「预测体验 + 配方 + 来源游戏」，是 6.7 的优质输入）
  → 新颖度 = 该「角色组合」在库内稀缺度（角色级）
```

属性稀缺度从生成主轴**降级为 wildcard 次级通道**（保留 serendipity），不再当主角。

## 2. 替换范围与安全策略

- **recipe 成为唯一生成入口。** 新 `enumerate_opportunities(games, desired)` 取代旧 `enumerate_candidates` 在 `match_opportunities` 中的位置。**不引入运行时 flag**。
- **删除**：`_substitute_candidates`、旧 `enumerate_candidates` 编排、其专属测试。SUBSTITUTE 型机会不再生成（决策见 §10.4）。
- **复用**：`_combine_candidates` 的机制借入 + 稀缺度机器（`_games_with_value` / `_combination_game_ids` / `_candidate_id`）→ 用于 wildcard 次级通道与角色级新颖度计算。`synergy.py` 全部复用。`rank_candidates` 的画像三档思想复用（输入换成新候选）。
- **安全不靠运行时 flag，靠：feature 分支 + 验证 harness（§6）+ 审查**。既有枚举/match/api/frame 相关测试**改写**为断言新行为（无"零回归"目标——旧生成行为被有意替换）。

## 3. 数据契约

### 3.1 角色级新颖度（核心新指标）
`role_combination_count(games, roleA, roleB)` = 库内**角色覆盖同时 ⊇ {roleA, roleB} 的游戏数**；越小越新颖（"这个设计模式还没人做"）。

### 3.2 候选承载（决策已定）
沿用 `CandidateOpportunityArea`，**不改 schema**。`existing_combination_count` 字段**复用承载组合计数**：recipe 候选 = `role_combination_count`（角色级）；wildcard 候选 = 属性值组合数（旧语义）。字段名"已有该组合的游戏数"对两者都成立。recipe 候选必带 `synergy`（rule + 角色对 + 预测体验）。
- `opportunity_frame_service._evidence_path` 的"现存游戏数=N（越小越新颖）"行对 recipe 候选自然解读为"已有该角色组合的游戏数"；plan 里微调措辞使之准确（如带 synergy 时写"该角色配方"）。

## 4. 生成算法（`enumerate_opportunities(games, desired)`）

### 4.1 主通道：体验/角色配方实例化
```
target_rules = [r for r in load_synergy_rules() if (not desired) or r.experience in desired]
seen: dict[id, candidate] = {}
for rule in target_rules:                       # roleA × roleB → experience
  for anchor_role, borrow_role in ((rule.role_a, rule.role_b), (rule.role_b, rule.role_a)):
    novelty = role_combination_count(games, anchor_role, borrow_role)   # 同配方共享
    for anchor in games:
      if anchor_role not in roles_for_elements(anchor 的来源段元素): continue
      for element, dim in load_elements_by_role()[borrow_role]:
        attr = _DIMENSION_ATTRS.get(dim)
        if attr is None or element in getattr(anchor, attr): continue
        target_games = _games_with_value(games, attr, element)
        if not target_games: continue           # evidence 非空
        cid = _candidate_id(anchor.game_id, "comb", dim, element)
        if cid in seen: continue                 # 多规则点亮同候选保留首条
        seen[cid] = CandidateOpportunityArea(
          ..., transformation=COMBINE(dim, element),
          existing_combination_count=novelty,
          evidence=OpportunityEvidence(anchor, target_games, combination_game_ids),
          synergy=SynergyRationale(rule.id, anchor_role, borrow_role, rule.experience))
```
（来源段 = #44 的核心四段；薄角色多来源段是 parked 的 C，不在本重构。）

### 4.2 次级通道：wildcard 发现（保留 serendipity）
对每个锚点，借入一个**不命中任何规则**且**属性稀缺度极高**的机制（复用 `_combine_candidates` 逻辑筛 `synergy is None` 者），按属性稀缺度排序，**配额上限**（`MAX_WILDCARD`，如 `top_n` 的一小部分或固定小数）。`synergy=None`、`existing_combination_count`=属性值组合数。

### 4.3 排序与配额
`rank_candidates`（改写）主键：`(画像命中档, existing_combination_count, -证据强度, id)`。
- 画像命中档（沿用 #44 三档思想）：recipe 且 `predicted_experience ∈ desired` → 0；recipe 非命中 → 1；wildcard（无 synergy）→ 2。desired 为空时 recipe 全部 1，按新颖度排。
- wildcard 受 `MAX_WILDCARD` 配额，保证主通道占多数、发现力不丢。
- 多样性配额（同锚点/同维度上限）沿用。

## 5. 编排接入
`match_opportunities`：`candidates = rank_candidates(enumerate_opportunities(games, set(profile.desired_player_experiences)), ...)`。LLM judge / 降级 / warnings 全不变——只是喂给 judge 的候选集换成更靶向、更小、天生带语义的集合。`seen_ids`（已看过去重）逻辑沿用。

## 6. 验证策略（验收闸，替代"零回归"）
1. **哑候选占比**：recipe 模式 Top-N 中无 `predicted_experience` 的候选占比应极低（理想仅 wildcard 配额那部分）。量化断言。
2. **画像靶向**：`desired={"欢乐混乱"}` 时 Top-N 命中/相关体验占比高；与"全规则展开"（desired=∅）对比，命中体验明显聚焦。
3. **留一法重新发现**：移除某爆款配方代表作后，对应角色配方机会仍被生成并靠前（复用/扩展 `test_hybrid_validation.py`）。
4. **发现力未丢**：wildcard 通道产出 ≥1 个"无规则、极稀缺"候选。
5. **缺省回退**：desired=∅ → 全体规则体验参与，产出非空。
6. **角色级新颖度有效**：构造两配方，已被库内多游戏共现的角色组合，新颖度更高（数值更大→排后）。

## 7. 范围边界（不做）
- 不进图谱、不改 GameDesignProfile schema、不改 import、不回填游戏 fixture、不改 `Transformation`/`SynergyRule`/`SynergyRationale` schema。
- 不扩生成可借维度（仍 #44 核心段；薄角色多来源段是 parked 的 C）。
- 不在新路恢复 SUBSTITUTE（parked 的 B「替换协同」另议）。
- 不替开发者画像做硬约束过滤（仍由 LLM judge）。
- 6.6/6.7 契约不变（recipe 候选仍是合法 COMBINE 候选，带更强语义）。

## 8. 模块独立测试用例
1. `role_combination_count`：含/不含同覆盖 {roleA,roleB} 游戏计数正确；无共现=0（最新颖）。
2. 主通道：desired={体验} → 只对产该体验的规则生成；候选带正确 synergy 与 anchor/borrow 角色、`existing_combination_count`=角色组合数。
3. 缺省回退：desired=∅ → 所有规则参与，产出非空。
4. wildcard：无规则的极稀缺机制借入进结果但受 `MAX_WILDCARD` 配额；`synergy=None`。
5. 排序：命中体验 recipe > 未命中 recipe > wildcard；多样性配额生效。
6. `enumerate_opportunities` 不再产 SUBSTITUTE（无 `transformation.type==SUBSTITUTE` 候选）。
7. `match_opportunities` 端到端跑通 LLM judge 编排（stub），候选来自新生成器。
8. 既有 enumeration/service/api/frame 测试改写后全绿（断言新行为）。

## 9. 验收标准
- 生成入口为 `enumerate_opportunities`；`match_opportunities` 不再调用旧 `enumerate_candidates`；无 SUBSTITUTE 候选产出。
- recipe Top-N 哑候选占比 ≪ 旧实现（§6.1，以改写前快照或人工核对为参照）。
- 有画像时命中/相关体验占比显著高（§6.2）。
- wildcard 保证 ≥1 发现型候选（§6.4）；留一法可重新发现（§6.3）。
- 全量套件（改写后）绿。

## 10. 决策（已定）/ 待评审
1. **【已确认】** desired 为空 → 全体协同规则体验。
2. **【已定】** 直接全量替换，无运行时 flag；recipe 为唯一生成入口；旧 substitute 删除、combine+稀缺度复用于 wildcard。
3. **【已定】** 新颖度复用 `existing_combination_count`（recipe=角色组合数，wildcard=属性组合数），不改 schema。
4. **【已定】** 新路去掉 SUBSTITUTE；能补角色完成协同者以 COMBINE-add 表达；机制发现由 wildcard 保留。
5. **【依赖】** 本分支 stacked 在 PR #44 之上，#44 合并后 rebase；parked 的 B/C 与本重构正交，recipe 站稳后再议。
6. **【待评审】** `MAX_WILDCARD` 配额具体值（plan 给默认，可调）。
