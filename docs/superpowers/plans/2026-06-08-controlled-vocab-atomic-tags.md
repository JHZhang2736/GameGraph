# 受控词表与原子化标签（技能侧）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让生成的游戏导入文档使用「中文 + 原子受控标签」，并复用一份共享词表，使入库后游戏在知识图谱中跨游戏连接。

**Architecture:** 只改技能侧（生成 JSON 这一步）与文档，不动后端/schema/Neo4j。新增共享词表 `preferred-terms.md`；新建一个中文+原子的参考样例游戏 JSON 替代已删除的 `balatro.json`；修改技能 `SKILL.md` 与字段指令模板 `game-import-prompt.md` 注入新规则；最后用更新后的技能生成额外种子游戏并用 Cypher 验证连接。

**Tech Stack:** Markdown（技能/词表/文档）、JSON（导入文档）、Python（既有 `validate_import_document` 校验，无新增代码）、Neo4j Cypher（连接验证）。

设计依据：`docs/superpowers/specs/2026-06-08-controlled-vocab-atomic-tags-design.zh-CN.md`

---

## 文件结构

| 文件 | 动作 | 职责 |
|---|---|---|
| `backend/app/fixtures/games/animal_well.json` | 创建 | 中文+原子的参考样例 = 替代删除的 balatro.json + 种子#1 + 词表初值来源 |
| `.claude/skills/researching-games-for-import/preferred-terms.md` | 创建 | 共享首选词表，按维度分组的 canonical 词 + 别名 |
| `.claude/skills/researching-games-for-import/SKILL.md` | 修改 | 加「输出规范：中文/原子化/选词/新词上报」一节；样例指向改为 animal_well.json |
| `docs/superpowers/import-guide/game-import-prompt.md` | 修改 | 硬规则加中文+原子约束；JSON 骨架注释标注哪些字段原子；样例指向更新；加 bad→good 示例 |

> 进图建节点的字段（来自 `import_service.PROFILE_LIST_EDGES` + `reference_value_tags` + `claims[].object`）必须原子；散文字段（`*_summary` / `core_loop` / `progression_model` / `failure_model` / `content_structure` / `explanation` / 各 evidence 文本）保持自然语言中文。

---

## Task 1: 新建中文+原子参考样例 `animal_well.json`

**Files:**
- Create: `backend/app/fixtures/games/animal_well.json`
- Verify with: `backend/app/services/import_service.py`（既有 `validate_import_document` / `build_graph_write_plan`，不改）

- [ ] **Step 1: 写样例 JSON 文件**

创建 `backend/app/fixtures/games/animal_well.json`，内容如下（散文字段为中文整句；`main_*` / `reference_value_tags.tag` / `claims.object` 为中文原子标签）：

```json
{
  "candidate": {
    "id": "game_animal_well",
    "title": "Animal Well",
    "source_refs": [
      {
        "title": "Animal Well（维基百科）",
        "url": "https://en.wikipedia.org/wiki/Animal_Well",
        "notes": "机制、分层秘密、单人开发与自研引擎的参考来源。"
      }
    ],
    "short_description": "一款低分辨率像素风的类银河城解谜平台游戏，围绕多用途道具与层层嵌套的秘密构建，由单人开发者打造。",
    "selection_reason": "作为秘密密度高、道具多用途设计与社区协作式元谜题的参考；由一人在自研 C++ 引擎上、带着刻意的技术限制完成。"
  },
  "profile": {
    "game_id": "game_animal_well",
    "one_sentence_summary": "一款非线性的类银河城解谜平台游戏，玩家操控一只小生物在地下迷宫中用多用途道具解谜并揭开层层秘密。",
    "core_loop": "探索相互连通的翻屏房间，寻找道具，试验它们的多种用途来解开环境谜题，逐层解锁路径与秘密。",
    "progression_model": "通过获得的道具（弹簧、飞盘、泡泡棒等）进行类银河城式门控，这些道具兼作移动与解谜工具；后期进展来自秘密、彩蛋与未公开的交互，而非数值成长。",
    "failure_model": "危险与某些生物会杀死角色并送回存档点；生存依赖道具（鞭炮吓退生物、火柴驱散幽灵）而非正面战斗。",
    "content_structure": "一个 16×16 的翻屏房间网格，组织成四个递进层级，从第一层的曼提柯尔 Boss，到隐藏彩蛋、ARG 式社区谜题与速通及未公开解锁。",
    "main_player_actions": ["平台跳跃", "翻屏移动", "道具运用", "生物驱避", "秘密解谜"],
    "main_player_decisions": ["道具选择", "探索路线", "秘密取舍", "社区协作"],
    "main_player_experiences": ["氛围营造", "诡异", "探索发现", "涌现玩法"],
    "main_mechanics": ["多用途道具", "非线性探索", "翻屏房间", "分层秘密", "社区协作解谜", "非战斗", "生物应对"],
    "replayability_sources": ["分层秘密", "社区协作解谜", "速通", "彩蛋收集"],
    "production_constraints": ["独立开发", "自研引擎", "低分辨率", "无武器战斗", "无过场动画"],
    "innovation_patterns": ["多用途道具", "分层秘密", "社区协作解谜"],
    "reusable_reference_patterns": ["多用途道具", "分层秘密", "自我限制设计"],
    "non_replicable_risks": ["超长开发周期", "自研引擎", "大规模玩家社区"],
    "reference_value_tags": [
      {
        "tag": "多用途道具",
        "confidence": "high",
        "quality_status": "draft",
        "evidence": [
          {
            "title": "道具机制",
            "quote_or_summary": "弹簧、飞盘、泡泡棒等道具各自服务于移动与解谜的多种用途。",
            "notes": "维基百科可观察机制。"
          }
        ]
      },
      {
        "tag": "分层秘密",
        "confidence": "high",
        "quality_status": "draft",
        "evidence": [
          {
            "title": "分层秘密",
            "quote_or_summary": "后期层级包含 ARG 元素，需要综合大量玩家的部分解法，另有速通与未公开解锁。",
            "notes": "维基百科可观察结构。"
          }
        ]
      },
      {
        "tag": "独立开发",
        "confidence": "high",
        "quality_status": "draft",
        "evidence": [
          {
            "title": "开发",
            "quote_or_summary": "Billy Basso 以单人开发者身份用 C++ 从零自研引擎，历时约七年。",
            "notes": "维基百科生产事实。"
          }
        ]
      }
    ],
    "evidence": [
      {
        "title": "Animal Well 玩法与开发综述",
        "url": "https://en.wikipedia.org/wiki/Animal_Well",
        "quote_or_summary": "非线性类银河城解谜平台游戏，多用途道具，四层递进秘密含 ARG 谜题，单人在自研 C++ 引擎上完成。",
        "notes": "机制与生产事实取自维基百科。"
      }
    ],
    "confidence": "high",
    "quality_status": "draft"
  },
  "claims": [
    {
      "id": "claim_animal_well_multiuse_tools",
      "subject": "多用途道具",
      "relation": "increases",
      "object": "谜题深度",
      "explanation": "为每件道具设计多种涌现用途，使一小组道具就能生成大量不同谜题，在不依赖庞大内容产线的情况下获得深度与惊喜，适合单人开发者。",
      "evidence": [
        {
          "title": "道具设计解读",
          "quote_or_summary": "每件道具服务于多种用途，而非一次性钥匙。",
          "notes": "基于可观察机制的解释性判断。"
        }
      ],
      "confidence": "medium",
      "quality_status": "draft"
    },
    {
      "id": "claim_animal_well_layered_secrets",
      "subject": "分层秘密",
      "relation": "creates",
      "object": "社区长尾参与",
      "explanation": "把最深层秘密设计成需要综合大量玩家的部分解法，使发售后的探索变成协作式社区事件，把参与度延伸到单次通关之外。",
      "evidence": [
        {
          "title": "秘密结构解读",
          "quote_or_summary": "最深层谜题需要至少数十名玩家综合解法。",
          "notes": "基于可观察结构的解释性判断，未经外部引用。"
        }
      ],
      "confidence": "medium",
      "quality_status": "draft"
    }
  ]
}
```

- [ ] **Step 2: 校验样例符合 schema 且能生成图写入计划**

Run（在 `backend/` 目录）：

```bash
cd backend && python -c "import json,sys; sys.path.insert(0,'.'); from app.services.import_service import validate_import_document, build_graph_write_plan; d=validate_import_document(json.load(open('app/fixtures/games/animal_well.json',encoding='utf-8'))); build_graph_write_plan(d); print('OK', d.candidate.id)"
```

Expected: 打印 `OK game_animal_well`，无异常。
若报 `extra fields` / `min_length` / `EvidenceRef requires url or quote_or_summary` 等，回到 Step 1 修正字段。

- [ ] **Step 3: 提交**

```bash
git add backend/app/fixtures/games/animal_well.json
git commit -m "feat: add Chinese atomic-tag reference sample animal_well.json"
```

---

## Task 2: 创建共享词表 `preferred-terms.md`

**Files:**
- Create: `.claude/skills/researching-games-for-import/preferred-terms.md`

- [ ] **Step 1: 写词表文件**

从 Task 1 样例的原子标签提取初值，创建 `.claude/skills/researching-games-for-import/preferred-terms.md`：

```markdown
# 首选词表 preferred-terms

生成游戏导入文档时，下列「会进图建节点」的字段**优先从本表选词**；表里确无合适词时才造新词，
并在交付 JSON 的同时、在对话里单独列出本次新增的词，供人工决定是否回填本表。

规则：全部简体中文；一个名词或 1–4 字名词短语；去掉「玩法/机制/系统/参考/设计/体验」等填充后缀；
不写整句；一个特征一项，复合短语拆开。专有名词（游戏名/人名/引擎/语言）保留原文。

## 机制 Mechanic
- 多用途道具
- 非线性探索
- 翻屏房间
- 分层秘密
- 社区协作解谜   别名: ARG
- 非战斗
- 生物应对
- 能力门控探索   别名: 能力解锁通行, 锁钥式推进

## 玩家行为 PlayerAction
- 平台跳跃
- 翻屏移动
- 道具运用
- 生物驱避
- 秘密解谜

## 玩家决策 PlayerDecision
- 道具选择
- 探索路线
- 秘密取舍
- 社区协作

## 体验 Experience
- 氛围营造   别名: 诡异, 压抑, 孤独
- 探索发现
- 涌现玩法
- 战斗精通

## 可玩性来源 ReplayabilitySource
- 分层秘密
- 社区协作解谜
- 速通
- 彩蛋收集

## 生产约束 ProductionConstraint
- 独立开发
- 自研引擎
- 低分辨率
- 无武器战斗
- 无过场动画

## 创新模式 InnovationPattern
- 多用途道具
- 分层秘密
- 社区协作解谜

## 可复用参考模式 ReferencePattern
- 多用途道具
- 分层秘密
- 自我限制设计

## 不可复制风险 Risk
- 超长开发周期
- 自研引擎
- 大规模玩家社区

## 参考价值标签 ReferenceTag
- 多用途道具
- 分层秘密
- 独立开发

## 概念 Concept（claims 的 object）
- 谜题深度
- 社区长尾参与
```

- [ ] **Step 2: 校验文件存在且结构完整**

Run：

```bash
grep -c "^## " .claude/skills/researching-games-for-import/preferred-terms.md
```

Expected: 输出 `11`（11 个维度分组标题）。

- [ ] **Step 3: 提交**

```bash
git add .claude/skills/researching-games-for-import/preferred-terms.md
git commit -m "feat: add shared preferred-terms controlled vocabulary"
```

---

## Task 3: 修改技能 `SKILL.md` 注入新规则

**Files:**
- Modify: `.claude/skills/researching-games-for-import/SKILL.md`

- [ ] **Step 1: 更新「样例」指向（balatro.json 已删除）**

把第 24 行：

```markdown
- Filled sample to copy from: `backend/app/fixtures/games/balatro.json`
```

改为：

```markdown
- Filled sample to copy from: `backend/app/fixtures/games/animal_well.json`（中文 + 原子标签）
```

- [ ] **Step 2: 删除过时的 balatro `reviewed` 警示**

删除「Confidence calibration」一节里这段（balatro.json 已不存在）：

```markdown
⚠️ The `balatro.json` sample shows `quality_status: "reviewed"` because it was hand-curated. **Do not copy `reviewed` from it** — your generated output is `draft`.
```

替换为：

```markdown
⚠️ 样例 `animal_well.json` 的生成内容用 `draft`（强证据但未经人工复核）。**不要**给机器生成内容标 `reviewed`。
```

- [ ] **Step 3: 新增「输出规范」一节**

在「## Field guidance」一节**之前**插入下面整节：

````markdown
## 输出规范：语言、原子化、词表（本项目硬约束）

**1. 全中文**：所有生成文本一律简体中文——散文字段、原子标签、`reference_value_tags`、claims（`subject`/`object`/`explanation`）、各 `EvidenceRef` 的 `quote_or_summary`/`notes`。例外：专有名词（游戏标题、人名、引擎/语言如 `C++`、平台名）保留原文；引用页若为外文，其 `url`/`title` 按实保留，但 `notes`/`quote_or_summary` 用中文转述。

**2. 散文 vs 原子标签，分开处理**：
- **散文字段**（写成完整中文句子）：`short_description`、`selection_reason`、`one_sentence_summary`、`core_loop`、`progression_model`、`failure_model`、`content_structure`、claim 的 `explanation`、所有 evidence 文本。
- **原子标签字段**（会进图建节点，必须原子）：`main_player_actions`、`main_player_decisions`、`main_player_experiences`、`main_mechanics`、`replayability_sources`、`production_constraints`、`innovation_patterns`、`reusable_reference_patterns`、`non_replicable_risks`、`reference_value_tags[].tag`、`claims[].object`（以及 `claims[].subject`）。

**3. 原子标签格式**：一个名词或 1–4 字中文名词短语；去掉「玩法/机制/系统/参考/设计/体验」等填充后缀；不写整句；一个特征一项，复合短语拆成多项。粒度取中：禁用「类银河城」这类把所有游戏连成一片的全集级词；也别只用「翻屏房间」这种仅一款独有的过窄词，优先想还能不能更通用。

bad → good：
| 描述性短语（错） | 原子标签（对） |
|---|---|
| `multi-purpose toy/tool usage` | `多用途道具` |
| `nonlinear flip-screen exploration` | `非线性探索`、`翻屏房间` |
| `an unsettling, eerie atmosphere` | `氛围营造`、`诡异` |
| `solo-developer custom-engine reference` | `独立开发`、`自研引擎` |

**4. 优先选词 + 新词上报**：原子标签**优先从 `preferred-terms.md`（与本技能同目录）选词**；表里确无合适词才造新词。由于文档 schema 禁止额外字段，新词**不能**塞进 JSON——交付 JSON 的同时，在对话里单独列出「本次用到、但词表里没有的新词」，供人工决定是否回填 `preferred-terms.md`。
````

- [ ] **Step 4: 校验改动落地**

Run：

```bash
grep -c "输出规范：语言、原子化、词表" .claude/skills/researching-games-for-import/SKILL.md && grep -c "balatro" .claude/skills/researching-games-for-import/SKILL.md
```

Expected: 第一条输出 `1`（新节存在）；第二条输出 `0`（balatro 引用已全部清除）。

- [ ] **Step 5: 提交**

```bash
git add .claude/skills/researching-games-for-import/SKILL.md
git commit -m "feat: add Chinese + atomic-tag output rules to import skill"
```

---

## Task 4: 修改字段指令模板 `game-import-prompt.md`

**Files:**
- Modify: `docs/superpowers/import-guide/game-import-prompt.md`

- [ ] **Step 1: 在硬规则里追加中文+原子约束**

在「硬规则」列表（以 `> - 每个 EvidenceRef 必须有 title 与 notes` 结尾那条）**之后**，追加三条：

```markdown
> - **全部输出简体中文**；专有名词（游戏名/人名/引擎/语言如 `C++`）保留原文。
> - **进图字段必须是原子标签**：`main_player_actions` / `main_player_decisions` / `main_player_experiences` / `main_mechanics` / `replayability_sources` / `production_constraints` / `innovation_patterns` / `reusable_reference_patterns` / `non_replicable_risks` / `reference_value_tags[].tag` / `claims[].object`（含 `subject`）——每项一个名词或 1–4 字名词短语，不写整句、不带「玩法/参考/设计」等填充后缀，复合的拆成多项。散文字段（各 `*_summary`/`core_loop`/`progression_model`/`failure_model`/`content_structure`/`explanation`/evidence 文本）写成完整中文句子。
> - **原子标签优先从 `.claude/skills/researching-games-for-import/preferred-terms.md` 选词**；没有合适的才造新词，并在交付 JSON 时另行列出新词供人工回填。
```

- [ ] **Step 2: 在 JSON 骨架里标注原子字段**

把骨架中这几行的注释改成（标明「原子」）：

```jsonc
    "main_player_actions": ["..."],        // 原子标签
    "main_player_decisions": ["..."],      // 原子标签
    "main_player_experiences": ["..."],    // 原子标签
    "main_mechanics": ["..."],             // 原子标签
    "replayability_sources": ["..."],      // 原子标签
    "production_constraints": ["..."],     // 原子标签
    "innovation_patterns": ["..."],        // 原子标签
    "reusable_reference_patterns": ["..."],// 原子标签
    "non_replicable_risks": ["..."],       // 原子标签
```

并把 claim 的 `object` 注释改为：

```jsonc
      "object": "<客体概念，原子标签>",
```

- [ ] **Step 3: 更新样例指向**

把「## 真实样例」一节内容：

```markdown
见 `backend/app/fixtures/games/balatro.json`，可照着改游戏名复用。
```

改为：

```markdown
见 `backend/app/fixtures/games/animal_well.json`（中文 + 原子标签），可照着改游戏名复用。
```

- [ ] **Step 4: 校验改动落地**

Run：

```bash
grep -c "进图字段必须是原子标签" docs/superpowers/import-guide/game-import-prompt.md && grep -c "balatro" docs/superpowers/import-guide/game-import-prompt.md
```

Expected: 第一条输出 `1`；第二条输出 `0`。

- [ ] **Step 5: 提交**

```bash
git add docs/superpowers/import-guide/game-import-prompt.md
git commit -m "docs: add Chinese + atomic-tag rules to game-import prompt"
```

---

## Task 5: 端到端验证 —— 生成种子游戏并验证跨游戏连接

**Files:**
- Create: `backend/app/fixtures/games/<slug>.json` ×2（由技能生成，文件名取自游戏 slug）

- [ ] **Step 1: 用更新后的技能生成 2 款种子游戏**

调用 `researching-games-for-import` 技能，对 2 款与 Animal Well 有共性的类银河城游戏（例如 Hollow Knight、Ori and the Blind Forest）各生成一个文档，保存到 `backend/app/fixtures/games/`。技能应遵守新规则：中文、原子标签、优先从 `preferred-terms.md` 选词（如氛围相关复用 `氛围营造`、传送/探索复用 `非线性探索`、独立团队复用 `独立开发`），并在产出后列出新词。

- [ ] **Step 2: 把新词回填词表**

把 Step 1 技能报告的新词，人工挑选合理者追加进 `.claude/skills/researching-games-for-import/preferred-terms.md` 对应分组。

- [ ] **Step 3: 校验两份新 JSON 合法**

Run（把 `<slug>` 换成实际文件名，逐个执行）：

```bash
cd backend && python -c "import json,sys; sys.path.insert(0,'.'); from app.services.import_service import validate_import_document, build_graph_write_plan; d=validate_import_document(json.load(open('app/fixtures/games/<slug>.json',encoding='utf-8'))); build_graph_write_plan(d); print('OK', d.candidate.id)"
```

Expected: 每个都打印 `OK game_<slug>`。

- [ ] **Step 4: 清空 Neo4j 旧节点并重新入库全部 3 款**

先确保后端 + Neo4j 在跑（`cd backend && docker compose up -d neo4j` + `uvicorn app.main:app --reload`）。

清库（Neo4j Browser `http://localhost:7474` 执行，清掉之前 8 款英文残留）：

```cypher
MATCH (n) DETACH DELETE n;
```

入库 3 款：

```bash
cd backend && python scripts/import_games.py app/fixtures/games/
```

Expected: 打印 `3/3 imported via http://...`。

- [ ] **Step 5: 验证跨游戏连接（验收核心）**

Neo4j Browser 执行诊断 Cypher：

```cypher
MATCH (g:Game)-->(n) WHERE NOT n:Game
WITH n, labels(n)[0] AS label, count(DISTINCT g) AS games
WHERE games >= 2
RETURN label, n.name, games ORDER BY games DESC;
```

Expected: 返回**若干被 ≥2 个游戏共享的节点**（例如 `氛围营造`、`非线性探索`、`独立开发` 等），且语义合理。若返回为空或仅 1 条，说明技能没有有效复用词表 —— 回到 Step 1 检查是否真的从 `preferred-terms.md` 选词、原子粒度是否合适。

- [ ] **Step 6: 提交种子游戏与词表更新**

```bash
git add backend/app/fixtures/games/ .claude/skills/researching-games-for-import/preferred-terms.md
git commit -m "feat: add seed games and grow vocabulary; verify cross-game links"
```

---

## 自检对照（spec 覆盖）

- 收敛三要素：原子粒度（Task 1/3/4）、共享词表（Task 2/3/4）、全中文（Task 1/3/4）✅
- 散文 vs 原子字段分离：Task 3 Step 3 明确字段清单 ✅
- 进图字段全覆盖（9 个 PROFILE_LIST_EDGES + tags + claims.object）：Task 3/4 字段清单 ✅
- claims subject/object 中文+原子：Task 1 样例 + Task 3/4 规则 ✅
- 无历史迁移 / 清空 Neo4j：Task 5 Step 4 ✅
- 后端不动：本计划无任何 `backend/app` 代码改动，仅新增 fixtures 数据 ✅
- 验收用诊断 Cypher：Task 5 Step 5 ✅
- balatro.json 死引用清除：Task 3 Step 1-2、Task 4 Step 3 + grep 校验 ✅
