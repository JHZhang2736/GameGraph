# 6.7 概念生成模块设计 Spec

## 1. 目的

把**单个 `OpportunityFrame`（6.6 产物）**在其**允许的设计空间内**具象化成 **3 张有实质差异、可被评估的 `ConceptCard`**，作为 6.8 概念评估模块的输入。

6.7 是整份系统设计里「先有证据再生成」铁律之后的**第一个纯创造性步骤**：6.6 已把支撑某机会的来源游戏、机制、体验、约束、创新模式、允许变形与禁止方向**组装成有边界的创意简报**；6.7 只在这个界内填充具体概念，不再扩张证据边界。

本模块在 6.6（机会框架）下游、6.8（概念评估）上游。

## 2. 核心模型：frame → 3 张概念卡

```
6.6: 单个被选中 OpportunityArea → 一个 OpportunityFrame（自包含创意简报）
                                      │  用户在前端把这个 frame 喂给 6.7
                                      ▼
6.7: 1 个 OpportunityFrame → 固定 3 张 ConceptCard（一次 LLM 调用，彼此有实质差异）
```

**粒度锁定：1 个 `OpportunityFrame` → 恒 3 张 `ConceptCard`。**

- 一次 tool-call 生成 3 张，让 LLM 在同一上下文里全局权衡、主动刷开三者差异（prompt 要求三张在核心玩法/核心幻想上各不相同，避免同一想法的改写）。
- 数量本期写死为 3（不引入可配 `count`，YAGNI；小种子库下 3 张已够对比）。

## 3. 设计哲学边界：薄确定性装配 + LLM 生成层

与 6.5/6.6 同源的两层架构，但**确定性层极薄**——因为 `OpportunityFrame` 是 6.6 产出的自包含简报，6.7 **不需要再查图谱、不需要 repository、不需要 profile**。

| 层 | 在 6.7 负责 | 为什么由它负责 |
|---|---|---|
| **确定性装配**（`concept_service.py`，不碰 LLM） | ① 把 frame 整体喂给 LLM；② 给 LLM 返回的每张草稿确定性赋 `id = concept\|{frame.id}\|{n}`、`opportunity_frame_id = frame.id`（**不信任 LLM 自填这两个字段**） | 可追溯：每张卡确定性回指其 frame，便于 6.8 与人审 |
| **LLM 生成层**（`concept_llm.py`，只生成创意字段） | 一次 tool-call 生成 3 张概念草稿的全部创意字段（标题、一句话、核心幻想、核心循环、玩家决策、机制、参考来源、与参考差异、fit、制作/设计风险、新颖理由、原型范围） | 概念生成是纯创造性综合，需自然语言与设计常识 |

**不可逾越的边界（仅由 system prompt 约束，后端不做语义后校验）：**

- `reference_sources` 只能来自 `frame.source_game_ids`。
- `main_mechanics` 取自 `frame.related_mechanics` / `frame.recommended_transformations`。
- 不得生成踩 `frame.forbidden_directions` 的概念。
- 不得引入 frame 证据之外的机制或参考。

> **为什么只靠 prompt、不后校验**：语义边界（「这个概念是否踩了禁止方向」）难以确定性判定，字面匹配易误伤合理概念。本期信任 prompt 约束，把人审留给前端展示与 6.8 评估。后端唯一的硬闸是 schema：若 LLM 草稿连 `ConceptCard` 的字段 `min_length=1` 都不满足 → 解析失败 → 502。

## 4. 数据流

```
{ frame: OpportunityFrame }
   │
   ▼ [路由] app/api/routes_concept.py
     llm_client is None → 503（强依赖 LLM，不降级；见 §7）
   │
   ▼ [LLM 生成层] app/services/concept_llm.py
     generate(frame) 一次 tool-call → ConceptGenerationBatch { concepts: [draft × 3] }
     （HTTP 错误 / 无 tool_call / 产物非法 → raise ValueError）
   │
   ▼ [确定性装配] app/services/concept_service.py
     逐张: ConceptDraft + { id: concept|{frame.id}|{n}, opportunity_frame_id: frame.id } → ConceptCard
   │
   ▼ list[ConceptCard]   （恒 3 张）
```

LLM **只回填创意字段**；`id` / `opportunity_frame_id` 全部由确定性装配产出。

## 5. 数据结构 (schema)

`ConceptCard` 已存在于 `app/schemas/artifacts.py`，字段名 = 前端 `lib/types/index.ts` 形状，**不改**。本期**无 schema 改动**。

```python
class ConceptCard(StrictBaseModel):
    id: str                               # 确定性: concept|{frame.id}|{n}
    opportunity_frame_id: str             # 确定性: frame.id
    title: str
    one_sentence_concept: str
    core_fantasy: str
    core_loop: str
    main_player_decisions: list[NonEmptyStr]
    main_mechanics: list[NonEmptyStr]
    reference_sources: list[NonEmptyStr]  # LLM: 只能来自 frame.source_game_ids
    difference_from_references: str
    fit_reason: str
    production_risks: list[NonEmptyStr]
    design_risks: list[NonEmptyStr]
    novelty_reason: str
    suggested_prototype_scope: str
```

LLM 生成层新增两个内部模型（在 `concept_llm.py`，不进 `artifacts.py`）：

```python
class ConceptDraft(StrictBaseModel):
    # extra="ignore"：LLM 可能多返字段，宽容忽略（与 opportunity_llm/opportunity_frame_llm 一致）。
    # = ConceptCard 去掉 id / opportunity_frame_id 的全部创意字段，均必填（tool schema 标 required，逼 LLM 补全）。
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1)
    one_sentence_concept: str = Field(min_length=1)
    core_fantasy: str = Field(min_length=1)
    core_loop: str = Field(min_length=1)
    main_player_decisions: list[NonEmptyStr] = Field(min_length=1)
    main_mechanics: list[NonEmptyStr] = Field(min_length=1)
    reference_sources: list[NonEmptyStr] = Field(min_length=1)
    difference_from_references: str = Field(min_length=1)
    fit_reason: str = Field(min_length=1)
    production_risks: list[NonEmptyStr] = Field(min_length=1)
    design_risks: list[NonEmptyStr] = Field(min_length=1)
    novelty_reason: str = Field(min_length=1)
    suggested_prototype_scope: str = Field(min_length=1)


class ConceptGenerationBatch(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")
    concepts: list[ConceptDraft] = Field(default_factory=list)
```

`id` 生成：`concept|{frame.id}|{n}`（n 为 1 起的序号；`frame.id` 已唯一含 area 全量标识）。

## 6. 确定性装配

`app/services/concept_service.py`（编排，无图谱、无 repository、无 profile 入参）：

```python
def generate_concepts(
    frame: OpportunityFrame,
    llm_client: SupportsConceptGeneration,   # 非 None（None 由路由前置拦成 503）
) -> list[ConceptCard]:
    batch = llm_client.generate(frame)        # 可能 raise ValueError → 路由映射 502
    return [
        ConceptCard(
            id=f"concept|{frame.id}|{i}",
            opportunity_frame_id=frame.id,
            **draft.model_dump(),
        )
        for i, draft in enumerate(batch.concepts, start=1)
    ]
```

> **批量校验，非法即 502（本期不做 per-card 容错）**：`ConceptCard(**draft.model_dump())` 若某张草稿字段不满足 `min_length=1` 会抛 `ValidationError`，整批 502。单张非法不拖垮其余的 per-card 韧性留作后续（见 §12）。

## 7. LLM 生成层 + 错误语义

`app/services/concept_llm.py`，仿 `opportunity_frame_llm.py`：OpenAI 兼容 tool-calling、env 配置（复用 `LLM_BASE_URL/LLM_API_KEY/LLM_MODEL/LLM_TIMEOUT` 与 `LlmSettings`）、可选依赖（未配置返回 `None`）、一次 tool-call。

**输入** = 整个 `OpportunityFrame`（opportunity_area / source_game_ids / related_* / recommended_transformations / forbidden_directions / evidence_path / fit_reason / risk_reason 全部进 prompt）。

**输出** = `ConceptGenerationBatch { concepts: [draft × 3] }`。

**System prompt 要点：**
- 在 frame 划定的设计空间内生成**恰好 3 个**具体概念。
- 三个概念必须在**核心玩法 / 核心幻想**上各不相同，不得是同一想法的改写。
- `reference_sources` 只能引用 `frame.source_game_ids`；`main_mechanics` 取自 `related_mechanics` / `recommended_transformations`。
- 不得生成踩 `forbidden_directions` 的概念；不得引入 frame 证据之外的机制或参考。
- 每张卡都要给制作风险与设计风险；证据弱时在 `novelty_reason` / `design_risks` 体现适当不确定性，不得宣称概念一定好玩或成功。

**错误语义（强依赖 LLM，不降级）——按 6.7「最依赖创造性」的定位，无 LLM 时没有可回退的实质内容：**

| 情况 | 行为 |
|---|---|
| 未配置 LLM（`get_concept_llm_client()` 返回 `None`） | 路由 **503**（与 6.5/6.6 的可选降级**有意不同**：概念生成无 LLM 即不可用） |
| LLM HTTP 错误 / 无 tool_call / 产物非法 | `concept_llm` raise `ValueError` → 路由捕获 → **502**（上游 LLM 失败，诚实暴露） |
| 请求体缺 `frame` 或字段非法 | FastAPI **422** |

## 8. API

新建 `app/api/routes_concept.py`（独立 router，概念域与 opportunity 域分开）：

```
POST /concept/generate
  body:  { frame: OpportunityFrame }     # 薄 Pydantic 包装 ConceptGenerateRequest(StrictBaseModel)
  deps:  get_concept_llm() → ConceptLlmClient | None（测试用 dependency_overrides 覆盖）
  resp:  list[ConceptCard]               # 恒 3 张
```

路由薄、委托 service。错误映射在路由层（保持 service 纯净、不耦合 FastAPI）：

```python
@router.post("/concept/generate", response_model=list[ConceptCard])
def generate_endpoint(
    request: ConceptGenerateRequest,
    llm_client: ConceptLlmClient | None = Depends(get_concept_llm),
) -> list[ConceptCard]:
    if llm_client is None:
        raise HTTPException(status_code=503, detail="未配置 LLM，概念生成不可用。")
    try:
        return generate_concepts(request.frame, llm_client)
    except ValueError as error:
        raise HTTPException(status_code=502, detail=f"LLM 概念生成失败：{error}") from error
```

在 `app/main.py` 用 `app.include_router(concept_router)` 注册。

## 9. 文件清单

| 文件 | 职责 | 动作 |
|---|---|---|
| `app/services/concept_llm.py` | `ConceptDraft` / `ConceptGenerationBatch` / `ConceptLlmClient` / `get_concept_llm_client`（仿 `opportunity_frame_llm`） | 新 |
| `app/services/concept_service.py` | `generate_concepts(frame, llm_client)` 编排 + id 装配 | 新 |
| `app/api/routes_concept.py` | `ConceptGenerateRequest` + `POST /concept/generate` + provider + 503/502 映射 | 新 |
| `app/main.py` | 注册 concept router | 改 |
| `tests/test_concept_service.py` | 装配 / id 格式 / opportunity_frame_id / 批量数量 单测（stub llm） | 新 |
| `tests/test_concept_llm.py` | `MockTransport` 行为：发请求 URL/body、解析、无 tool_call、HTTP 错误、未配置返回 None | 新 |
| `tests/test_concept_api.py` | 契约往返 + 422 + 503（无 LLM）+ 502（LLM 抛错）端到端（stub） | 新 |

（schema 不改——`ConceptCard` 已在 `artifacts.py`。）

## 10. 测试（对应规格 §6.7 验收）

| 规格验收 | 测试方式 |
|---|---|
| 每张概念卡映射回一个机会框架 | 断言 `opportunity_frame_id == frame.id`；`id` 前缀 `concept\|{frame.id}\|` 且序号递增 |
| 每张卡说明参考来源与差异 | schema 必填 `reference_sources` / `difference_from_references`；stub 返回即断言透传 |
| 每张卡含制作风险与设计风险 | schema 必填 `production_risks` / `design_risks` |
| 概念避开禁止方向 / 三张有实质差异 / 弱证据带不确定性 | LLM 行为测试：stub 断言 prompt 含 `forbidden_directions` 与「3 张需差异」「弱证据带不确定性」指令（非确定性行为不强测生成内容，与 `test_opportunity_llm` 同策略） |
| 无 LLM | API 测试断言 503 |
| LLM 失败 | stub 抛错 → API 断言 502；`concept_llm` HTTP 错误/无 tool_call → 断言 `ValueError` |

- **service**：stub LLM 客户端单测（装配 / id / 数量 / 502 路径）。
- **LLM 层**：`httpx.MockTransport`（仿 `test_opportunity_frame_llm`）。
- **API**：`TestClient` + `dependency_overrides` 覆盖 `get_concept_llm`。

## 11. 范围

### 范围内
- 上述新增/改动文件。
- 1 个 frame → 恒 3 张 ConceptCard（一次 LLM 调用）。
- 确定性 id 装配 + LLM 生成层 + 503/502/422 错误语义。

### 范围外（留后续）
- **6.8 概念评估**（评分 / 稳妥-平衡-挑战分类）——本期不做，前端 concepts 页的评估区块仍是 mock。
- 可配置概念数量（`count`）。
- per-card 容错（单张非法不拖垮整批，当前整批 502）。
- 后端语义后校验（reference_sources ⊆ source_game_ids、forbidden 命中检测）——本期仅 prompt 约束。
- 前端接 API（沿用 6.6 做法：本后端分支不动 `frontend/`，见 §13 交接）。
- 概念的服务端持久化（本期前端持有 frame 直传，无状态）。

## 12. 已知局限

- **强依赖 LLM**：无 LLM 时本步整条创意流程在前端会停在 6.7（503）。这是有意取舍——概念生成无创造性综合即无意义，不假装产出骨架概念。
- **LLM 行为非确定**：概念内容从「确定性可精确测试」变为「LLM 行为测试」（stub 断言 prompt 与产物形状，不强测生成文本），与 `test_opportunity_llm` / `test_opportunity_frame_llm` 同策略。
- **边界仅 prompt 约束**：LLM 理论上仍可能引用 frame 外参考或软性踩禁止方向；本期信任 prompt + 人审，后端只兜 schema 合法性。
- **整批 502**：3 张里 1 张 schema 非法即整批失败重来；小概率、可重试，per-card 韧性留后续。

## 13. 跨模块共享契约 + 前端交接

- `POST /concept/generate`，body `{ frame: OpportunityFrame }` → `list[ConceptCard]`（恒 3 张）。
- 响应元素字段名对齐 `frontend/lib/types/index.ts` 的 `ConceptCard`，**无字段增减**。
- **前端交接（不在本后端分支改动）**：前端 agent 在 6.7 前端分支自行——
  - 把现有 mock 的 `/concepts` 页改成由选中的 `OpportunityFrame` 驱动，调 `POST /concept/generate` 渲染 3 张卡。
  - 评估区块（分类 / 评分）保持 mock，等 6.8。
  - 503 → 提示「需配置 LLM 才能生成概念」；502 → 提示「概念生成失败，可重试」。
- **本后端 worktree 不触碰任何 `frontend/` 文件**，以免与前端 agent 并发冲突。
