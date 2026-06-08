# 开发者画像 LLM 解析（6.4 增强）设计 Spec

## 1. 目的

把开发者画像模块（6.4）的解析步骤从确定性规则解析升级为 **LLM 抽取 + 规则裁决** 的混合式实现。

现有 `parse_developer_profile_input` 用硬编码触发词匹配自由文本，对真实输入（换说法、任意游戏名、复杂措辞）覆盖差、易误判。本次新增一个后端 `POST /profile/parse` 端点，用 OpenAI 兼容的 LLM（function/tool calling）做字段抽取；前端把本地解析改为调用该端点。

**核心边界不变**：LLM 只负责「模糊抽取」，`is_complete`、缺失字段判定、`promote_draft_to_profile` 仍由确定性代码裁决，避免模型幻觉放行不完整画像。这与开发者画像模块 spec §4.1 / §6.6 一致。

## 2. 范围

### 范围内

- 后端新增 OpenAI 兼容 LLM 客户端：通过环境变量配置 `base_url` / `api_key` / `model`，用 tool calling 抽取画像字段。
- 后端新增 `POST /profile/parse` 端点：薄封装解析服务，返回现有 `ProfileParseResult` 契约。
- 重构现有确定性 parser，抽出共享的「完整度判定」逻辑，供 LLM 路径和规则路径复用（单一事实源）。
- 降级兜底：未配置 LLM 或调用失败/超时时，回退到现有确定性解析，并在 `warnings` 标注。
- 前端 `lib/data.parseDeveloperProfileInput` 从本地解析改为 `fetch` 该端点；fetch 失败时回退本地规则解析。
- 后端 pytest（不联网，用 `httpx.MockTransport` 和依赖注入）+ 前端 Vitest 覆盖核心行为。

### 范围外

- **任何持久化**：画像、机会框架、概念卡、原型简报仍不落库。解析无状态。
- 真实 LLM provider 选型、prompt 精调、流式输出、多轮补问。
- 机会匹配、概念生成、概念评分（6.5/6.6）。
- `POST /profile/confirm`：promote 是纯函数，确认仍留在前端本地。
- 画像版本历史、归属、多用户。
- 后端鉴权、限流、计费。

## 3. 当前上下文

- 后端 `app/services/developer_profile_parser.py` 提供 `parse_developer_profile_input`（确定性）和 `promote_draft_to_profile`（纯函数）。前者内部计算 `missing_fields` / `is_complete`。
- 后端契约 `app/schemas/developer_profile.py`：`ProfileParseInput`、`DeveloperProfileDraft`、`ProfileFieldSource`、`MissingProfileField`、`ProfileParseResult`。
- 后端已有 FastAPI 应用（`app/main.py`）、路由模式（`app/api/routes_import.py` 用 `APIRouter` + `Depends` + 测试 `dependency_overrides`）、配置模式（`Neo4jSettings.from_env()`）、`ContractViolation → 409` 异常处理。`httpx` 已是依赖。
- 前端 `lib/data.parseDeveloperProfileInput` 目前用本地 `lib/profile/parser.ts`，通过 `settle` 模拟延迟。`lib/profile/parser.ts` 镜像后端规则解析。
- **本设计不动** `promote` / `recompute` / 前端工作台页面 / 组件 / 类型。

## 4. 设计原则

### 4.1 LLM 抽取，代码裁决

LLM 输出仅包含「字段值 + 来源 + 约束分级 + warnings」。是否完整、缺哪些阻断字段、能否提升为正式画像，全部由确定性代码决定。工具 schema **不包含** `is_complete` 和 `missing_fields`。

### 4.2 单一完整度事实源

从现有规则 parser 抽出 `finalize_completeness`，LLM 路径和规则兜底路径都调用它。保证两条路径对「什么算完整」判断一致，现有 parser 测试不回归。

### 4.3 显式字段确定性覆盖

`ProfileParseInput` 的 `liked_references` / `disliked_references_or_mechanics` / `expected_project_scale` 若显式提供，在 LLM 输出之后由代码强制覆盖对应字段。保留「显式优先于推断」契约，不依赖模型遵守。

### 4.4 永不因 LLM 故障而 500

未配置、超时、4xx/5xx、tool_call 缺失或 schema 不符——一律回退确定性解析并加 warning。端点对调用方始终返回合法 `ProfileParseResult`（除非连规则解析本身抛 `ValidationError`）。

### 4.5 测试不依赖网络

所有后端测试用依赖注入（fake client 或 None）或 `httpx.MockTransport`，绝不发真实请求。

## 5. 配置

后端新增环境变量，沿用 `from_env()` 模式：

| 变量 | 说明 | 默认 |
|------|------|------|
| `LLM_BASE_URL` | OpenAI 兼容端点根，如 `https://api.openai.com/v1` | 空字符串 |
| `LLM_API_KEY` | 密钥 | 空字符串 |
| `LLM_MODEL` | 模型 id，如 `gpt-4o-mini` | 空字符串 |
| `LLM_TIMEOUT` | 请求超时秒数 | `30` |

`is_configured` 定义为 `base_url`、`api_key`、`model` 三者均非空。任一为空 → 未配置 → 规则兜底。

前端新增（构建期可选）：

| 变量 | 说明 | 默认 |
|------|------|------|
| `NEXT_PUBLIC_API_BASE_URL` | 后端根地址 | `http://localhost:8000` |

两者都会写进各自的 `.env.example`。

## 6. 后端架构

### 6.1 `app/services/profile_llm.py`

确定性配置 + LLM 客户端 + 抽取结果契约。

- `LlmSettings`（frozen dataclass）：字段 `base_url` / `api_key` / `model` / `timeout`；`from_env()`；`is_configured` 属性。
- `ProfileExtraction`（Pydantic `StrictBaseModel`）：LLM tool 返回的原始抽取结构。字段：
  - `team_size` / `time_budget` / `programming_ability` / `art_ability` / `audio_ability` / `content_production_ability`: `str | None`
  - `liked_references` / `disliked_references_or_mechanics` / `desired_player_experiences`: `list[str]`
  - `constraints`: `list[ExtractedConstraint]`，其中 `ExtractedConstraint` = `{ type: ConstraintType, statement: str }`（**无 id**，由代码生成）
  - `field_sources`: `list[ExtractedSource]` = `{ field: str, source_text: str, confidence: ConfidenceLevel }`（**无 source_kind**，由代码填）
  - `warnings`: `list[str]`
- `build_tool_schema() -> dict`：从 `ProfileExtraction` 派生 OpenAI tools 数组（工具名 `emit_developer_profile`，`parameters` = JSON Schema）。
- `ProfileLlmClient`：构造接收 `LlmSettings` 和可选 `httpx.Client`（便于注入 `MockTransport`）。方法 `extract(input: ProfileParseInput) -> ProfileExtraction`：
  - 组 system + user 消息（user 含 raw_text 和显式字段）。
  - POST `{base_url}/chat/completions`，body 含 `model`、`messages`、`tools`、`tool_choice={"type":"function","function":{"name":"emit_developer_profile"}}`。
  - 取第一个 tool_call 的 `function.arguments`，JSON 解析后用 `ProfileExtraction.model_validate` 校验。
  - 任何网络/解析/校验错误抛异常（由上层兜底捕获）。
- `get_llm_client() -> ProfileLlmClient | None`：依赖提供者。`LlmSettings.from_env().is_configured` 为真时返回客户端，否则 `None`。

### 6.2 `app/services/developer_profile_parser.py`（重构）

抽出可复用的完整度判定：

```text
finalize_completeness(values: dict[str, object]) -> tuple[list[MissingProfileField], bool]
```

- 输入：8 个阻断字段的当前值。
- 输出：`missing_fields`（仅阻断字段，空值即缺失，reason 文案沿用现有 `missingProfileField`）+ `is_complete`。
- 现有 `parse_developer_profile_input` 改为调用它，行为不变（现有测试保持绿）。

### 6.3 `app/services/profile_parse_service.py`

编排层，路由唯一入口：

```text
parse_profile(input: ProfileParseInput, client: ProfileLlmClient | None) -> ProfileParseResult
```

- `client is None` → 直接返回 `parse_developer_profile_input(input)`（规则路径），不加额外 warning（未配置属正常）。
- 否则 `try`：
  1. `extraction = client.extract(input)`
  2. 用 extraction 字段构造 draft 字段值；为 constraints 生成 id（`constraint_1`…）；为 sources 填 `source_kind="raw_text"`。
  3. **显式覆盖**：若 input 提供了 `liked_references` / `disliked_references_or_mechanics` / `expected_project_scale`，覆盖对应字段并补一条 `explicit_field` 来源。
  4. `missing_fields, is_complete = finalize_completeness(values)`。
  5. 组装 `DeveloperProfileDraft` + `ProfileParseResult(draft, warnings=extraction.warnings)`。
- `except Exception` → 回退 `parse_developer_profile_input(input)`，并在结果 `warnings` 前插入「LLM 解析失败，已降级为规则解析。」

### 6.4 `app/api/routes_profile.py`

```text
POST /profile/parse
  body: ProfileParseInput
  response_model: ProfileParseResult
  client = Depends(get_llm_client)
  return parse_profile(document, client)
```

`main.py` 挂载该 router。

## 7. 前端架构

### 7.1 `lib/data.parseDeveloperProfileInput`（改）

```text
parseDeveloperProfileInput(input):
  try:
    res = fetch(`${API_BASE}/profile/parse`, POST json=input)
    if !res.ok: throw
    return res.json()  // ProfileParseResult
  catch:
    console.warn(...)
    result = parseLocalDeveloperProfileInput(input)   // 现有本地规则
    return { ...result, warnings: ["后端不可用，已使用本地规则解析。", ...result.warnings] }
```

- `API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"`。
- 保留 `lib/profile/parser.ts` 作为兜底。**页面、组件、类型、queries 不变。**

### 7.2 测试影响

- 现有 `lib/profile/parser.test.ts`（直接测本地 parser）不变。
- 现有 `profile-page.test.tsx`：jsdom 无服务器，`fetch` 抛错 → 走本地兜底 → **行为与现状一致，无需改**（仅 warnings 多一条，不影响断言）。
- 新增 `lib/data` 测试：mock `fetch` 成功返回 → 用后端结果；mock `fetch` 失败 → 本地兜底 + warning。

## 8. 数据流

```text
ProfilePage（不变）
-> lib/data.parseDeveloperProfileInput(input)
-> fetch POST /profile/parse
   -> routes_profile -> parse_profile(input, client)
      -> client.extract（LLM tool calling）       [模糊抽取]
      -> 显式覆盖 + finalize_completeness          [规则裁决]
      -> ProfileParseResult
   失败/未配置 -> parse_developer_profile_input    [规则兜底]
-> 页面渲染 draft / missing / sources（不变）
fetch 失败 -> 前端本地 parser 兜底
```

## 9. 错误处理与降级矩阵

| 情形 | 后端行为 | warnings |
|------|----------|----------|
| 未配置（无 key/url/model） | 规则解析 | 无 |
| LLM 超时 / 网络错 | 规则解析 | 已降级 |
| 4xx/5xx | 规则解析 | 已降级 |
| 无 tool_call / arguments 非法 JSON | 规则解析 | 已降级 |
| extraction schema 不符 | 规则解析 | 已降级 |
| 规则解析自身抛 ValidationError | 抛出（由 FastAPI/异常处理转 4xx/5xx） | — |
| 前端 fetch 失败 | 前端本地规则兜底 | 后端不可用 |

## 10. 测试策略

### 10.1 后端

- `test_profile_llm.py`：用 `httpx.MockTransport` 喂一段含 `emit_developer_profile` tool_call 的样例响应；断言请求体含 `model`/`tools`/`tool_choice`，且 `extract` 返回正确 `ProfileExtraction`；再喂一段无 tool_call 的响应断言抛错。
- `test_profile_parse_service.py`：
  - 注入 fake client（`extract` 返回固定 extraction）→ draft 含 LLM 字段，且 `is_complete` 由 `finalize_completeness` 决定（即使 extraction 谎报也不被采信）。
  - `client=None` → 与 `parse_developer_profile_input` 等价。
  - fake client `extract` 抛错 → 规则兜底 + 含「已降级」warning。
  - 显式字段覆盖 LLM 抽取结果，且来源 `source_kind="explicit_field"`。
- `test_routes_profile.py`：`dependency_overrides[get_llm_client]` 注入 fake client 与 `None`，`TestClient` 调 `POST /profile/parse`，断言 200 + `ProfileParseResult`。
- 现有 `test_developer_profile_parser.py` / `test_developer_profile_contracts.py`：重构后保持全绿。

### 10.2 前端

- `lib/data/parse.test.ts`：mock 全局 `fetch` 返回固定 `ProfileParseResult` → 断言透传；mock `fetch` reject → 断言本地兜底且 warnings 含降级提示。
- 现有 parser / page 测试保持绿。

## 11. 成功标准

成功，如果：

- 配好 `LLM_*` 后，`/profile/parse` 用 LLM 抽取真实自由文本（任意游戏名、换说法都能解析），输出仍是 `ProfileParseResult`。
- `is_complete` / 缺失字段 / promote 行为与纯规则版完全一致——模型不能绕过完整度门禁。
- 未配置或 LLM 故障时端点不报 500，自动规则兜底并标注降级。
- 前端零页面改动即用上后端解析；后端没起时前端本地兜底。
- 后端测试不联网即可全绿；现有测试无回归。

失败，如果：

- LLM 输出被直接当成最终 draft（含 `is_complete`），绕过裁决。
- 未配置/故障导致 500 或前端崩。
- 重构破坏现有 parser 行为。
- 端点落库或越界生成机会/概念（违反范围）。

## 12. 后续扩展方向

1. `POST /profile/confirm` + 画像持久化（单独 spec：存储选型、schema、版本、归属）。
2. prompt 精调、few-shot、置信度阈值与多轮补问（只问阻断缺失字段）。
3. `field_sources` 增加 `user_edited` 来源类型，覆盖前端手动编辑。
4. LLM 抽取接入 6.5 机会匹配的解释链。
