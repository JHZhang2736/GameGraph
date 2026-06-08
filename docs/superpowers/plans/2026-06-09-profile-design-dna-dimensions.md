# Profile 维度扩展(design-DNA)实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `GameDesignProfile` 增加 9 个一等设计维度(8 个进图原子维度 + 1 个散文 `core_hook`),让游戏在美术/音频/视角/主题/叙事/类型/手感/团队等更多角度上跨游戏连接。

**Architecture:** 沿用现有「`PROFILE_LIST_EDGES`(profile 列表字段 → 边/节点)」机制——加 8 行就自动建节点建边,repository 白名单从该表派生、无需改。`core_hook` 是散文,存入 `Game` 节点属性(与其它散文字段一致)。schema 与数据必须同步改以保持 StrictBaseModel 校验通过。

**Tech Stack:** Pydantic schema、FastAPI、Neo4j、pytest、JSON fixtures、Markdown 词表/技能。

设计依据:本会话 brainstorming 结论(用户确认:范围=完备 design-DNA;`core_hook` 散文不进图;`team_model` 纳入)。

---

## 设计:9 个新字段

| 字段 | 节点 label | 边类型 | 形态 |
|---|---|---|---|
| `genre` | `Genre` | `HAS_GENRE` | 原子必填 list |
| `art_style` | `ArtStyle` | `HAS_ART_STYLE` | 原子必填 list |
| `audio_style` | `AudioStyle` | `HAS_AUDIO_STYLE` | 原子必填 list |
| `perspective` | `Perspective` | `HAS_PERSPECTIVE` | 原子必填 list |
| `theme` | `Theme` | `HAS_THEME` | 原子必填 list |
| `narrative_style` | `NarrativeStyle` | `HAS_NARRATIVE_STYLE` | 原子必填 list |
| `game_feel` | `GameFeel` | `HAS_GAME_FEEL` | 原子必填 list |
| `team_model` | `TeamModel` | `HAS_TEAM_MODEL` | 原子必填 list |
| `core_hook` | —(存 Game 属性) | — | **散文必填 str** |

**归并规则**(消除与新维度重叠):`production_constraints` 里的团队项→`team_model`、美术项→`art_style`、音频项→`audio_style`,移走后 production_constraints 只留真正的成本/技术/自我限制事实。

## 文件结构

| 文件 | 动作 |
|---|---|
| `backend/app/schemas/artifacts.py` | `GameDesignProfile` 加 9 字段 |
| `backend/app/services/import_service.py` | `PROFILE_LIST_EDGES` 加 8 行;`_game_node` 加 `core_hook` 属性 |
| `backend/tests/test_import_service.py` | `profile_payload()` 补 9 字段 |
| `backend/tests/test_game_import_document.py` | `valid_profile_kwargs()` 补 9 字段 |
| `backend/tests/test_game_repository_integration.py` | 把 balatro→animal_well(integration,顺带修) |
| `backend/app/fixtures/games/animal_well.json` | 补 9 字段 + 归并 |
| `backend/app/fixtures/games/hollow_knight.json` | 补 9 字段 + 归并 |
| `backend/app/fixtures/games/ori_and_the_blind_forest.json` | 补 9 字段 + 归并 |
| `.claude/skills/researching-games-for-import/preferred-terms.md` | 加 8 个词表组 |
| `.claude/skills/researching-games-for-import/SKILL.md` | 原子字段清单加 8 项、散文清单加 core_hook |
| `docs/superpowers/import-guide/game-import-prompt.md` | 硬规则字段清单 + JSON 骨架加 9 字段 |

---

## Task 1: 后端 schema + 接线 + 内存测试 + animal_well fixture(保持单元测试绿)

schema 变必填后,任何被加载/构造的 profile 都必须含新字段。单元测试里:`test_import_service` / `test_game_import_document` 用**内存 payload**,`test_import_api` 加载 **animal_well.json**。故本任务把它们一起改,确保 `pytest -m "not integration"` 绿。

**Files:** 见下各步。Work from `D:\Files\GameGraph`。

- [ ] **Step 1: artifacts.py 加 9 字段**

`backend/app/schemas/artifacts.py` 的 `GameDesignProfile`:在 `one_sentence_summary: str = Field(min_length=1)` 这一行**后面**插入:
```python
    core_hook: str = Field(min_length=1)
```
并在 `non_replicable_risks: list[NonEmptyStr] = Field(min_length=1)` 这一行**后面**插入:
```python
    genre: list[NonEmptyStr] = Field(min_length=1)
    art_style: list[NonEmptyStr] = Field(min_length=1)
    audio_style: list[NonEmptyStr] = Field(min_length=1)
    perspective: list[NonEmptyStr] = Field(min_length=1)
    theme: list[NonEmptyStr] = Field(min_length=1)
    narrative_style: list[NonEmptyStr] = Field(min_length=1)
    game_feel: list[NonEmptyStr] = Field(min_length=1)
    team_model: list[NonEmptyStr] = Field(min_length=1)
```

- [ ] **Step 2: import_service.py 接线**

`backend/app/services/import_service.py`：在 `PROFILE_LIST_EDGES` 字典的最后一项 `"replayability_sources": ("HAS_REPLAYABILITY_SOURCE", "ReplayabilitySource"),` **后面**(闭合 `}` 之前)插入:
```python
    "genre": ("HAS_GENRE", "Genre"),
    "art_style": ("HAS_ART_STYLE", "ArtStyle"),
    "audio_style": ("HAS_AUDIO_STYLE", "AudioStyle"),
    "perspective": ("HAS_PERSPECTIVE", "Perspective"),
    "theme": ("HAS_THEME", "Theme"),
    "narrative_style": ("HAS_NARRATIVE_STYLE", "NarrativeStyle"),
    "game_feel": ("HAS_GAME_FEEL", "GameFeel"),
    "team_model": ("HAS_TEAM_MODEL", "TeamModel"),
```
再在 `_game_node` 的 `properties` 字典里,把 `"one_sentence_summary": profile.one_sentence_summary,` 这一行**后面**插入:
```python
        "core_hook": profile.core_hook,
```

- [ ] **Step 3: 内存测试 payload 补字段**

`backend/tests/test_import_service.py` 的 `profile_payload()` 与 `backend/tests/test_game_import_document.py` 的 `valid_profile_kwargs()`:两处都在 `"one_sentence_summary": ...,` 后面加一行 `"core_hook"`,并在 `"non_replicable_risks": [...],` 后面加 8 个 list 字段。两处用相同内容:
```python
        "core_hook": "Familiar poker rules as an on-ramp to exponential scoring builds.",
```
和(加在 non_replicable_risks 之后):
```python
        "genre": ["roguelike deckbuilder"],
        "art_style": ["abstract card art"],
        "audio_style": ["lo-fi ambient"],
        "perspective": ["top-down UI"],
        "theme": ["playing cards", "casino"],
        "narrative_style": ["minimal framing"],
        "game_feel": ["snappy card play"],
        "team_model": ["solo developer"],
```

- [ ] **Step 4: 集成测试改指向(顺带修 balatro 死引用)**

`backend/tests/test_game_repository_integration.py`:把函数 `balatro_document` 整体改名为 `animal_well_document`,fixture 路径 `"balatro.json"`→`"animal_well.json"`;两个测试体里 `balatro_document()`→`animal_well_document()`,所有 `"game_balatro"`→`"game_animal_well"`,`id="game_balatro"`→`id="game_animal_well"`。`mechanic_count` 那段用的是 `len(document.profile.main_mechanics)`(动态),不用改数值。

- [ ] **Step 5: animal_well.json 补 9 字段 + 归并**

`backend/app/fixtures/games/animal_well.json`:
- 在 `"one_sentence_summary": ...,` 后面加:
```json
    "core_hook": "用一小组多用途玩具撬动层层嵌套的秘密，并把最深的解谜延伸成社区协作的 ARG 元谜题。",
```
- 把 `production_constraints` 改为(移除 `独立开发`,它去 team_model):
```json
    "production_constraints": ["自研引擎", "低分辨率", "无武器战斗", "无过场动画"],
```
- 在 `"non_replicable_risks": [...],` 后面加 8 个字段:
```json
    "genre": ["类银河城", "解谜平台"],
    "art_style": ["像素美术"],
    "audio_style": ["极简音效", "环境音"],
    "perspective": ["横版2D"],
    "theme": ["动物", "超现实"],
    "narrative_style": ["无文字", "环境叙事"],
    "game_feel": ["精准平台"],
    "team_model": ["单人开发"],
```

- [ ] **Step 6: 跑单元测试,必须全绿**

```
cd backend; python -m pytest -q -m "not integration"
```
Expected: 全部 passed(应为 78 passed 或相近,0 failed)。失败则按报错回到对应 Step 修正(常见:某 payload 漏字段、JSON 逗号/中文编码)。

- [ ] **Step 7: 提交**
```
git add backend/app/schemas/artifacts.py backend/app/services/import_service.py backend/tests/test_import_service.py backend/tests/test_game_import_document.py backend/tests/test_game_repository_integration.py backend/app/fixtures/games/animal_well.json
git commit -m "feat: add 9 design-DNA dimensions to GameDesignProfile"
```

---

## Task 2: hollow_knight + ori 两款 fixture 补字段 + 归并

**Files:** `backend/app/fixtures/games/hollow_knight.json`、`backend/app/fixtures/games/ori_and_the_blind_forest.json`

- [ ] **Step 1: hollow_knight.json**

- `"one_sentence_summary": ...,` 后加:
```json
    "core_hook": "把死亡变成必须追回的风险目标（Shade 系统），让广袤地下王国的每一步探索都带着代价与张力。",
```
- `production_constraints` 改为(移除 `小型团队`→team_model、`手绘美术`→art_style):
```json
    "production_constraints": ["Unity 引擎", "众筹资金"],
```
- `"non_replicable_risks": [...],` 后加:
```json
    "genre": ["类银河城", "类魂"],
    "art_style": ["手绘美术"],
    "audio_style": ["管弦乐", "氛围音乐"],
    "perspective": ["横版2D"],
    "theme": ["虫族", "废墟王国"],
    "narrative_style": ["碎片化叙事", "环境叙事"],
    "game_feel": ["精准近战"],
    "team_model": ["小团队"],
```

- [ ] **Step 2: ori_and_the_blind_forest.json**

- `"one_sentence_summary": ...,` 后加:
```json
    "core_hook": "用消耗资源的手动存档与视听情感叙事，把高难跑酷的探索升华成情绪体验。",
```
- `production_constraints` 改为(移除 `小型团队`→team_model、`手绘美术`→art_style、`全管弦乐配乐`→audio_style):
```json
    "production_constraints": ["Unity 引擎"],
```
- `"non_replicable_risks": [...],` 后加:
```json
    "genre": ["类银河城", "平台跳跃"],
    "art_style": ["手绘美术"],
    "audio_style": ["管弦乐"],
    "perspective": ["横版2D"],
    "theme": ["自然", "森林童话"],
    "narrative_style": ["过场驱动", "情感叙事"],
    "game_feel": ["流畅跑酷", "动量"],
    "team_model": ["小团队"],
```

- [ ] **Step 3: 校验两份 fixture 合法**

```
cd backend; python -c "import json,sys; sys.path.insert(0,'.'); from app.services.import_service import validate_import_document, build_graph_write_plan
for s in ['hollow_knight','ori_and_the_blind_forest']:
    d=validate_import_document(json.load(open(f'app/fixtures/games/{s}.json',encoding='utf-8'))); build_graph_write_plan(d); print('OK', d.candidate.id)"
```
Expected: 打印 `OK game_hollow_knight` 与 `OK game_ori_and_the_blind_forest`。

- [ ] **Step 4: 提交**
```
git add backend/app/fixtures/games/hollow_knight.json backend/app/fixtures/games/ori_and_the_blind_forest.json
git commit -m "feat: add design-DNA dimensions to hollow_knight and ori fixtures"
```

---

## Task 3: 词表 preferred-terms.md 加 8 个维度组

**Files:** `.claude/skills/researching-games-for-import/preferred-terms.md`

- [ ] **Step 1: 在文件末尾追加 8 个分组**(取自三款游戏的取值)
```markdown

## 类型 Genre
- 类银河城
- 解谜平台
- 平台跳跃
- 类魂
- 类肉鸽

## 美术风格 ArtStyle
- 像素美术
- 手绘美术
- 低多边形
- 极简风格

## 音乐音效 AudioStyle
- 管弦乐
- 氛围音乐
- 极简音效
- 环境音
- 芯片音乐
- 动态配乐

## 视角呈现 Perspective
- 横版2D
- 俯视
- 等距
- 第一人称

## 主题题材 Theme
- 动物
- 超现实
- 虫族
- 废墟王国
- 自然
- 森林童话
- 宗教
- 神话

## 叙事手法 NarrativeStyle
- 环境叙事
- 碎片化叙事   别名: lore
- 无文字
- 过场驱动
- 情感叙事

## 操作手感 GameFeel
- 精准平台
- 精准近战
- 流畅跑酷
- 动量
- 厚重打击

## 团队模式 TeamModel
- 单人开发
- 小团队
- 众筹
```
并在 `## 生产约束 ProductionConstraint` 组里删除 `- 独立开发`(已迁至 TeamModel 的 `单人开发`)。

- [ ] **Step 2: 校验分组数**
```
(Get-Content .claude/skills/researching-games-for-import/preferred-terms.md | Select-String '^## ').Count
```
Expected: `19`(原 11 + 新 8)。

- [ ] **Step 3: 提交**
```
git add .claude/skills/researching-games-for-import/preferred-terms.md
git commit -m "feat: add 8 design-DNA vocabulary groups to preferred-terms"
```

---

## Task 4: 更新 SKILL.md 与 prompt 的字段清单/骨架

**Files:** `.claude/skills/researching-games-for-import/SKILL.md`、`docs/superpowers/import-guide/game-import-prompt.md`

- [ ] **Step 1: SKILL.md 输出规范节**

在「## 输出规范」第 2 条里:
- **散文字段**清单末尾(`content_structure` 之后、claim 之前)加入 `core_hook`。
- **原子标签字段**清单的 `reference_value_tags[].tag` **之前**插入这 8 个:`genre`、`art_style`、`audio_style`、`perspective`、`theme`、`narrative_style`、`game_feel`、`team_model`。
即把原子清单改为包含:`main_player_actions`、`main_player_decisions`、`main_player_experiences`、`main_mechanics`、`replayability_sources`、`production_constraints`、`innovation_patterns`、`reusable_reference_patterns`、`non_replicable_risks`、`genre`、`art_style`、`audio_style`、`perspective`、`theme`、`narrative_style`、`game_feel`、`team_model`、`reference_value_tags[].tag`、`claims[].object`(及 `subject`)。

- [ ] **Step 2: game-import-prompt.md 硬规则**

把那条「进图字段必须是原子标签」的字段清单扩充进上面 8 个新字段;并新增一条散文说明:
```
> - `core_hook`（核心创意/钩子）是**一句话散文**：用一句中文点出这款游戏最差异化的卖点，不拆成标签。
```

- [ ] **Step 3: game-import-prompt.md JSON 骨架**

在骨架 `"one_sentence_summary": "...",` 后加 `"core_hook": "<一句话核心创意/钩子>",`；在 `"non_replicable_risks": ["..."],` 后加:
```jsonc
    "genre": ["..."],                      // 原子标签
    "art_style": ["..."],                  // 原子标签
    "audio_style": ["..."],                // 原子标签
    "perspective": ["..."],                // 原子标签
    "theme": ["..."],                      // 原子标签
    "narrative_style": ["..."],            // 原子标签
    "game_feel": ["..."],                  // 原子标签
    "team_model": ["..."],                 // 原子标签
```

- [ ] **Step 4: 校验**
```
(Get-Content .claude/skills/researching-games-for-import/SKILL.md -Raw | Select-String 'team_model').Matches.Count
```
Expected: ≥1。并用 Grep 确认 `game-import-prompt.md` 含 `"team_model": ["..."]`。

- [ ] **Step 5: 提交**
```
git add .claude/skills/researching-games-for-import/SKILL.md docs/superpowers/import-guide/game-import-prompt.md
git commit -m "docs: document 9 design-DNA fields in skill and import prompt"
```

---

## Task 5: 端到端 —— 重新入库三款并验证新维度连接

**Files:** 无新增(纯验证)。需后端(8100/8101)+ Neo4j(7687)在跑;凭据读 `backend/.env`(密码形如 `!Zhang001019`,实际以 .env 为准)。

- [ ] **Step 1: 清空 Neo4j 并重新入库 3 款**

```
cd backend; python -c "from neo4j import GraphDatabase; import os; d=GraphDatabase.driver('bolt://localhost:7687',auth=('neo4j', open('.env').read().split('NEO4J_PASSWORD=')[1].splitlines()[0].strip())); s=d.session(); s.run('MATCH (n) DETACH DELETE n'); print('wiped'); s.close(); d.close()"
python scripts/import_games.py app/fixtures/games/
```
Expected: 打印 `wiped` 与 `3/3 imported via http://...`。(若 8100 被占,脚本可能用 8101——只要后端连同一个 Neo4j 即可。)

- [ ] **Step 2: 诊断 Cypher 验证新维度成桥**

```
cd backend; python -c "from neo4j import GraphDatabase; d=GraphDatabase.driver('bolt://localhost:7687',auth=('neo4j', open('.env').read().split('NEO4J_PASSWORD=')[1].splitlines()[0].strip())); s=d.session(); rows=s.run('MATCH (g:Game)-->(n) WHERE NOT n:Game WITH n, labels(n)[0] AS label, count(DISTINCT g) AS games WHERE games>=2 RETURN label, n.name AS name, games ORDER BY games DESC, label').data(); [print(r) for r in rows]; print('SHARED_NODES', len(rows)); newlabels=[r for r in rows if r['label'] in ('Genre','ArtStyle','AudioStyle','Perspective','Theme','NarrativeStyle','GameFeel','TeamModel')]; print('NEW_DIM_BRIDGES', len(newlabels)); s.close(); d.close()"
```
Expected:`SHARED_NODES` 比上一轮(22)更多;且 `NEW_DIM_BRIDGES > 0`——能看到 `Genre 类银河城 (3)`、`Perspective 横版2D (3)`、`ArtStyle 手绘美术 (2)`、`AudioStyle 管弦乐 (2)`、`NarrativeStyle 环境叙事 (2)`、`TeamModel 小团队 (2)` 等新维度节点。若 `NEW_DIM_BRIDGES==0`,说明 fixtures 未正确入库或字段未生效,回查 Task 1/2。

- [ ] **Step 3: 无文件改动,无需提交**(若 Step 1 误改了文件则不提交)。把 Step 2 的完整输出记入报告。

---

## 自检对照
- 9 字段全部落到 schema(Task1 S1)、接线(Task1 S2)、3 fixtures(Task1 S5 + Task2)、词表(Task3)、技能/prompt(Task4)、验证(Task5)✅
- 必填:全部 `min_length=1`,内存测试与 3 fixtures 同步补齐 → 单元测试绿(Task1 S6)✅
- 归并:团队/美术/音频项从 production_constraints 迁出(Task1 S5、Task2)✅
- core_hook 散文:schema str、存 Game 属性(Task1 S2)、prompt 说明(Task4 S2)✅
- balatro 死引用:集成测试改指向 animal_well(Task1 S4)✅
- 端到端新维度连接证据(Task5 S2)✅
