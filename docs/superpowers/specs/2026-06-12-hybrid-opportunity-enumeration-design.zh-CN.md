# 混合机会枚举：规则驱动跨维度生成 + 画像感知协同加权 设计 Spec

## 1. 目的与背景

上一阶段（已合并，PR #43）给机会枚举加了「功能角色协同」**质量先验**：候选仍由属性枚举生成，角色作为**叠加层**对其标注 `SynergyRationale` 并把命中协同的候选排前。

本阶段在此基础上把协同层从「只排序」推进到「也参与生成、且对具体开发者个性化」，但**严格保持混合**——不拿标签替换属性。要解决两个具体缺口：

1. **跨维度协同无法被生成。** 现有 `_combine_candidates` 只借入 **Mechanic**。因此那些载体在 Theme / GameFeel / Genre 的角色（典型：`恐惧张力`、`放松抚慰`、`操作快感`）只能靠 SUBSTITUTE 替换触及，而替换又不参与协同标注。结果：「给肉鸽叠加恐怖题材 → 氛围营造」这类协同**根本生成不出来**。
2. **协同与开发者脱节。** `SynergyRationale.predicted_experience`（如「欢乐混乱」）和 `DeveloperProfile.desired_player_experiences` 各管各的。排序只看设计结构，不看「这个开发者想要哪种体验」。

## 2. 核心不变量（本阶段的硬约束）

> 这条不变量是本 spec 的第一性原则，任何实现不得违反，且要落到测试上。

1. **属性枚举与稀缺度全部保留，角色永不替换属性。** `_substitute_candidates`、`_combine_candidates`（Mechanic 全量借入，含**不命中任何规则**的纯新颖候选）、`existing_combination_count` 稀缺度计算——**一行不删**。本阶段只**新增**一个规则驱动生成器与画像加权，与属性产物取**并集**。
2. **「稀缺=发现」与「协同=质量」两半都留。** 属性枚举负责广度/serendipity，协同负责质量/个性化。本阶段不得退化为「只生成规则预测的组合」。
3. **flag 关 = 字节级回退到 PR #43 后的行为。** 沿用 `SYNERGY_RANKING`（默认开）；关闭时不跑规则驱动生成、不做画像加权、排序回退。
4. **仍不进图谱。** 角色/规则继续作服务层旁路推导（Approach B）；图谱结构、import、GameDesignProfile schema、fixture 全部零改动。

## 3. 数据契约改动

### 3.1 `element_roles.json` 增加维度标注
当前结构 `role -> [terms]` 丢失了「词来自哪一段」，而跨维度生成需要知道借入元素属于 Mechanic / GameFeel / Theme / Genre（用于 `Transformation.dimension` 与稀缺度按对应维度计算）。改为按段分组：

```json
"roles": {
  "恐惧张力": {
    "Mechanic": ["理智系统", "追猎者", "躲藏潜逃", "夜视摄影", "压力系统"],
    "Theme":    ["生存恐怖", "心理恐怖", "宗教恐怖", "灵异", "人体实验", "丧尸末世"],
    "GameFeel": ["紧张节奏"],
    "Genre":    ["生存恐怖"]
  },
  ...
}
```

- 向后兼容：加载器把分组拍平成既有的 `element -> set[FunctionalRole]`（§3.2），现有 `roles_for_elements` / `find_synergy` / `rationale_for` 行为不变。
- 新增能力：加载器同时构建 `element -> dimension` 与 `role -> set[(element, dimension)]` 两张反查表。
- 数据本身（词的归类）不变，仅重组结构 + 标注所属段。

### 3.2 `services/synergy.py` 新增
- `load_element_dimensions() -> dict[str, str]`：元素 → 所属维度段（Mechanic/GameFeel/Theme/Genre）。
- `elements_for_role(role: FunctionalRole) -> frozenset[tuple[str, str]]`：角色 → 提供它的 (元素, 维度) 集合（element_roles 的反查）。
- 既有 `load_element_roles` / `roles_for_elements` / `find_synergy` / `rationale_for` 接口与语义保持不变（只是内部从新结构构建）。

### 3.3 `Transformation` 用法泛化（schema 不变）
`Transformation` 字段不变。本阶段把 COMBINE 的 `dimension` 从固定 `"Mechanic"` 泛化为 `{"Mechanic","GameFeel","Theme","Genre"}` 之一，`from_value=None`、`to_value=借入元素`。`_combine_candidates`（属性 Mechanic 借入）保持只产 `"Mechanic"`；跨维度只由新生成器产出。

## 4. 模块行为

### 4.1 规则驱动跨维度候选生成器（新增 `_rule_driven_candidates`）
仅当 `_synergy_enabled()` 时运行。算法：

```
对每条协同规则 (roleA × roleB → exp)：
  对每个覆盖 roleA 的锚点游戏 G（roles_for_elements(G 四段) ⊇ {roleA}）：
    对每个提供 roleB 的 (元素 E, 维度 D)（来自 elements_for_role(roleB)）：
      若 G 在维度 D 上尚无 E：
        产出 COMBINE 候选：G 借入 E
          transformation = COMBINE, dimension=D, from_value=None, to_value=E
          existing_combination_count 按维度 D 对应的 GameDimensions 属性计算（沿用 _combination_game_ids 逻辑，维度→属性名映射扩到 4 段）
          synergy = SynergyRationale(rule.id, anchor_role=roleA, borrowed_role=roleB, predicted_experience=exp)
          id = _candidate_id(G, "comb", D, E)   # dimension 进 id，跨维度天然不撞 Mechanic 候选
```

- roleA/roleB 对称：两个方向都枚举（锚点出 roleA 借 roleB，以及锚点出 roleB 借 roleA），与 `find_synergy` 的对称语义一致。
- 借入 Mechanic 维度的候选与属性 `_combine_candidates` 产物 **id 相同** → §4.2 去重消解；借入 Theme/GameFeel/Genre 的是**全新候选空间**。

### 4.2 候选并集与去重（`enumerate_candidates` 整合）
```
candidates = _substitute_candidates ∪ _combine_candidates ∪ _rule_driven_candidates   （flag 关时后者为空）
按 candidate.id 去重；重复时优先保留带 synergy 的那个
```
属性两类生成器**完全不动**，规则驱动是第三个加性来源。

### 4.3 画像感知协同加权（`rank_candidates` 接受可选画像信号）
- `rank_candidates(..., desired_experiences: set[str] | None = None)`：可选参数，缺省 None（如 `_secondary_pool` 等无画像场景），行为同现在。
- 当提供 `desired_experiences` 且 flag 开时，排序主键升级为三档：
  1. 命中协同 **且** `synergy.predicted_experience ∈ desired_experiences`（为这个开发者量身的协同）
  2. 命中协同（结构上成立，但非该开发者首选体验）
  3. 无协同（纯稀缺候选）
  其后沿用 `(existing_combination_count, -target证据数, id)`；多样性配额（`max_per_anchor`/`max_per_dimension`）与兜底第二遍**不变**。
- `match_opportunities` 把 `profile.desired_player_experiences` 传入 `rank_candidates`。flag 关或未传画像时退回二档（命中/不命中），即 PR #43 行为。

### 4.4 框架与下游
`opportunity_frame_service` 既有 `_evidence_path` 协同行不变。跨维度协同候选被选中成 area 后，框架的 `recommended_transformations` 主变形会自然描述为「在 {Theme/GameFeel/...} 维度组合借入『…』」（沿用 `_describe_transformation`），无需改动。

## 5. 验证策略（本阶段必须交付，作为验收闸）

1. **留一法重新发现（leave-one-out rediscovery）。** 从库中移除某爆款配方的代表作（如 PEAK 型「社交放大器 × 高方差失败源」），跑混合枚举，验证对应机会区域仍因协同规则被生成并进入 Top-N。证明协同真的挣到了它的复杂度成本。以可跑的测试/脚本交付（可用内存 `GameDimensions` 构造，避免依赖活库）。
2. **消融对比（ablation）。** 同一画像，`SYNERGY_RANKING` 开 vs 关，对比 Top-N 候选集差异；记录「跨维度协同候选」与「画像命中候选」的占比，确认它们确实改变了结果而非空转。
3. **跨维度可达性。** 构造一个「角色只来自 Theme/GameFeel」的协同（如恐惧张力 × 资源张力），验证混合枚举能生成对应候选——而纯属性枚举（flag 关）生成不出来。这是本阶段价值的直接证据。

## 6. 不改动（范围边界）

- 不删/不改 `_substitute_candidates`、`_combine_candidates`、稀缺度计算。
- 不进图谱（无 `PLAYS_ROLE` 边）、不改 import / GameDesignProfile schema / game fixture。
- 不改 `Transformation` / `SynergyRule` / `SynergyRationale` schema 定义。
- SUBSTITUTE 仍不参与协同标注（替换的协同语义留作再下一阶段）。
- 不引入新的 LLM 调用；画像加权是确定性的集合匹配。

## 7. 模块独立测试用例

1. **维度反查**：`load_element_dimensions()["生存恐怖"]=="Theme"`、`["老虎机"]=="Mechanic"`；`elements_for_role(恐惧张力)` 含 `("生存恐怖","Theme")` 与 `("紧张节奏","GameFeel")`。
2. **加载向后兼容**：重组后 `roles_for_elements`/`find_synergy`/`rationale_for` 全部既有测试不变。
3. **跨维度生成**：锚点为肉鸽（高方差失败源、无恐怖题材），库内存在恐怖题材游戏 → 混合枚举产出「该锚点借入 Theme『生存恐怖』」候选且带 synergy（dread_scarcity 或对应规则）；该候选在 flag 关时**不存在**。
4. **去重**：Mechanic 维度的规则驱动候选与属性 combine 候选 id 相同，最终只保留一个且带 synergy。
5. **属性发现不丢**：一个不命中任何规则的纯稀缺 combine 候选，混合枚举里依然存在（不被规则驱动「挤掉」）。
6. **画像加权三档**：两个均命中协同的候选，`predicted_experience` 命中开发者 `desired_player_experiences` 的排在另一个之前；都不命中画像时退回按稀缺。
7. **flag 关零回归**：`SYNERGY_RANKING=0` 时 `enumerate_candidates`/`rank_candidates` 与 PR #43 输出逐候选一致。
8. **留一法**（§5.1）与**跨维度可达性**（§5.3）作为集成式验证用例交付。

## 8. 验收标准

- 混合枚举 = 属性产物 ∪ 规则驱动产物，去重后属性产物**全部仍在**（不变量可测）。
- 至少存在一类「仅核心四段非 Mechanic 维度可完成」的协同候选，被混合枚举生成、被纯属性枚举漏掉（§5.3 自证跨维度价值）。
- 画像加权下，预测体验匹配开发者期望的协同候选稳定排在前。
- `SYNERGY_RANKING=0` 全量套件零回归（逐候选一致）。
- 留一法能在不知道代表作的情况下重新发现其机会区域。

## 9. 已知局限 / 待评审

1. **借入 Theme/GameFeel/Genre 的"组合"语义偏抽象**（"给肉鸽叠加恐怖题材"作为设计方向是合理的，但"借入一个 GameFeel"比借入机制更需下游 LLM 具象化）。框架/概念阶段需能把跨维度借入讲成可读概念——本阶段只负责生成与排序，具象化交给 6.6/6.7。
2. **薄角色仍薄**：沉浸氛围/创造表达/情感羁绊在仅核心四段下覆盖弱；跨维度生成会缓解（Theme 来源被激活），但根治仍需后续纳入 ArtStyle/AudioStyle/UGC 段。
3. **画像加权目前只匹配 `desired_player_experiences`**；是否也纳入 `liked_references`/`disliked_*` 的体验映射，留作评审。
4. **规则表完备性**：跨维度生成放大了规则表的影响面——一条缺失或错误的规则会直接影响生成而不只是排序。规则表需领域人审查（对齐可解释性原则）。
