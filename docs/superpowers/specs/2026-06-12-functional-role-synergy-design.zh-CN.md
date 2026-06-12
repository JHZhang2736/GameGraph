# 功能角色 × 协同规则：机会枚举质量先验 设计 Spec

## 1. 目的与背景

本阶段在既有 **6.5 机会匹配**（`opportunity_service.py`）之上，叠加一层「功能角色协同」作为机会候选的**质量先验**，解决当前枚举的一个结构性盲点。

当前枚举以 **稀缺度 = 新颖度**（`existing_combination_count`，越小越优先）排序。但稀缺度无法区分「没人做因为没想到」与「没人做因为不成立」：图谱里一个空的组合格子，既可能是 PEAK（派对 + 爬山）那样的金矿，也可能是「派对 + 报税」那样的死格子，两者同样稀缺。

**核心观察：** 爆款的真正配方常不在「标签对」层面，而在**机制交互**层面：
- PEAK = 派对 + 爬山 → 成立的原因是「**高方差/高失败活动** × **社交在场放大** → 涌现喜剧」。
- Gamble With Your Friends = 派对 + 赌场 → 同一条配方（老虎机=高方差失败源 × 共享账户/近距语音=社交放大器 → 欢乐混乱）。

这条配方活在比 Mechanic / Experience 更高一层的**功能角色**层。本阶段给系统补这一层 + 一张手工策展的**协同规则**表，让枚举从「找稀缺组合」升级为「找**结构上互补且**稀缺的组合」。

## 2. 核心原则

1. **角色是标签层，不替换机制。** preferred-terms 的 ~210 个机制及其它词表**一个不删、一个不并**；图谱节点/边/游戏的 `HAS_MECHANIC` 全部照旧。角色只是给元素额外贴的「体验职责」分类（一元素可多角色）。机制是书，角色是书架分区标签。
2. **角色是元素的内在属性，推导得到、不逐局标注。** 角色由**核心四段**受控词表分类：**Mechanic / GameFeel / Theme / Genre**。游戏的角色覆盖 = 其这四段取值在 `element_roles` 表里的并集。因此**无需新增 schema 字段、无需回填任何 fixture**。
3. **Approach B：v1 不进图谱。** 角色与规则只待在旁路数据表，由服务层在枚举时查表推导。**图谱结构零改动，已入库数据零改动。**（将来若 UI 需可视化角色，再加性地给机制挂 `PLAYS_ROLE` 边，机制本身不变。）
4. **稀缺保留为次因子，协同为主因子。** 排序先看「是否命中协同规则」，再看稀缺度；多样性配额（同锚点/同维度上限）沿用 6.5 既有逻辑。
5. **不承诺好玩。** 协同只表示「结构上有产生某涌现体验的潜力」，沿用 spec §7.4，不声称概念好玩或成功。

## 3. 数据契约（系统产物）

### 3.1 `FunctionalRole`（枚举，20 个）
元素在「体验经济」里承担的功能角色。简体中文枚举值。完整清单见 §4。

### 3.2 `element_roles.json`（角色分类表）
`backend/app/fixtures/element_roles.json`。结构：`{"version", "description", "roles": { 角色值: [核心四段词…] }}`。
- 键必须是 `FunctionalRole` 枚举值（加载时校验，非法即响亮失败）。
- 值是来自 Mechanic / GameFeel / Theme / Genre 四段的受控词；一个词可出现在多个角色下。
- 加载器反转为 `元素名 -> set[FunctionalRole]`；游戏角色覆盖 = 其四段取值在此表的并集（表里没有的词不贡献角色）。

### 3.3 `SynergyRule`（协同规则）
`backend/app/fixtures/synergy_rules.json`，结构 `{"version","description","rules":[…]}`。每条规则字段：
- `id`：稳定标识。
- `role_a` / `role_b`：`FunctionalRole`，**对称**（角色顺序无关）。
- `experience`：预测涌现体验（取自 preferred-terms 体验词表）。
- `evidence_games`：库内印证该配方的代表作 id（文档/证据用，加载器不强制校验存在）。

### 3.4 `SynergyRationale`（候选上的协同理由）
某候选被一条规则点亮的具体理由，字段：`rule_id`、`anchor_role`（锚点已有的角色）、`borrowed_role`（借入补上的角色）、`predicted_experience`。

### 3.5 `CandidateOpportunityArea.synergy`
在既有 `CandidateOpportunityArea` 上**新增可选字段** `synergy: SynergyRationale | None = None`。`None` 表示纯稀缺候选（未点亮任何规则）。`OpportunityArea` 继承之。加性可选，不破坏既有契约往返。

## 4. 角色清单（20）

> 「主来源」标注该角色在核心四段里的主要载体段（M=Mechanic, F=GameFeel, T=Theme, G=Genre）。仅核心四段下，**沉浸氛围 / 创造表达 / 情感羁绊**三者偏薄（强信号本在 ArtStyle/AudioStyle/UGC 段，本阶段未纳入），格式可扩展，后续补段即可加词。

**张力 / 风险**
1. `高方差失败源` HIGH_VARIANCE_FAILURE — 随机性/永久死亡/高失败活动制造的风险张力。主来源 M、G(类肉鸽/大逃杀)。
2. `恐惧张力` DREAD_SOURCE — 恐惧/压迫/追逐制造的情绪压力。主来源 T(生存恐怖/心理恐怖)、M(追猎者/理智系统)、G。
3. `节奏压缩器` PACING_COMPRESSOR — 限时/短局/撤离造成的时间压力。主来源 M。
4. `竞技对抗` COMPETITION — 玩家间对抗/淘汰（区别于合作社交）。主来源 M(淘汰赛制)、G(大逃杀)。

**精通 / 技巧**
5. `掌握曲线` MASTERY_CURVE — 构筑/连招/战术深度带来的精通空间。主来源 M、G(类魂)。
6. `操作快感` VISCERAL_EXECUTION — 手感本身的爽（区别于 build 深度）。主来源 F(爽快射击/厚重打击/精准平台)。
7. `系统优化` SYSTEM_OPTIMIZATION — 造引擎/自动化/经营调优的满足（区别于资源稀缺张力）。主来源 M(自动化/引擎构筑)、G(4X/模拟经营)。
8. `解题洞察` PUZZLE_INSIGHT — 收敛式设计谜题的「aha」（区别于发散涌现）。主来源 M(视角解谜/传送门)、G(解谜)。

**认知 / 涌现**
9. `认知降负载` COGNITIVE_OFFLOAD — 复用玩家熟悉规则降低学习成本。主来源 M(二十一点/牌型组合/回合制)、F(桌游质感)。
10. `涌现源` EMERGENCE_SOURCE — 物理/AI/规则操控/沙盒催生不可预设互动。主来源 M、G(沙盒/沉浸模拟)。

**资源 / 成长**
11. `资源张力` RESOURCE_TENSION — 稀缺/经济/管理压力。主来源 M(资源管理/物资配给)、G(生存)。
12. `成长权力` POWER_ESCALATION — 数值滚雪球/刷宝的变强爽感。主来源 M(元进度/装备分层/灵魂货币)、G(刷宝射击)。
13. `收集驱动` COLLECTION_DRIVE — 收集/积累/养成驱动。主来源 M(怪物捕捉/采集/合成制作)、G(怪物收集)。

**社交**
14. `社交放大器` SOCIAL_AMPLIFIER — 多人在场/共享资源把个人后果放大为集体后果。主来源 M(共享账户/近距语音/非对称协作)、G(派对/合作射击)。

**探索 / 沉浸 / 叙事 / 创造 / 舒缓 / 羁绊**
15. `探索驱动` EXPLORATION_DRIVE — 探索/发现/能力门控推进。主来源 M(非线性探索/能力门控探索)、G(类银河城/开放世界)、T(地下探险/考古探险)。
16. `沉浸氛围` ATMOSPHERIC_IMMERSION — 氛围/世界沉浸/视觉享受。主来源 F(沉浸代入)、T(超现实/自然/海洋)、M(环境叙事)。
17. `叙事钩子` NARRATIVE_HOOK — 作者化剧情/分支/抉择牵引。主来源 M(分支叙事/环境叙事)、G(叙事冒险/RPG)、T(犯罪悬疑/家庭情感)。
18. `创造表达` CREATIVE_AUTHORSHIP — 建造/编辑/自定义的创作与表达。主来源 M(关卡编辑/建造/创意工坊)、G(创作工具/沙盒)。
19. `放松抚慰` COZY_COMFORT — cozy/低压/抚慰（高方差失败源的反极）。主来源 F(轻松休闲)、T(田园生活/家装/美食)、M(房屋翻新/烹饪模拟)。
20. `情感羁绊` EMOTIONAL_BOND — 机制化的角色/同伴/世代羁绊（区别于剧情牵引）。主来源 M(好感系统/同伴协助/世代传承)、T(家庭情感)。

## 5. 协同规则表（20 条，覆盖全部 20 角色）

> `role_a × role_b → 预测体验`（体验取自 preferred-terms 体验词表）。每条至少一款库内证据作。

| id | role_a × role_b | → 体验 | 证据作（例） |
|---|---|---|---|
| social_high_variance_comedy | 高方差失败源 × 社交放大器 | 欢乐混乱 | gamble_with_your_friends, lethal_company, among_us, repo, rounds |
| mastery_under_permadeath | 掌握曲线 × 高方差失败源 | 战斗精通 | hades, dead_cells, risk_of_rain_2, slay_the_spire |
| familiar_rules_deep_build | 认知降负载 × 掌握曲线 | 构筑乐趣 | balatro, dicey_dungeons |
| emergent_systems_exploration | 涌现源 × 探索驱动 | 涌现玩法 | noita, outer_wilds, animal_well |
| scarcity_time_pressure | 资源张力 × 节奏压缩器 | 运筹帷幄 | frostpunk, this_war_of_mine, escape_from_duckov |
| short_run_rng_snowball | 节奏压缩器 × 高方差失败源 | 滚雪球快感 | vampire_survivors, deep_rock_galactic_survivor, the_spell_brigade |
| coop_exploration_coordination | 社交放大器 × 探索驱动 | 协作默契 | we_were_here_together, we_were_here_too, deep_rock_galactic |
| collection_mastery_growth | 收集驱动 × 掌握曲线 | 收集养成 | slay_the_spire, hades, dead_cells |
| dread_scarcity_atmosphere | 恐惧张力 × 资源张力 | 氛围营造 | resident_evil_2, resident_evil_7_biohazard, outlast |
| dread_chase_pacing | 恐惧张力 × 节奏压缩器 | 氛围营造 | outlast, the_outlast_trials, the_evil_within |
| visceral_mastery_flow | 操作快感 × 掌握曲线 | 战斗精通 | cuphead, hollow_knight, titanfall_2 |
| optimization_scarcity | 系统优化 × 资源张力 | 经营成就 | oxygen_not_included, frostpunk, civilization_vi |
| competition_social_tension | 竞技对抗 × 社交放大器 | 竞技紧张 | fall_guys, rounds, among_us |
| bond_loss_under_permadeath | 情感羁绊 × 高方差失败源 | 情感叙事 | wildermyth, darkest_dungeon, xcom_2 |
| puzzle_exploration_discovery | 解题洞察 × 探索驱动 | 探索发现 | outer_wilds, animal_well, rise_of_the_tomb_raider |
| power_collection_snowball | 成长权力 × 收集驱动 | 滚雪球快感 | borderlands_2, vampire_survivors, risk_of_rain_2 |
| cozy_collection_growth | 放松抚慰 × 收集驱动 | 收集养成 | slime_rancher, my_time_at_portia, travellers_rest |
| shared_economy_coordination | 资源张力 × 社交放大器 | 协作默契 | gamble_with_your_friends, deep_rock_galactic |
| creative_emergence_expression | 创造表达 × 涌现源 | 个性化表达 | terraria, tabletop_simulator |
| atmosphere_narrative_immersion | 沉浸氛围 × 叙事钩子 | 情感叙事 | firewatch, outer_wilds, finding_paradise |

## 6. 行为改动

### 6.1 取数扩展（只读、加性）
`opportunity_repository` 的取数查询新增 **theme + game_feel** 两段（genre / art_style / mechanics 已在取）。`GameDimensions` 新增 `theme: set[str]`、`game_feel: set[str]` 字段（**置于末位带默认**，保证既有 positional 构造不破）。

### 6.2 角色推导
`services/synergy.py`：
- `load_element_roles() -> dict[str, frozenset[FunctionalRole]]`（元素→角色）。
- `load_synergy_rules() -> tuple[SynergyRule, …]`。
- `roles_for_elements(elements) -> set[FunctionalRole]`：一组元素的角色并集。
- 游戏角色 = `roles_for_elements(mechanics ∪ game_feel ∪ theme ∪ genre)`。
- `find_synergy(anchor_roles, borrowed_roles) -> (rule, anchor_role, borrowed_role) | None`：对称匹配第一条「锚点出一角色、借入出另一角色」的规则。

### 6.3 枚举标注 synergy
- **COMBINE 候选**（借入机制 M）：算 `anchor_roles = roles_for_elements(锚点四段)`、`borrowed_roles = element_roles[M]`，命中规则则在候选上挂 `SynergyRationale`。
- **SUBSTITUTE 候选**：v1 **不标 synergy**（替代是换值不是补角色，协同语义不直接适用）；保持现状，仅参与稀缺排序。spec 留作后续。

### 6.4 排序：协同优先
`rank_candidates` 主排序键改为「是否命中 synergy」（命中在前），其后才是既有 `(existing_combination_count, -target证据数, id)`；多样性配额（`max_per_anchor` / `max_per_dimension`）与兜底第二遍**沿用**。整段以 feature flag（如 `SYNERGY_RANKING` env，默认开）控制，便于消融对比与回退。

### 6.5 框架证据接入
`opportunity_frame_service._evidence_path`：当 area 带 `synergy` 时，追加一行协同推理（「锚点提供 {anchor_role}，借入 {borrowed_mechanic} 补 {borrowed_role}，模式预测 {experience}」），强化框架可解释性。

## 7. 不改动（范围边界）

- 不给 `GameDesignProfile` 加字段；不改 `import_service` / `game_repository`；不回填任何 fixture。
- 不改图谱节点/边结构；不动 preferred-terms 的机制/创新/参考等词表（不删不并）。
- 不改 6.5 的 SUBSTITUTE 枚举与稀缺度计算本身；synergy 是叠加层。

## 8. 模块独立测试用例

1. **加载/分类**：`element_roles.json` 加载后，`老虎机` 含「高方差失败源」与「认知降负载」；`共享账户` 含「社交放大器」；非法角色键 → 抛错。
2. **角色推导**：给一组四段元素（机制+题材+手感+类型），`roles_for_elements` 返回正确并集；表外词不贡献角色。
3. **协同命中**：锚点 {高方差失败源} + 借入 {社交放大器} → 命中 `social_high_variance_comedy`，返回正确 `(anchor_role, borrowed_role)`；反方向同样命中。
4. **协同不命中**：{叙事钩子} + {认知降负载} → None。
5. **枚举标注**：含「共享账户」锚点 + 可借入「老虎机」→ 该 COMBINE 候选带 `synergy`，`predicted_experience=欢乐混乱`；无互补角色的借入候选 `synergy is None`。
6. **排序优先**：一个命中 synergy 但稍不稀缺的候选，排在一个纯稀缺但无 synergy 候选之前。
7. **框架证据**：带 synergy 的 area 经 `build_frame`，`evidence_path` 含协同推理行。
8. **留一法（可选，集成）**：库内移除 PEAK 型证据作后，对应「社交放大器 × 高方差失败源」机会区域仍因规则点亮而进入 Top-N。

## 9. 验收标准

- 每条进入排序优先的候选都能给出 `SynergyRationale`（规则 id + 角色对 + 预测体验），可追溯到 `synergy_rules.json`。
- 角色覆盖完全由四段受控词表推导，无需任何逐局标注或 fixture 回填。
- flag 关闭时，6.5/6.6 既有行为与既有测试**零回归**。
- 20 个角色每个至少被一条协同规则覆盖（§5 表自证）。

## 10. 已知局限 / 待评审

1. **三个薄角色**（沉浸氛围/创造表达/情感羁绊）在仅核心四段下信号偏弱；如效果不足，后续纳入 ArtStyle/AudioStyle/UGC 段补词（格式已支持）。
2. **角色 = 元素内在属性** 的简化：同一机制在不同游戏的语境差异未被捕捉；如需要，后续加「逐游戏覆盖」补丁。
3. **SUBSTITUTE 暂不参与协同**：是否给替代候选也定义协同语义，留作下一阶段。
4. 协同规则是手工策展的**设计假说**，需领域人可审查（对齐 spec §7.5 可解释性）；规则带 `evidence_games` 以便抽查。
