# 后端 Fixture 契约设计 Spec

## 1. 目的

本文档定义独立游戏创意图谱系统的第一块可实现后端边界：基于 Pydantic schema 和确定性 fixture pipeline，验证核心系统产物能以稳定契约串成一条端到端流程。

这一步不搭完整前后端，不接入 FastAPI route，不连接 Neo4j，不调用真实 LLM。它的目标是先证明产品设计中最关键的约束可以被代码表达、被 fixture 验证、被测试守住。

第一条 fixture 流程覆盖：

```text
种子游戏
-> 设计论断
-> 图谱关系
-> 开发者画像
-> 机会框架
-> 概念卡
-> 原型验证简报
```

## 2. 范围

### 范围内

- 建立 `backend/` 目录作为后端代码根目录。
- 使用 Pydantic v2 定义第一批核心产物 schema。
- 使用一条 `golden_flow.json` fixture 表达完整样例流程。
- 实现一个纯内存、确定性的 fixture pipeline。
- 用 pytest 验证 schema、引用完整性和跨产物业务规则。
- 验证概念生成必须位于机会框架下游。
- 验证证据、置信度和质量状态能从设计论断传递到下游。
- 验证硬性约束和禁止方向能阻断不兼容概念。

### 范围外

- FastAPI endpoint。
- Neo4j 连接、Cypher 查询或 Docker Compose。
- 真实 LLM provider、prompt 模板或 streaming。
- 前端工作台。
- 多用户、权限、任务历史或持久化任务队列。
- 完整游戏设计档案字段全集。
- 完整概念评估模块。

## 3. 设计原则

### 3.1 先契约，后基础设施

系统产物和跨产物规则应先以 Pydantic model、fixture 和测试固定下来。API、数据库和 LLM adapter 后续都围绕这些契约接入。

### 3.2 Fixture 不是假装智能

第一版 fixture pipeline 不负责生成聪明点子。概念卡和原型验证简报可以来自手写 fixture。pipeline 的责任是验证这些产物是否满足系统规则。

### 3.3 确定性优先

所有测试必须可重复。第一版不允许随机生成、不允许实时网络请求、不允许依赖外部服务。

### 3.4 保持后续可替换

后续的 Neo4j repository、LLM concept generator 和 FastAPI route 可以替换 fixture pipeline 的内部实现，但不应改变核心 schema 和规则语义。

## 4. 推荐目录结构

```text
backend/
  app/
    __init__.py
    schemas/
      __init__.py
      common.py
      artifacts.py
    services/
      __init__.py
      fixture_pipeline.py
    fixtures/
      golden_flow.json
  tests/
    test_artifact_contracts.py
    test_fixture_pipeline.py
```

说明：

- `schemas/` 只定义类型和校验规则，不读取文件、不运行流程。
- `services/fixture_pipeline.py` 只实现纯内存流程和跨产物契约检查。
- `fixtures/golden_flow.json` 存放第一条端到端样例。
- `tests/` 验证 schema 和流程规则。

## 5. 核心类型

### 5.1 共享类型

`common.py` 定义跨产物共享的枚举和小模型。

推荐类型：

- `ConfidenceLevel`: `low`, `medium`, `high`
- `QualityStatus`: `draft`, `reviewed`, `weak_evidence`, `conflicting`
- `ConstraintType`: `hard`, `strong_preference`, `soft_preference`
- `EvidenceRef`: 来源标题、URL 或引用文本、说明

这些字段必须优先保持简单。第一版不需要复杂评分体系。

### 5.2 系统产物

`artifacts.py` 定义 fixture 流需要的最小产物集合。

第一版需要：

- `SeedGame`
- `DesignClaim`
- `GraphRelation`
- `DeveloperProfile`
- `OpportunityFrame`
- `ConceptCard`
- `PrototypeBrief`

暂不实现：

- 完整 `GameDesignProfile`
- 完整 `ConceptEvaluation`

原因是第一条 fixture 流要先验证证据链和机会框架边界，避免被全量字段拖慢。

## 6. 产物契约

### 6.1 SeedGame

表示被选入 fixture 种子库的游戏。

必需字段：

- `id`
- `title`
- `source_refs`
- `short_description`
- `selection_reason`

规则：

- `source_refs` 不得为空。
- `selection_reason` 不得为空。
- 种子游戏本身不得被当作设计知识使用。

### 6.2 DesignClaim

表示关于某个游戏或设计模式的有证据论断。

必需字段：

- `id`
- `subject`
- `relation`
- `object`
- `explanation`
- `evidence`
- `confidence`
- `quality_status`

规则：

- 每条论断必须有至少一个 `EvidenceRef`。
- `confidence` 和 `quality_status` 必须显式存在。
- 低置信度论断可以进入 fixture，但下游必须能看到其降级状态。

### 6.3 GraphRelation

表示从设计论断转换而来的可查询图谱关系。

必需字段：

- `id`
- `source_node`
- `relation`
- `target_node`
- `claim_id`
- `evidence`
- `confidence`
- `quality_status`

规则：

- 每条图谱关系必须引用存在的 `DesignClaim`。
- 关系继承对应论断的证据、置信度和质量状态。
- fixture pipeline 不得凭空创建没有论断来源的关系。

### 6.4 DeveloperProfile

表示开发者能力、约束和偏好。

必需字段：

- `id`
- `team_size`
- `time_budget`
- `programming_ability`
- `art_ability`
- `audio_ability`
- `content_production_ability`
- `liked_references`
- `disliked_references_or_mechanics`
- `desired_player_experiences`
- `constraints`

规则：

- `constraints` 中必须区分 `hard`、`strong_preference` 和 `soft_preference`。
- fixture 中至少包含一个硬性约束，用于测试阻断规则。
- 喜欢的游戏只能表示兴趣，不得被解释为想要复制这些游戏。

### 6.5 OpportunityFrame

表示概念生成前的有边界创意简报。

必需字段：

- `id`
- `developer_profile_id`
- `opportunity_area`
- `source_game_ids`
- `related_mechanics`
- `related_player_experiences`
- `related_constraints`
- `related_innovation_patterns`
- `recommended_transformations`
- `forbidden_directions`
- `evidence_path`
- `fit_reason`
- `risk_reason`

规则：

- 必须引用存在的 `DeveloperProfile`。
- `evidence_path` 必须至少引用一条存在的 `GraphRelation` 或 `DesignClaim`。
- `forbidden_directions` 不得为空。
- 机会框架是概念卡的必要上游。

### 6.6 ConceptCard

表示从机会框架推导出的具体游戏概念。

必需字段：

- `id`
- `opportunity_frame_id`
- `title`
- `one_sentence_concept`
- `core_fantasy`
- `core_loop`
- `main_player_decisions`
- `main_mechanics`
- `reference_sources`
- `difference_from_references`
- `fit_reason`
- `production_risks`
- `design_risks`
- `novelty_reason`
- `suggested_prototype_scope`

规则：

- 必须引用存在的 `OpportunityFrame`。
- 不得包含机会框架列出的禁止方向。
- 必须说明参考来源和与参考作品的差异。
- 不得声称概念一定好玩或商业成功。

### 6.7 PrototypeBrief

表示围绕概念最大风险的最小测试说明。

必需字段：

- `id`
- `concept_card_id`
- `largest_risk_hypothesis`
- `minimum_prototype_scope`
- `target_playtest_duration`
- `success_signals`
- `failure_signals`
- `do_not_build_yet`

规则：

- 必须引用存在的 `ConceptCard`。
- `largest_risk_hypothesis` 必须具体，不能写成“验证是否好玩”。
- `success_signals` 和 `failure_signals` 都不得为空。
- `do_not_build_yet` 必须明确排除第一轮不需要制作的内容。

## 7. Fixture 数据设计

第一版使用单文件 fixture：

```text
backend/app/fixtures/golden_flow.json
```

推荐结构：

```json
{
  "seed_games": [],
  "design_claims": [],
  "developer_profile": {},
  "opportunity_frame": {},
  "concept_cards": [],
  "prototype_brief": {}
}
```

第一条 fixture 建议沿用产品设计文档中的示例方向：

- 开发者画像：solo、程序能力强、美术能力弱、三个月原型、不想做在线多人或长篇叙事。
- 参考游戏：`Balatro`、`Into the Breach`、`Baba Is You`。
- 机会区域：低美术成本、短局、高重玩性、系统深度、符号化或棋盘式呈现。
- 概念卡：类似 `Ruleforge Tactics` 的规则编辑短局战术概念。
- 原型验证：测试玩家能否理解并享受改变战场规则。

Fixture 中应有意包含：

- 至少一条高置信度论断。
- 至少一条低置信度或弱证据论断。
- 至少一个硬性禁止方向，例如在线多人。
- 至少一个概念卡，用于验证正常通过。
- 至少一个负向测试用例在测试文件中构造，而不是放入 golden fixture。

## 8. Pipeline 设计

### 8.1 输入和输出

输入：

- `golden_flow.json`

输出：

- `FixturePipelineResult`

推荐结果对象包含：

- `seed_games`
- `design_claims`
- `graph_relations`
- `developer_profile`
- `opportunity_frame`
- `concept_cards`
- `prototype_brief`

### 8.2 流程

```text
load_fixture
-> validate_seed_games
-> validate_design_claims
-> build_graph_relations_from_claims
-> validate_developer_profile
-> validate_opportunity_frame
-> validate_concept_cards
-> validate_prototype_brief
-> return FixturePipelineResult
```

### 8.3 图谱关系构造

第一版不实现真实图数据库。`build_graph_relations_from_claims` 只把 `DesignClaim` 转换为 `GraphRelation`。

转换规则：

- `source_node = claim.subject`
- `relation = claim.relation`
- `target_node = claim.object`
- `claim_id = claim.id`
- `evidence = claim.evidence`
- `confidence = claim.confidence`
- `quality_status = claim.quality_status`

这样可以先验证证据和质量状态的传递，不提前设计 Neo4j schema。

### 8.4 概念卡处理

第一版不做 LLM 生成。`validate_concept_cards` 从 fixture 中读取手写概念卡，并验证：

- `opportunity_frame_id` 存在。
- 概念卡没有违反 `forbidden_directions`。
- 概念卡包含参考来源和差异说明。
- 概念卡没有成功承诺。

## 9. 错误处理

第一版只需要两类错误：

### 9.1 Pydantic ValidationError

用于字段缺失、类型错误、枚举非法、列表为空等 schema 层问题。

### 9.2 ContractViolation

用于 schema 合法但跨产物规则失败的情况。

推荐定义：

```python
class ContractViolation(ValueError):
    pass
```

必须覆盖的错误消息：

- `GraphRelation must reference an existing design claim`
- `OpportunityFrame must include a valid evidence path`
- `ConceptCard must reference an existing opportunity frame`
- `ConceptCard must not include forbidden directions`
- `PrototypeBrief must reference an existing concept card`
- `PrototypeBrief must define observable success and failure signals`

错误消息不需要复杂本地化，但必须足够清楚，方便测试和调试。

## 10. 测试策略

### 10.1 Schema 契约测试

文件：

```text
backend/tests/test_artifact_contracts.py
```

覆盖：

- 有效 fixture 能实例化所有核心 Pydantic model。
- 枚举字段拒绝非法值。
- 必填证据字段不能为空。
- `ConceptCard` 必须有 `opportunity_frame_id`。
- `PrototypeBrief` 必须有成功和失败信号。

### 10.2 Fixture Pipeline 测试

文件：

```text
backend/tests/test_fixture_pipeline.py
```

覆盖：

- `golden_flow.json` 可以跑完整流程。
- pipeline 返回所有预期产物。
- 每条 `GraphRelation` 可追溯到 `DesignClaim`。
- `OpportunityFrame` 的证据路径可追溯。
- 每张 `ConceptCard` 映射回 `OpportunityFrame`。
- 禁止方向会阻断不兼容概念。
- `PrototypeBrief` 引用存在的概念卡。

### 10.3 负向测试

负向测试应在测试里复制并修改 fixture 数据，避免污染 golden fixture。

必须包含：

- 删除 concept card 的 `opportunity_frame_id`，应失败。
- 让 concept card 包含 forbidden direction，应该失败。
- 让 opportunity frame 引用不存在的 claim 或 relation，应该失败。
- 让 prototype brief 引用不存在的 concept card，应该失败。

## 11. 成功标准

这一步成功，如果：

- `backend/` 中有清晰的 Pydantic 产物模型。
- 一条 `golden_flow.json` 可以通过确定性 pipeline 跑通。
- pytest 能证明核心跨产物规则成立。
- 证据、置信度和质量状态不会在图谱关系中丢失。
- 概念卡不能绕过机会框架。
- 禁止方向能阻断不兼容概念。
- 原型验证简报具体到可执行测试，而不是泛泛建议。

这一步失败，如果：

- fixture pipeline 开始模拟真实 LLM 推理。
- schema 与产品设计中的系统产物脱节。
- 跨产物引用只靠字符串存在，但没有测试验证完整性。
- 测试只验证字段存在，不验证业务规则。
- 第一版提前引入 Neo4j、FastAPI 或多 provider adapter，导致地基变重。

## 12. 后续扩展方向

完成本 spec 后，后续可以分阶段扩展：

1. 加入 FastAPI route，让外部可以读取 fixture pipeline 结果。
2. 加入 Neo4j repository，把 `GraphRelation` 映射到真实图数据库。
3. 加入 LLM adapter，用真实模型替代手写概念卡，但输出仍必须通过 `ConceptCard` schema。
4. 加入前端工作台，读取后端产物并展示机会框架、概念卡和原型验证简报。

每一步都应保持同一个核心原则：先通过类型化产物和测试守住边界，再接入更复杂的基础设施。

