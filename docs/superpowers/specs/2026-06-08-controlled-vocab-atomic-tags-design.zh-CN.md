# 受控词表与原子化标签（技能侧）设计 Spec

## 1. 目的

让入库后的游戏在知识图谱中**彼此连接**起来。

当前现象：8 款类银河城游戏入库后各自成簇——每个主游戏节点周围约 20 个属性节点，但游戏之间几乎没有连线。

根因：`profile` 的 list 字段（`main_mechanics`、`main_player_experiences`、`reference_value_tags` 等）生成的是**自由的描述性短语/小句**，后端按 `name` 精确字符串 `MERGE` 建节点。不同游戏对同一特征的措辞永不逐字相同 → 不会落到同一个节点 → 没有共享节点 → 游戏间没有桥。

> 例：`animal_well` 的体验 `"an unsettling, eerie atmosphere"`、`blasphemous` 的 `"oppressive, grotesque atmosphere"`、`ori_and_the_blind_forest` 的 `"emotional, atmospheric storytelling"` 都在讲"氛围"，但三个字符串互不相等，于是三款游戏在"氛围"上没有任何连接。

已确认：schema 与后端**本身支持共享**——按 `name` MERGE，逐字相同的词（如目前少数游戏共有的 `"ability-gated traversal"`）就是现存唯一的桥。问题不在代码，在**生成出来的词不收敛**。

## 2. 方案概述

收敛需要两个**必要且缺一不可**的要素，外加一条本期新增约束：

1. **原子粒度**：进图的 list 字段从"描述性短语"改为"原子受控标签"（一个名词或短名词短语，一项一个特征）。
2. **共享词表**：技能每次生成时把一份 `preferred-terms`（首选词表）当上下文，**优先复用**已有词，只有确实没有合适词时才造新词。
3. **全中文**：所有生成内容（散文、标签、证据摘要、claims）一律简体中文。

**实现边界：只改技能侧（生成 JSON 这一步）+ 新增一个词表文件。后端 import / schema / Neo4j 逻辑本期不动。** 强约束（后端确定性解析）、embedding、候选词暂存均留作后续，可平滑升级、不返工。

## 3. 范围

### 范围内

- 新增首选词表文件 `preferred-terms`（位置见 §6）。
- 修改技能 `.claude/skills/researching-games-for-import/SKILL.md`：增加"输出语言/原子化/优先选词/新词上报"规则与 bad→good 示例。
- 修改字段指令模板 `docs/superpowers/import-guide/game-import-prompt.md`：把原子化与中文约束写进逐字段规则。
- 用现有 8 款游戏 bootstrap 出初版 `preferred-terms`（一次性）。

### 范围外（本期不做，留后续）

- 后端确定性解析/校验级联（未命中报错 + 最近词建议）。
- embedding 相似度 / Neo4j 向量索引 / 跨语言匹配。
- 候选词暂存队列与人工审核 UI、自动合并近义词。
- 后端 `import_service` / `game_repository` / schema 的任何改动。
- 现有 8 款 fixtures 散文字段的**中文翻译**（见 §8 迁移，标为可选后续）。

## 4. 设计决策摘要（已与用户对齐）

1. **方案 A 起步**：词表存仓库文件、靠 LLM 在生成时自觉对齐，软约束；不上后端强校验。
2. **LLM proposes, human disposes**：LLM 负责"建议归并/选词"，最终生效靠人工审 JSON + 回填词表；后端入库那一端**不调 LLM**，保持确定性、可复现。
3. **散文与标签分离**：散文字段保持自然语言（给人读，且整份文档已存进 `Game.document_json`，细节不丢）；只有"会变成图节点"的 list 字段原子化（负责连接）。
4. **全中文**：见 §7。
5. **本期不引入 embedding**：~80 词体量，LLM 聚类对"同义"判断优于 embedding 阈值聚类（embedding 测"相关"非"同义"，易把"二段跳/墙跳"这类不同机制 over-merge）。embedding 留作二期"未命中建议"的召回器，且只做建议。

## 5. 字段规则：哪些原子化、哪些保持散文

### 5a. 散文字段（保持自然语言中文，不受原子化限制）

`short_description`、`selection_reason`、`one_sentence_summary`、`core_loop`、`progression_model`、`failure_model`、`content_structure`、claim 的 `explanation`、各 `EvidenceRef` 的 `quote_or_summary`/`notes`。

这些不进图（除整份 `document_json` 存于 Game 节点），是给人读的，写成完整中文句子。

### 5b. 原子标签字段（中文原子受控标签）

凡是按 `name` 进图建节点的 list 字段，全部适用原子化：

- `PROFILE_LIST_EDGES` 全部 9 个：`main_mechanics`、`main_player_actions`、`main_player_decisions`、`main_player_experiences`、`production_constraints`、`innovation_patterns`、`reusable_reference_patterns`、`non_replicable_risks`、`replayability_sources`。
- `reference_value_tags[].tag` → ReferenceTag。
- `claims[].object` → Concept（当前只有 `object` 进图建节点）。`subject` 当前不进图（仅存于 `document_json`），但为可读性与一致性同样写成中文、尽量原子。建议 `object` 尽量取自词表，但 claim 是"因果洞见"，主宾允许比标签略具体。

> 注：`claims[].relation` 仍是短动词（`uses`/`reduces`/`increases`/`creates`/`enables` 等），保持原有约定。

### 5c. 原子标签格式规范

1. **原子**：一个标签 = 一个特征。一个名词或 1–4 字的中文名词短语。复合短语**拆开**成多个标签。
2. **去填充词**：删掉 `玩法`/`机制`/`系统`/`参考`/`设计`/`体验`/`reference` 这类无信息后缀。
3. **不写整句**：禁止出现完整句子、动词主谓结构、形容词长串、标点分隔的并列。
4. **中文**：见 §7。
5. **优先取自 `preferred-terms`**；词表里没有合适的才造新词。

bad → good 示例（取自 `animal_well`）：

| 现状（描述性短语） | 原子化后（中文标签） |
|---|---|
| `multi-purpose toy/tool usage` | `多用途道具` |
| `nonlinear flip-screen exploration` | `非线性探索`、`翻屏房间` |
| `layered secret and ARG meta-puzzles` | `分层秘密`、`社区协作解谜` |
| `non-combat creature management` | `非战斗`、`生物应对` |
| `an unsettling, eerie atmosphere` | `氛围营造`、`诡异` |
| `delight at emergent uses of simple tools` | `涌现玩法` |
| `solo-developer custom-engine reference` | `独立开发`、`自研引擎` |

原子化后，`氛围营造` 连起 Animal Well / 渎神 / 奥日，`分层秘密`/`非战斗`/`独立开发` 各自成桥——这是描述性短语永远做不到的。

### 5d. 粒度准则（甜区在中间）

- 太宽（`类银河城`）：8 款全连，等于无信号——**禁用**这类全集级标签。
- 太窄（`翻屏房间`，仅一款有）：连不上别人——允许存在，但优先想还能不能更通用。
- 甜区：能连 2–5 款的中等粒度。**`preferred-terms` 的作用就是把粒度固化**：氛围一旦定为 `氛围营造`，后续都复用，不再漂成 `诡异氛围`/`压抑氛围`。

## 6. 首选词表 `preferred-terms`

- **位置**：`.claude/skills/researching-games-for-import/preferred-terms.md`（与技能同目录，便于技能引用并随技能演进）。
- **格式**：本期为"LLM 上下文"用途，用 Markdown（人类友好、LLM 友好），二期需机器解析时再升级为 YAML，平滑可转。按维度分组，每条目 `首选词` + 可选 `别名:`（历史出现过的等价写法，帮助对齐）：

```markdown
## 机制 Mechanic
- 能力门控探索   别名: 能力解锁通行, 锁钥式推进
- 多用途道具
- 非线性探索

## 体验 Experience
- 氛围营造   别名: 诡异, 压抑, 孤独
- 探索发现
- 战斗精通

## 标签 ReferenceTag
- 独立开发
- 自研引擎
- 分层秘密
```

- **维护**：人工编辑 + git 提交。改文件即"加词"，PR / commit 即审核与审计日志——这就是"随时添加新词条"的全部机制，零额外基础设施。

## 7. 中文约束

- 所有生成文本一律**简体中文**：散文字段、原子标签、`reference_value_tags`、claims（`subject`/`object`/`explanation`）、`EvidenceRef.quote_or_summary`/`notes`。
- **例外**：
  - 专有名词保留原文：游戏标题、人名、引擎/语言（如 `C++`）、平台名。
  - 确无通用中文译名的术语：在 `preferred-terms` 登记一个**中文首选词**作为 canonical（可在别名里记英文原文，如 `社区协作解谜  别名: ARG`），生成时用中文首选词。
- `source_refs` / `evidence` 的 `url`、`title`（若引用页本身为外文）按实际保留，不强行翻译标题；但 `notes`/`quote_or_summary` 用中文转述。

## 8. 对现有数据的影响（迁移）

现有 8 款 fixtures 是**英文 + 描述性短语**，与新规则不一致，不会和新生成的中文原子标签连接。

- **本期（bootstrap）**：用新规则一次性重做 8 款的**进图 list 字段**（5b 列出的字段），改成中文原子标签，并据此填充初版 `preferred-terms`。这一步直接解决"连接"问题，是验收的基础。
- **可选后续**：把 8 款的**散文字段**也翻成中文（工作量较大，不影响连接，只影响一致性/可读性）。本期不强制。

## 9. 验收标准

1. 新生成的游戏文档：5b 的字段全部为中文原子标签，无整句、无填充词后缀，且多数取自 `preferred-terms`。
2. bootstrap 后重新入库 8 款，跑诊断 Cypher，**被 ≥2 个游戏共享的属性节点数量显著 > 0** 且语义合理：

   ```cypher
   MATCH (g:Game)-->(n) WHERE NOT n:Game
   WITH n, labels(n)[0] AS label, count(DISTINCT g) AS games
   WHERE games >= 2
   RETURN label, n.name, games ORDER BY games DESC;
   ```

3. 散文字段仍为可读中文句子。

## 10. 测试与验证

- 后端未改：现有 import 测试不受影响，保持通过。
- 技能产出靠"人工审 JSON" + 既有 `验证片段`（`validate_import_document` + `build_graph_write_plan`）确认仍符合 schema。
- 端到端：重做 + 入库 8 款 → 跑 §9 的诊断 Cypher 看连接数。

## 11. 风险与权衡

- **软约束**：靠 LLM 自觉，后端不校验，偶尔会有词没对齐或漏标新词 → 靠人工审 JSON 兜底。可接受，因为这是用户自己策展、量不大的种子库。若漂移变多，再加二期后端强校验（A 的确定性解析），架构上平滑升级。
- **粒度主观**：靠 `preferred-terms` 固化，减少逐次漂移。
- **中文迁移工作量**：散文翻译留作可选后续，先保证连接。
