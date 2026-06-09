# 6.6 机会框架模块设计 Spec

## 1. 目的

把**单个被选中的机会区域 (`OpportunityArea`，6.5 产物)** 深挖成一个**完整、可独立阅读的创意简报 (`OpportunityFrame`)**，作为 6.7 概念生成模块的输入。

6.6 是整份系统设计里「先有证据再生成」这条铁律的**最后一道闸**(规格 §4：「最重要的边界位于『机会框架』和『概念生成』之间」)。它必须把支撑某个机会的来源游戏、机制、体验、约束、创新模式**组装成有边界的简报**，定义**允许的变形**与**禁止的方向**，让推理明确到人类可以质疑审查——然后才轮到 6.7 在这个框架内具象化。

本模块在 6.5(机会匹配)下游、6.7(概念生成)上游。

## 2. 核心模型:被选中区域 → 框架

与 6.5「铺开候选 → 用户挑选」的产品流程对齐:

```
6.5: 开发者画像 + 图谱 → 一批候选机会区域(跨 safe/balanced/challenging)
                              │  用户在前端挑中其中【一个】
                              ▼
6.6: 单个被选中的 OpportunityArea → 深挖成一个 OpportunityFrame
```

**粒度锁定:1 个被选中的 `OpportunityArea` → 1 个 `OpportunityFrame`(1:1)。**

- 不做「每个候选都 1:1 富化」(那是对未深挖的候选做昂贵 LLM 综合;候选列表的富化是 6.5 自己的事，它已给出 `fit_reason / risk_reason / risk_posture`)。
- 不做「按锚点聚类」(用户挑的是「某 anchor × 某具体变形」这一条，聚类会把没选的变形糊进来)。

框架的脊梁 = 被选中那个变形;它必须在产物里**显式可辨**(见 §9)。

## 3. 设计哲学边界:确定性引擎 + LLM 综合层

严守 6.5 立下的两层架构——**LLM 绝不发明候选、绝不自己数稀缺度，只在确定性引擎给出的有界材料上做综合**。在 6.6 上的落地:

| 层 | 在 6.6 负责 | 为什么由它负责 |
|---|---|---|
| **确定性引擎**(不碰 LLM) | ① 按 area 的 anchor + evidence 游戏查图谱，取 `related_mechanics / related_player_experiences / related_constraints / related_innovation_patterns`;② 按 anchor 重跑 6.5 枚举，产「未选中但有证据」的**次变形池**;③ 组装 `source_game_ids` 证据闭包与 `evidence_path`;④ 从画像硬约束确定性产出 `forbidden_directions` 基底 | 客观、可追溯、可审计(呼应规格 §6.10) |
| **LLM 综合层**(只综合，不发明) | ① 写 `opportunity_area` 主题标签;② 把**主变形**具象化成 `recommended_transformations[0]`，再从**次变形池**里挑选/排序/叙述出后续条目;③ 把 dead-zone 次变形 + 硬约束写成 `forbidden_directions` 叙述;④ 写 `fit_reason / risk_reason` | 需要自然语言综合与设计常识 |

**不可逾越的边界:**

- LLM 不得引入 source games 证据之外的机制/参考。
- LLM 不得 mint 一个图谱里零证据的次变形——`recommended_transformations` 的来源**只允许两类**:
  - **(a) 主变形的具象化**:对 locked 的那一个变形给几种落地执行方式(纯「具象化」，本就在哲学允许范围内)。这是主体。
  - **(b) 同证据的次变形**:必须来自确定性引擎对该 anchor 枚举出来、只是没被选中、且有证据的变形。LLM 只能从这份确定性菜单**挑选/排序/叙述**。
- LLM 不得篡改 anchor 或被选中的主变形。

### 3.1 6.5 与 6.6 是同一套确定性枚举的两次使用

6.5 的 `enumerate_candidates / rank_candidates`(`opportunity_service.py`)被 6.6 **直接复用、零重复实现**:

- 6.5 用它在**全库锚点**上枚举候选 → 用户挑选。
- 6.6 用它在**单个 anchor** 上枚举 → 排除已选中那条 → 得到**次变形池 (b)**。

`forbidden_directions` 自然接住次变形池里的 **dead-zone**(看似新颖但不自洽/做不出)——与 6.5 用「可行性闸」区分 white-space / dead-zone **同源自洽**。6.5 把 dead-zone 路由到 `rejected[]`;6.6 把(同 anchor 下的)dead-zone 写成禁止方向。

## 4. 数据流

```
{ profile: DeveloperProfile, area: OpportunityArea }
   │
   ▼ [确定性引擎]  app/services/opportunity_frame_service.py
     ① source_game_ids = anchor ∪ target_value_game_ids ∪ combination_game_ids (去重保序)
     ② fetch_game_design_facts(source_game_ids) → related_* 并集
     ③ 次变形池 = enumerate_candidates(全库) |> 过滤 anchor==area.anchor |> rank |> 排除 area.id
     ④ evidence_path = 确定性人读路径
     ⑤ forbidden_directions 基底 = 画像中 type==hard 的约束
   │
   ▼ [LLM 综合层]  app/services/opportunity_frame_llm.py
     opportunity_area 标签 / recommended_transformations(主[0]+次) /
     forbidden_directions 叙述 / fit_reason / risk_reason
     (未配置或调用失败 → 降级:见 §7)
   │
   ▼ OpportunityFrame  (+ warnings[])
```

LLM **只回填叙述字段**;`source_game_ids / related_* / evidence_path` 全部由确定性引擎产出、原样透传。

## 5. 数据结构 (schema)

`OpportunityFrame` 已存在于 `app/schemas/artifacts.py`，字段名 = 前端 `lib/types/index.ts` 形状，**不改字段名**。本期**唯一的 schema 改动**:新增可选 `warnings`。

```python
class OpportunityFrame(StrictBaseModel):
    id: str
    developer_profile_id: str
    opportunity_area: str                          # LLM 写的主题标签
    source_game_ids: list[NonEmptyStr]             # 确定性:证据闭包
    related_mechanics: list[NonEmptyStr]           # 确定性:HAS_MECHANIC
    related_player_experiences: list[NonEmptyStr]  # 确定性:DELIVERS_EXPERIENCE
    related_constraints: list[NonEmptyStr]         # 确定性:CONSTRAINED_BY
    related_innovation_patterns: list[NonEmptyStr] # 确定性:USES_INNOVATION
    recommended_transformations: list[NonEmptyStr] # [0]=主变形(约定，见 §9);其余=次变形
    forbidden_directions: list[NonEmptyStr]        # 硬约束基底 + LLM dead-zone 叙述
    evidence_path: list[NonEmptyStr]               # 确定性:可追溯路径
    fit_reason: str
    risk_reason: str
    warnings: list[NonEmptyStr] = Field(default_factory=list)   # 【新增】可选,降级可见
```

> **跨模块契约改动**:后端给 `OpportunityFrame` 加 `warnings`(默认 `[]`);前端 `lib/types/index.ts` 同步加 `warnings?: string[]`。加性可选字段,现有 `/opportunities` mock 页不受影响,且复用 6.5 既有的 warnings 提示条渲染。**否决「未配置 LLM 直接 503」**——必须与 6.5「LLM 可选 + 降级保留」一致,否则本地无 LLM 时整条创意流程断在 6.6。

`id` 生成:`frame|{area.id}`(area.id 已唯一含 anchor/kind/dimension/to_value)。

## 6. 确定性引擎

`app/services/opportunity_frame_service.py`(编排)+ `app/graph/opportunity_repository.py`(新增只读查询)。

### 6.1 source_game_ids(证据闭包)

```
source_game_ids = dedup_preserve_order(
    [area.anchor_game_id] + area.evidence.target_value_game_ids + area.evidence.combination_game_ids
)
```

### 6.2 related_*(新增图查询)

现有 `fetch_game_dimensions` 只查 4 个维度,**不含**机制/体验/约束/创新模式。新增:

```python
@dataclass
class GameDesignFacts:
    game_id: str
    mechanics: list[str]
    experiences: list[str]
    constraints: list[str]
    innovation_patterns: list[str]

class OpportunityRepository:
    def fetch_game_design_facts(self, game_ids: list[str]) -> list[GameDesignFacts]: ...
```

只读 Cypher(方向均 `(Game)-[:REL]->(X)`,取 `x.name`,与 `fetch_game_dimensions` 一致):

```cypher
MATCH (g:Game) WHERE g.id IN $game_ids
RETURN g.id AS game_id,
       [(g)-[:HAS_MECHANIC]->(x)        | x.name] AS mechanics,
       [(g)-[:DELIVERS_EXPERIENCE]->(x) | x.name] AS experiences,
       [(g)-[:CONSTRAINED_BY]->(x)      | x.name] AS constraints,
       [(g)-[:USES_INNOVATION]->(x)     | x.name] AS innovation_patterns
```

`related_*` = 各 source game 对应列表的**并集**(去重保序)。截断由前端负责(chips 上限 + 展开),后端不预截。

> **边类型已实查核对**(对照 `import_service.PROFILE_LIST_EDGES`,2026-06-09):

| 字段 | 边类型 | 目标 label |
|---|---|---|
| `related_mechanics` | `HAS_MECHANIC` | `Mechanic` |
| `related_player_experiences` | `DELIVERS_EXPERIENCE` | `Experience`(**非** `PlayerExperience`) |
| `related_constraints` | `CONSTRAINED_BY` | `ProductionConstraint` |
| `related_innovation_patterns` | `USES_INNOVATION` | `InnovationPattern` |

### 6.3 次变形池 (b)

复用 6.5 `opportunity_service`,零重复实现:

```python
games = repository.fetch_game_dimensions()
pool = rank_candidates([
    c for c in enumerate_candidates(games)
    if c.anchor_game_id == area.anchor_game_id and c.id != area.id
])
```

把 `pool` 连同被选中的 `area` 一起喂给 LLM 综合层(LLM 只能从 `pool` 里挑/排/叙述次变形)。

### 6.4 evidence_path(确定性、可追溯)

确定性组装成人读路径(保证可审计,呼应规格 §6.10),例如:

```
["锚点 vampire_survivors 提供成熟配方",
 "目标值『第一人称』在 game_x / game_y 上有据",
 "该组合在策展库中稀缺(existing_combination_count=0)"]
```

### 6.5 forbidden_directions 基底

画像中 `type == hard` 的每条约束 → 一条确定性禁止项(原文转述)。LLM 再叠加 dead-zone 次变形的禁止叙述。即使 LLM 缺席,硬约束禁止项也一定在(见 §7 降级)。

## 7. LLM 综合层 + 降级

`app/services/opportunity_frame_llm.py`,仿 `opportunity_llm.py`:OpenAI 兼容 tool-calling、env 配置(复用 `LLM_BASE_URL/LLM_API_KEY/LLM_MODEL/LLM_TIMEOUT`)、可选依赖(未配置返回 `None`)、一次 tool-call。

**输入** = 画像 + 被选中 area(含主变形与证据)+ 次变形池 (b) + 已确定性组装好的 `related_*`。

**输出回填**:`opportunity_area`、`recommended_transformations`(主在 `[0]`,次从 pool 选)、`forbidden_directions` 叙述、`fit_reason`、`risk_reason`。

**System prompt 要点:**
- 主变形是脊梁,必须放 `recommended_transformations[0]` 并具象化为几种落地方式。
- 次变形只能从给定 pool 里挑/排/叙述,**不得发明** pool 之外的变形。
- pool 里看似新颖但不自洽/做不出的(dead-zone)→ 写进 `forbidden_directions` 并说明为何行不通。
- 不得引入 `related_*` / source games 之外的机制或参考。

**降级(未配置 LLM 或调用抛错)**——产出一个仍可用的 frame,几乎无信息损失(因为 6.5 已把判断做完):
- `related_* / source_game_ids / evidence_path`:确定性已就绪,原样。
- `fit_reason / risk_reason`:**直接沿用输入 `area` 自带的**(6.5 已写好)。
- `forbidden_directions`:只用硬约束基底。
- `recommended_transformations`:只含主变形的机械措辞(`[0]`)。
- `opportunity_area`:由 anchor 主类型 + 主变形机械拼出。
- `warnings`:追加「未配置 LLM(或调用失败),框架未做叙述综合与次变形扩展,仅返回确定性证据组装。」(区分「未配置」vs「判断失败」,与 `opportunity_service` 降级一致。)

## 8. API

`app/api/routes_opportunity.py` 新增路由(复用同一 router 与 DI provider):

```
POST /opportunity/frame
  body:  { profile: DeveloperProfile, area: OpportunityArea }   # area 整对象直传,免按 id 回查
  deps:  OpportunityRepository(driver, Depends 注入) + 可选 LLM 客户端
  resp:  OpportunityFrame                                        # 单个
```

请求体用一个薄 Pydantic 包装模型(如 `OpportunityFrameRequest { profile, area }`)。校验失败 → 422。路由薄、委托 service;driver 经 `Depends` 注入、测试用 `dependency_overrides` 覆盖。router 已在 `main.py` 注册(6.5 时完成),无需改动。

## 9. recommended_transformations[0] 约定

**约定型契约(不加字段):`recommended_transformations[0]` 恒为主变形(脊梁),其余为补充次变形。** spec 写死这条;6.6 前端据此把 `[0]` 渲染成 headline,其余作次级。

## 10. 测试(对应规格 §6.6 验收)

| 规格验收 | 测试方式 |
|---|---|
| 框架引用来源游戏 / 有证据论断 | 断言 `source_game_ids` 非空且 = 证据闭包;`related_*` 来自这些游戏的图谱边 |
| 含允许变形 + 禁止方向 | schema 必填 + 断言主变形在 `recommended_transformations[0]`;硬约束逐条进 `forbidden_directions` |
| 反对多人联网的硬约束 → 禁止依赖联网的方向 | service 单测:硬约束基底确定性产出对应禁止项(不依赖 LLM) |
| 弱证据 → 标低置信度 | `evidence_path` 反映 `existing_combination_count` / 佐证规模 |
| 框架可独立阅读 | 契约往返 + 降级路径单测(无 LLM 仍产合法 frame) |
| 次变形不得发明 | LLM stub 返回 pool 外 id/变形 → service 忽略或仅采纳 pool 内,带 warning |

- **引擎**:`fetch_game_design_facts` 走 Neo4j 集成测试(`@pytest.mark.integration`,仿 `test_game_repository_integration`),给定 fixture 断言 `related_*`;纯组装/闭包/次变形池逻辑用 stub repository 单测。
- **LLM 层**:stub 客户端(仿 `test_opportunity_llm` / `test_profile_llm`)。

## 11. 文件清单

| 文件 | 职责 |
|---|---|
| `app/schemas/artifacts.py` | **改**:`OpportunityFrame` 加 `warnings` 可选字段 |
| `app/services/opportunity_frame_service.py` | **新**:确定性组装 + 调 LLM + 降级 + 装配 `OpportunityFrame` |
| `app/services/opportunity_frame_llm.py` | **新**:`OpportunityFrameLlmClient`(仿 `opportunity_llm`) |
| `app/graph/opportunity_repository.py` | **改**:新增 `fetch_game_design_facts(game_ids)` + `GameDesignFacts` |
| `app/api/routes_opportunity.py` | **改**:新增 `POST /opportunity/frame` + 请求包装模型 + LLM provider |
| `tests/test_opportunity_frame_service.py` | **新**:组装/闭包/次变形池/降级单测 |
| `tests/test_opportunity_frame_llm.py` | **新**:LLM stub 行为测试 |
| `tests/test_opportunity_frame_api.py` | **新**:契约往返 + 422 + 降级端到端(stub) |
| `tests/test_opportunity_repository_integration.py` | **改/新**:`fetch_game_design_facts` 集成测试 |

(schema 不新建文件——`OpportunityFrame` 已在 `artifacts.py`。)

## 12. 范围

### 范围内
- 上述新增/改动文件。
- 1 个被选中 area → 1 个 frame(1:1)。
- 确定性:证据闭包、`related_*` 图查询、次变形池(复用 6.5 枚举)、`evidence_path`、硬约束禁止基底。
- LLM 综合层 + 未配置/失败降级。
- `OpportunityFrame.warnings` 可选字段 + 前端 types 同步。

### 范围外(留后续,平滑升级)
- 反转 / 迁移 / 压缩 三类变形(6.5 也未实现,次变形池只含替代/组合)。
- 多 area 聚类成一个 frame、按主题跨锚点聚合(规格 §8 端到端示例的多锚点框架)。
- 框架的服务端持久化(本期前端持有 area 直传)。
- `置信度` 显式分级字段(本期用 evidence 规模隐式反映)。

## 13. 已知局限

- **小库下次变形池稀薄**:种子库现约 8~11 款,单 anchor 下「有证据的次变形」可能很少甚至为空,`recommended_transformations` 退化为只有主变形一条。语义正确(没有就是没有),随入库增长自动变丰。
- **LLM 行为非确定**:叙述综合与次变形的挑选/排序从「确定性可精确测试」变为「LLM 行为测试」(stub 断言),与 `test_opportunity_llm` / `test_profile_llm` 同策略。
- **`fetch_game_design_facts` 未对活库验证**(本地无 Neo4j):靠推理 + 对照 `import_service` 写入路径核对 + 集成测试标记;建议起库跑一次 `-m integration`。
- **evidence_path 为机械模板**:可读但非自然语言精修(刻意保持确定性可审计);如需润色可后续交 LLM,但要保留确定性底本。

## 14. 跨模块共享契约(最终态)

与 6.5 / 前端 agent 对齐确认:

- `POST /opportunity/frame`,body `{ profile, area }` → 单个 `OpportunityFrame`。
- 响应字段名对齐 `frontend/lib/types/index.ts` 的 `OpportunityFrame`,**新增可选 `warnings?: string[]`**(双方都改:后端默认 `[]`,前端 types 加可选)。
- `recommended_transformations[0]` = 主变形(约定型契约)。
- 确定性枚举(`opportunity_service` 的 `enumerate_candidates / rank_candidates`)6.5、6.6 共用,不重复实现。
- 6.5 前端为 C1 纯展示(候选列表 + 被拒 + 警告),6.6 前端独立接 `/opportunity/frame`;两模块互不阻塞,可并发。
