# 手动游戏导入（6.1/6.2）设计 Spec

## 1. 目的

本文档定义独立游戏创意图谱系统中 6.1「精选游戏入库」和 6.2「游戏设计标注」两个模块的**手动导入实现方式**。

这一版**不**搭自动来源抓取、**不**接入实时 LLM adapter。取而代之的工作流是：

```text
人工挑选游戏
-> 把游戏 + 指令模板交给 Claude，生成符合契约的 JSON
-> 经 FastAPI 导入端点校验
-> 写入 Neo4j 设计知识图谱
-> 读回核对
```

本质上是把 **Claude Code 当作 6.2 的标注引擎**，产出符合 schema 的单游戏导入文档，从而推迟「自动 ingestion + 多 provider LLM adapter」这套重基础设施。这与已有后端文档的两条原则一致：「先契约，后基础设施」「Fixture 不是假装智能」。

本文档对应 `2026-06-08-backend-fixture-contract-design.zh-CN.md` 第 12 节「后续扩展方向」中的第 1 步（加 FastAPI route）和第 2 步（加 Neo4j repository）。

## 2. 范围

### 范围内

- 扩展 `backend/app/schemas`：新增完整 `GameDesignProfile`（18 字段）、`ReferenceValueTag`。
- 新增单游戏导入文档 `GameImportDocument`（`candidate` / `profile` / `claims` 三段式）。
- 新增导入服务：校验文档 + 把文档翻译成「图写入操作」描述。
- 新增 Neo4j 连接层与 game repository：把导入文档落成可遍历的图。
- 新增 FastAPI 应用与 `POST /import/game`、`GET /games/{id}` 两个端点。
- 新增 Docker Compose 起本地 Neo4j。
- 新增「让 Claude 生成 JSON」的指令模板、JSON 骨架与一个真实样例。
- 新增导入相关测试；真实数据库测试用标记隔离、默认跳过。

### 范围外

- 自动来源抓取、商店页解析、实时 LLM 调用。
- 6.3 之后的图谱查询/遍历 API（机会匹配、机会框架、概念生成等）。
- 前端工作台。
- PostgreSQL、多用户、权限、任务历史。
- 完整 `ConceptEvaluation`。
- 现有 fixture pipeline 及其测试的改动（保持不变）。

## 3. 设计决策摘要

这些决策已与用户对齐：

1. **存储目标**：FastAPI 导入端点 → Neo4j 入库（不只落 fixture 文件）。
2. **交付边界**：后端负责架构、API 与「Claude 该生成什么 JSON」的契约；实际生成与导入由用户手动操作。
3. **档案完整度**：`GameDesignProfile` 实现完整 18 字段。
4. **证据规则（宽松）**：`evidence` 允许写 Claude 的分析文本（`EvidenceRef.quote_or_summary`），不强制外部 URL；但 `confidence` / `quality_status` 必填且须诚实。仅凭模型知识的论断 `confidence` 不得标 `high`（在指令模板中约束，不在 schema 强制）。
5. **6.1/6.2 合并为单游戏文档**：一款游戏 = 一个 JSON 文件 = 一次导入。文档内部用 `candidate`（无设计知识）与 `profile`/`claims`（带证据）两个子结构保留原设计的证据边界。
6. **DesignClaim 可选 0..n**：profile 必出；claim 只为「非显而易见、可跨概念复用」的洞见而写，由 AI 生成填充。

## 4. 目录结构

```text
backend/
  app/
    __init__.py
    main.py                  # 新增：FastAPI app 装配
    api/
      __init__.py
      routes_import.py        # 新增：POST /import/game, GET /games/{id}
    schemas/
      common.py               # 不变
      artifacts.py            # 扩展：GameDesignProfile, ReferenceValueTag
      import_document.py       # 新增：GameImportDocument
    services/
      fixture_pipeline.py     # 不变
      import_service.py        # 新增：校验 + 翻译为图操作
    graph/
      __init__.py
      connection.py            # 新增：Neo4j driver 工厂 + 配置
      game_repository.py       # 新增：执行图写入 + 读回
    fixtures/
      golden_flow.json        # 不变
      games/
        balatro.json           # 新增：真实样例导入文档
  tests/
    test_artifact_contracts.py        # 不变
    test_fixture_pipeline.py          # 不变
    test_project_structure.py         # 不变
    test_game_import_document.py       # 新增
    test_import_service.py             # 新增
    test_import_api.py                 # 新增
    test_game_repository_integration.py # 新增（@pytest.mark.integration）
  docker-compose.yml          # 新增：Neo4j 服务
  .env.example                # 新增：Neo4j 连接环境变量样例
  pyproject.toml              # 扩展依赖
docs/
  superpowers/
    import-guide/
      game-import-prompt.md   # 新增：Claude 生成指令模板 + JSON 骨架
```

## 5. Schema 层

沿用现有风格：`StrictBaseModel`（`extra="forbid"`、strip whitespace、`validate_assignment`）、`Field(min_length=1)` / `NonEmptyStr`、Pydantic v2。

### 5.1 ReferenceValueTag（新增）

对应原设计 6.2「为标签关联证据、置信度和质量状态」。

必需字段：

- `tag`
- `confidence`
- `quality_status`

可选字段：

- `evidence: list[EvidenceRef]`（默认空列表；体现宽松证据）

### 5.2 GameDesignProfile（新增，完整 18 设计字段 + game_id 引用键）

对应原设计 5.2 的 18 个设计字段（一句话总结、核心循环、玩家行动/决策、体验、机制、成长/失败模型、重玩性、内容结构、制作约束、创新模式、可复用模式、参考价值标签、不可复制风险、证据说明、置信度、质量状态）。`game_id` 是为关联 `candidate` 额外加的引用键，不计入这 18 个设计字段。

标量字段：

- `game_id`（引用键，= `candidate.id`）
- `one_sentence_summary`
- `core_loop`
- `progression_model`
- `failure_model`
- `content_structure`
- `confidence`
- `quality_status`

列表字段（均 `NonEmptyStr`，且非空）：

- `main_player_actions`
- `main_player_decisions`
- `main_player_experiences`
- `main_mechanics`
- `replayability_sources`
- `production_constraints`
- `innovation_patterns`
- `reusable_reference_patterns`
- `non_replicable_risks`

带证据的子结构：

- `reference_value_tags: list[ReferenceValueTag]`（非空）
- `evidence: list[EvidenceRef]`（非空；档案级证据说明）

### 5.3 GameImportDocument（新增）

这是 Claude 要生成的 JSON 形状。

```text
GameImportDocument:
  candidate:  SeedGame                 # 6.1 候选：入库理由/来源，无设计知识
  profile:    GameDesignProfile         # 6.2 档案：完整 18 字段
  claims:     list[DesignClaim] = []    # 6.2 论断：可选 0..n
```

复用现有 `SeedGame`、`DesignClaim`、`EvidenceRef`（无需修改这三者）。

### 5.4 证据宽松规则在 schema 上的落地

- `DesignClaim.evidence` 仍要求至少 1 条 `EvidenceRef`（保留结构）。
- `EvidenceRef` 既有定义已允许「只填 `quote_or_summary` + `notes`、不填 `url`」，因此 Claude 的分析文本可直接作为证据，无需改 `EvidenceRef`。
- `confidence` / `quality_status` 在 profile、tag、claim 上均必填。
- 「仅模型知识的论断不得标 high」是软约束，写在指令模板里，不在 schema 强制（保持 schema 简单、确定）。

## 6. 跨产物契约校验

新增 `validate_import_document(doc)`，沿用 `ContractViolation(ValueError)` 风格。除 Pydantic 字段校验外，检查：

- `profile.game_id` 必须等于 `candidate.id`。
  - 错误消息：`profile.game_id must match candidate.id`
- 每条 `claim` 的 `evidence` 非空、`confidence` / `quality_status` 存在（由 schema 保证，服务层再断言以产生清晰错误）。
- `candidate.source_refs` 非空、`candidate.selection_reason` 非空（由 schema 保证）。
- `claims` 可为空列表（0 条合法）。

不在此步强制：claim 的 subject 必须等于游戏标题（保持灵活，subject 可以是机制等概念）。

## 7. Neo4j 图模型

一个游戏导入后展开为：

```text
(:Game {
   id, title, short_description, selection_reason,
   one_sentence_summary, core_loop, progression_model,
   failure_model, content_structure,
   confidence, quality_status,
   source_refs_json,        # list[EvidenceRef] 序列化为 JSON 字符串
   evidence_json            # profile 级 evidence 序列化为 JSON 字符串
})

(:Game)-[:HAS_MECHANIC]->(:Mechanic {name})
(:Game)-[:TAKES_ACTION]->(:PlayerAction {name})
(:Game)-[:MAKES_DECISION]->(:PlayerDecision {name})
(:Game)-[:DELIVERS_EXPERIENCE]->(:Experience {name})
(:Game)-[:CONSTRAINED_BY]->(:ProductionConstraint {name})
(:Game)-[:USES_INNOVATION]->(:InnovationPattern {name})
(:Game)-[:REUSABLE_PATTERN]->(:ReferencePattern {name})
(:Game)-[:NON_REPLICABLE_RISK]->(:Risk {name})
(:Game)-[:TAGGED {confidence, quality_status, evidence_json}]->(:ReferenceTag {name})

# 每条 DesignClaim → 一条带证据的边
(:Game)-[:CLAIM {
   claim_id, relation, explanation,
   evidence_json, confidence, quality_status
}]->(:Concept {name})
# source_node = 该游戏；target_node = claim.object，按 name MERGE 为 Concept
```

要点：

- Neo4j 属性不能存嵌套对象，`list[EvidenceRef]` 一律序列化为 JSON 字符串（`*_json` 属性）；读回时反序列化并用 `EvidenceRef` 校验。
- 概念类节点（Mechanic、Experience、ReferenceTag、Concept 等）按 `name` 用 `MERGE` 去重，使多个游戏共享同一节点——这是 6.3 设计知识图谱可遍历的基础。
- claim 的边能连接「游戏 → 概念」乃至「概念 → 概念」式的设计因果，这是 profile 固定字段表达不了、却是下游机会框架 `evidence_path` 要遍历的结构。

### 7.1 幂等导入

- `MERGE (:Game {id})`，再 `SET` 标量属性。
- 重新导入同一游戏前，先删除该 Game 的上述全部出边（`HAS_MECHANIC`、`TAGGED`、`CLAIM` 等），再按新文档重建。
- 这样重复导入结果确定、可重复，符合「确定性优先」。
- 共享概念节点不随单个游戏删除而清理（保留给其他游戏引用）；孤立概念节点的清理不在本版范围。

## 8. 导入服务

`services/import_service.py` 为纯逻辑，不依赖 HTTP，也不直连 driver，便于确定性单元测试。

```text
validate_import_document(raw: dict) -> GameImportDocument
  - Pydantic 校验整个文档
  - 跨产物契约检查（第 6 节）
  - 返回强类型文档对象

build_graph_ops(doc: GameImportDocument) -> list[GraphOp]
  - 把文档翻译为一组「图写入操作」描述（节点 / 边 / 属性 / MERGE key）
  - 只描述、不执行 —— 可脱离数据库断言
```

`GraphOp` 是一个简单的数据类/Pydantic 模型，描述一次 MERGE 或边写入。这样 `test_import_service.py` 可在无数据库环境下断言「文档翻译成了正确的图操作」。

`graph/game_repository.py`：

```text
class GameRepository:
    upsert_game(doc) -> ImportSummary   # 在一个事务里：先清旧出边，再执行 build_graph_ops
    get_game(game_id) -> GameReadModel | None  # 读回 game + 标签 + 论断，反序列化 *_json
```

`graph/connection.py`：从环境变量 `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` 构造官方 `neo4j` driver；提供单例工厂与关闭钩子。

## 9. API

`app/main.py` 装配 FastAPI app；`api/routes_import.py` 定义端点。

```text
POST /import/game
  body: GameImportDocument JSON
  200 -> ImportSummary {
           game_id, mechanics_written, tags_written, claims_written,
           experiences_written, concepts_written
         }
  422 -> Pydantic ValidationError（字段缺失 / 类型 / 枚举非法 / 列表为空）
  409 -> ContractViolation（schema 合法但跨产物规则失败），消息明确

GET /games/{id}
  200 -> GameReadModel（档案 + 标签 + 论断，供肉眼核对）
  404 -> 不存在
```

错误处理沿用 fixture 契约文档第 9 节两类：

- Pydantic `ValidationError` → FastAPI 自动 422。
- `ContractViolation` → 注册 exception handler 映射为 409，消息原样透出。

## 10. Claude 生成契约（手动操作核心产物）

`docs/superpowers/import-guide/game-import-prompt.md` 包含三部分：

### 10.1 指令模板（可直接粘贴）

要点（写给 Claude 的硬规则）：

- 角色：游戏设计标注员，对给定游戏产出符合 `GameImportDocument` 的 JSON。
- `candidate` 只写入库理由与来源，**不得**含设计判断或机制推断。
- `profile` 必须填满 18 字段；列表字段不留空。
- `claims` 可选；只为「非显而易见、可跨概念复用」的洞见写，subject-relation-object 三元组要能落成图的边。
- 仅凭模型知识的论断，`confidence` **不得标 high**。
- 区分可观察事实与解释性判断；暴露不确定性而非隐藏。
- 不得对游戏「好不好玩 / 会不会成功」下断言。
- 输出必须是单个合法 JSON，无多余解释文本。

### 10.2 JSON 骨架

带字段注释的空模板，列出 `candidate` / `profile` / `claims` 全部字段与枚举取值（`confidence`: low/medium/high；`quality_status`: draft/reviewed/weak_evidence/conflicting）。

### 10.3 真实样例

`backend/app/fixtures/games/balatro.json`：一个填好的 Balatro 导入文档，可用作回归测试输入，也供用户照改。

用户的实际流程：

```text
挑游戏 -> 把游戏名 + 指令模板交给 Claude -> Claude 产出 JSON
       -> 扫一眼 -> POST /import/game -> GET /games/{id} 核对
```

## 11. 测试策略

沿用「确定性优先」：单元测试不依赖真实数据库。

```text
test_game_import_document.py
  - 有效 balatro.json 能实例化 GameImportDocument
  - 枚举非法值被拒
  - profile 列表字段为空被拒
  - claims 缺省 = [] 合法（0 条可导入）
  - profile.game_id != candidate.id 触发 ContractViolation

test_import_service.py
  - build_graph_ops 产出预期节点/边/属性
  - reference_value_tags 边带 confidence/quality/evidence_json
  - claim 翻译为 CLAIM 边，evidence 序列化正确
  - 0 条 claim 时不产出 CLAIM 边，其余照常
  - 同游戏重导入产生「先删后建」语义（断言操作序列含清旧出边）

test_import_api.py
  - FastAPI TestClient，repository 用 fake/mock
  - 200 返回 ImportSummary 计数正确
  - 422 字段错误
  - 409 ContractViolation 消息
  - GET 命中 / 404

test_game_repository_integration.py
  - @pytest.mark.integration，需真实 Neo4j 才跑，默认跳过
  - 导入 balatro.json 后用 Cypher 验证 Game/Mechanic/Concept/CLAIM 边存在
  - 重导入后无重复节点、出边数稳定（幂等）
```

现有 `test_fixture_pipeline.py`、`test_artifact_contracts.py`、`test_project_structure.py` 不变。`pyproject.toml` 注册 `integration` marker。

## 12. 本地运行

- `backend/docker-compose.yml` 起 Neo4j（默认账号密码、数据卷、暴露 7474/7687）。
- 后端读 `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD`；提供 `.env.example`。
- 启动：`docker compose up -d neo4j` → `uvicorn app.main:app --reload`。
- 不引入 PostgreSQL、不引入前端。

## 13. 依赖

`pyproject.toml` 新增：

- 运行时：`fastapi`、`uvicorn[standard]`、`neo4j`
- 开发/测试：`httpx`（FastAPI TestClient 需要）

保留现有 `pydantic>=2.7,<3`、`pytest>=8.2,<9`。

## 14. 成功标准

这一步成功，如果：

- Claude 能照指令模板对任意挑选的游戏产出合法 `GameImportDocument` JSON。
- `POST /import/game` 能校验文档并把游戏落成可遍历的 Neo4j 图。
- profile 的机制/体验/标签成为多游戏共享的概念节点。
- DesignClaim 成为带证据/置信度/质量状态的图边；0 条也能正常导入。
- 重复导入同一游戏结果幂等。
- 单元测试无需真实数据库即可跑；真实图行为由独立 integration 测试覆盖。
- 现有 fixture pipeline 及其测试不受影响。

这一步失败，如果：

- 导入端点把仅模型知识的论断当作 high 置信度落库。
- 嵌套证据对象丢失或无法读回。
- 重复导入产生重复节点/边。
- 图退化为「游戏 ↔ 标签」的标签库，没有 claim 边承载因果。
- 单元测试被迫依赖真实 Neo4j 才能跑。

## 15. 后续扩展方向

- 6.3 图谱查询 API：基于本版写入的图，提供约束 → 游戏/机制/模式的遍历与证据路径。
- 把「仅模型知识 confidence 不得 high」从软约束升级为可选的导入期校验开关。
- 孤立概念节点清理 / 概念别名归一。
- 用真实 LLM adapter 替代手动生成，但输出仍须通过 `GameImportDocument` schema。
- 前端工作台读取 `GET /games/{id}` 展示档案与图。
