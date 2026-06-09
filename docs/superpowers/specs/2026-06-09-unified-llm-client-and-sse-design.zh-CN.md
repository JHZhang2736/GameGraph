# 统一 LLM Client 与 SSE 心跳保活 — 设计文档

日期：2026-06-09
状态：已确认，待写实现计划

## 背景与问题

后端现有 3 处 LLM 调用，散落在三个 service 文件，且彼此重复：

- `backend/app/services/profile_llm.py`（`ProfileLlmClient.extract`）
- `backend/app/services/opportunity_llm.py`（`OpportunityLlmClient.judge`）
- `backend/app/services/opportunity_frame_llm.py`（`OpportunityFrameLlmClient.synthesize`，已复用 `opportunity_llm` 的部分渲染器与 `LlmSettings`）

三者都是 OpenAI 兼容的 `/chat/completions` + **强制 tool-call** 模式，且各自重复了同一套基建：

- `LlmSettings`（`from_env` / `is_configured`）—— 三处重复（frame 从 opportunity 复用）。
- HTTP POST → `raise_for_status` → 解析 `choices[0].message.tool_calls[0].function.arguments` → `model_validate_json`。
- 错误处理一律 `raise ValueError(...)`。

差异仅在：system prompt、tool 名/schema、user 消息渲染、返回的 pydantic 模型。

**两个目标：**

1. **统一**：抽出一个共享 LLM client，集中重试、日志、统一错误类型、配置，消除三处重复。
2. **保活**：LLM 调用耗时长，前端 HTTP 连接在拿到结果前会超时/主动断开。改用 SSE 心跳保活，让连接在等待期间持续收到字节。

**现状关键事实：**

- 上层 service 消费 seam：`opportunity_service` / `opportunity_frame_service` 已通过 Protocol（`SupportsOpportunityJudgment` / `SupportsFrameSynthesis`）依赖 client；`profile_parse_service` 直接依赖 `ProfileLlmClient`。三者都调用 domain 方法（`.extract` / `.judge` / `.synthesize`）。
- 三个 LLM 端点全是同步 `def`：`POST /profile/parse`、`POST /opportunity/match`、`POST /opportunity/frame`。
- 项目无中央 config 模块，无 tenacity/backoff/structlog 等依赖。
- 测试 seam：domain 测试通过构造函数注入 `httpx.Client(transport=MockTransport(...))` 在 HTTP 层 mock。
- 前端是 Next.js，三个调用集中在 `frontend/lib/data/index.ts` 三个 helper（`parseDeveloperProfileInput` / `matchOpportunities` / `buildOpportunityFrame`），经 Next `/api` rewrite 代理到后端。`parseDeveloperProfileInput` 带本地降级。

## 决策摘要

| 决策点 | 选择 |
|---|---|
| 抽象边界 | 通用 tool-call 方法：单个 `LlmClient.call_tool(...) -> T`，domain service 各自保留 prompt 渲染与 schema |
| 内置能力 | 重试 + 日志 + 统一错误类型 + 配置集中（全要） |
| 重试实现 | 手写指数退避小循环，不引入新依赖 |
| 前端保活方式 | 心跳保活（最小）：`call_tool` 仍同步 `-> T`，在工作线程跑；route 返回 SSE，等待期间发心跳，完成发完整 result |
| 范围 | 一个 spec，两部分：A 统一 client、B SSE 保活；含前端 `lib/data` 改动 |

## Part A — 统一 LLM Client

新增模块 `backend/app/services/llm_client.py`，承载所有横切关注点。

### LlmSettings（单一来源）

迁移现有 `LlmSettings`，删掉三处重复。字段：

- 现有：`base_url` / `api_key` / `model` / `timeout`（从 `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` / `LLM_TIMEOUT` 读）。
- 新增：`max_retries`（默认如 2）、`backoff_base`（默认如 0.5s），从 env 读、带默认值。
- 保留 `from_env()` 与 `is_configured`。

### 异常体系（替代到处 raise 的 ValueError）

- `LlmError(Exception)` —— 基类。
- `LlmRequestError(LlmError)` —— 重试耗尽后的网络/5xx/超时，或不可重试的 4xx；携带状态码（可选）。
- `LlmResponseError(LlmError)` —— 响应结构异常 / 缺 `tool_call` / pydantic 校验失败。

### LlmClient

核心单方法：

```python
def call_tool(
    self, *,
    system_prompt: str,
    user_message: str,
    tool_name: str,
    response_model: type[T],
    tool_description: str = "",
) -> T
```

内部职责：

1. 拼 payload：`messages`（system + user）、`tools`（由 `response_model.model_json_schema()` 生成的 function schema）、强制 `tool_choice`（`{"type":"function","function":{"name":tool_name}}`）。
2. **带指数退避重试循环**地 POST：仅对网络错误 / 超时 / 5xx 重试，至多 `max_retries` 次；4xx 立即抛 `LlmRequestError`。
3. **日志**：每次调用记录 model、tool_name、耗时、重试次数、成败；错误时记录状态码与响应片段。用标准 `logging`，不引入新依赖。
4. 解析 `choices[0].message.tool_calls[0].function.arguments`；结构异常或缺 tool_call → `LlmResponseError`。
5. `response_model.model_validate_json(...)`；校验失败 → `LlmResponseError`。

构造函数：`LlmClient(settings: LlmSettings, http_client: httpx.Client | None = None, sleep: Callable[[float], None] = time.sleep)`。`sleep` 可注入，测试时传 no-op 验证退避而不真等。

工厂：`get_llm_client() -> LlmClient | None`，未配置返 `None`。

### Domain 模块迁移（最低 churn）

三个 `*_llm.py` 保留：`SYSTEM_PROMPT`、`TOOL_NAME`、schema 模型、prompt 渲染 helper。
其 client 类（`ProfileLlmClient` 等）**保留**（保住 Protocol seam 与方法签名 `.extract`/`.judge`/`.synthesize`），但内部改为：

- 构造从 `(settings, http_client)` 改为持有一个 `LlmClient`。
- 方法体改为：渲染 prompt → `self._llm.call_tool(system_prompt=..., user_message=..., tool_name=..., response_model=...)`。

`get_*_client()` 工厂保留（route 仍调用），内部用 `get_llm_client()` 构造共享 `LlmClient` 再包成 domain client。

## Part B — SSE 心跳保活

覆盖三个 LLM 端点：`/profile/parse`、`/opportunity/match`、`/opportunity/frame`。

### 共享 helper

```python
async def sse_with_heartbeat(
    work: Callable[[], T],          # 阻塞的 LLM 调用，丢进线程跑
    to_event: Callable[[T], str],   # 成功结果 -> JSON 字符串
    *, interval: float = 10.0,
) -> AsyncIterator[bytes]
```

机制：

- `task = asyncio.create_task(asyncio.to_thread(work))`。
- 循环 `asyncio.wait({task}, timeout=interval)`：超时则 yield 一条 `heartbeat` 事件；task 完成则 yield `result` 事件 + 完整 JSON；`work` 抛 `LlmError` 则 yield `error` 事件 + `{"detail": ...}`。

放置位置：`backend/app/api/`（如 `sse.py`）或复用现有 api 工具模块。

### SSE 事件协议

- `event: heartbeat\ndata: {}\n\n` —— 每 `interval` 秒（默认 10s，可配），纯保活。
- `event: result\ndata: <完整结果 JSON>\n\n` —— 成功；内容即原 `response_model` 序列化结果。
- `event: error\ndata: {"detail": "..."}\n\n` —— 失败；把 `LlmError` 映射成消息。

### Route 改动

三个 route：

- 改为 `async def`，返回 `StreamingResponse(sse_with_heartbeat(...), media_type="text/event-stream")`。
- 响应头设 `X-Accel-Buffering: no`（防代理/Nginx 缓冲）。
- 去掉 `response_model=`（现在是流），但保留 pydantic 模型用于序列化 result 事件。
- 阻塞的 service 调用（含 LLM）包成 `work`，未配置 LLM 的降级路径维持原语义（仍走非 LLM 分支，照样可通过 result 事件返回）。

### 前端改动（lib/data/index.ts）

- 抽共享 helper `readSseResult<T>(response): Promise<T>`：读 body reader、解析 SSE 帧、忽略 `heartbeat`、收到 `result` resolve、收到 `error` throw。
- 三个 helper 内部从 `await fetch().json()` 改为 `readSseResult(...)`，并在 fetch 时带 `Accept: text/event-stream`。
- **三个函数对外签名（`Promise<ProfileParseResult>` 等）完全不变**，上层 hook/组件零改动。
- `parseDeveloperProfileInput` 现有本地降级保留（SSE 读取/连接失败时回退本地解析）。

## 测试计划

### 后端

- 新增 `tests/test_llm_client.py`：重试（网络错/5xx 重试、4xx 立即抛 `LlmRequestError`）、注入 no-op `sleep` 验证退避不真等、日志、`LlmResponseError`（缺 tool_call / 结构异常 / 校验失败）、`get_llm_client()` 未配置返 `None`。用 `MockTransport`。
- 改三个 `tests/test_*_llm.py`：domain client 构造改为注入 `LlmClient(settings, mock_http)`；HTTP 层 payload 断言（带 tools/tool_choice）不变。
- 新增 SSE helper 单测：可控的慢 `work` + 短 `interval` 验证「先若干 heartbeat 再 result」、「`work` 抛 `LlmError` → error 事件」。
- route 测试：happy path 断言流里最终有 `result` 事件且内容等于原结果；失败断言 `error` 事件（不依赖计时）。

### 前端

- 新增 `readSseResult` helper 单测：解析帧、忽略 heartbeat、`result` resolve、`error` throw。
- 改 `lib/data/api.test.ts`：三个 helper 的 mock 从返回 JSON 改为返回 SSE 流。

### 测试环境注意（来自项目记忆）

- 后端：worktree 里跑测试须 `cd backend/` 再跑，否则 import 到主仓库 editable 旧 `app`。
- 前端：本 Windows 环境跑 vitest 须加 `--pool=threads`，否则 forks pool teardown 崩。

## 迁移影响汇总

| 项 | 改动 |
|---|---|
| `LlmSettings` | 三处 → 一处（`llm_client.py`） |
| 三个 `*_llm.py` | 删 HTTP 管线，仅留 prompt/schema/render；client 类内部改为持有 `LlmClient` |
| 错误类型 | `ValueError` → `LlmError` 体系 |
| 三个 route | 同步 JSON → `async` SSE StreamingResponse |
| 前端 `lib/data/index.ts` | 三 helper 改读 SSE 流，签名不变 |

对外契约（service Protocol、前端函数签名）保持不变，blast radius 受控。

## 风险与注意

- **代理缓冲**：SSE 经 Next `/api` rewrite 代理，须确认不被缓冲（`X-Accel-Buffering: no`）；心跳间隔须短于前端/代理 idle 超时。
- **线程池**：`asyncio.to_thread` 用默认 executor，并发高时注意线程数；当前调用量低，暂不调优（YAGNI）。
- **降级路径**：未配置 LLM 时三个端点仍要能通过 result 事件正常返回（不发 error）。
- **客户端断开**：前端中途断开时，后端 `to_thread` 任务应被取消或自然结束，避免悬挂（实现时确认 StreamingResponse 的取消语义）。
