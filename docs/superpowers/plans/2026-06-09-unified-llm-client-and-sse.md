# 统一 LLM Client + SSE 心跳保活 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把后端 4 处散落、重复的 LLM 调用收敛到一个共享 `LlmClient`（统一重试/日志/错误/配置），并为 4 个 LLM 端点加 SSE 心跳保活，防止前端长等待时连接断开。

**Architecture:** Part A 新增 `app/services/llm_client.py`（`LlmClient.call_tool(...) -> T` + `LlmError` 体系 + `LlmSettings`），4 个 `*_llm.py` 的 domain client 类保留对外方法（守住 Protocol seam），内部改为持有 `LlmClient` 并委托 `call_tool`。Part B 新增 `app/api/sse.py`（`sse_with_heartbeat`），4 个 route 改 `async` + `StreamingResponse`，前端 `lib/data` 改读 SSE 流；对外契约（service Protocol、前端函数签名）保持不变。

**Tech Stack:** Python / FastAPI / httpx / pydantic v2 / pytest；前端 Next.js / TypeScript / vitest。

**Spec:** `docs/superpowers/specs/2026-06-09-unified-llm-client-and-sse-design.zh-CN.md`

## 执行前置

- 按 `CLAUDE.local.md`：在 worktree 中实现；新 worktree 基于落后的本地 main 时，先 `git reset --hard origin/main` 再开工。
- 后端测试必须 `cd backend/` 后再跑（否则 import 到主仓库 editable 旧 `app`）。本计划所有后端命令默认工作目录为 `backend/`。
- 前端 vitest 必须加 `--pool=threads`（本 Windows 环境 forks pool teardown 会崩）。

## 文件结构

**Part A（统一 client）**
- 新增 `backend/app/services/llm_client.py` — `LlmSettings` / `LlmError` 体系 / `LlmClient.call_tool` / `get_llm_client`。
- 新增 `backend/tests/test_llm_client.py`。
- 改 `backend/app/services/opportunity_llm.py` / `profile_llm.py` / `opportunity_frame_llm.py` / `concept_llm.py` — 删 HTTP 管线，client 类持有 `LlmClient`。
- 改 `backend/app/api/routes_concept.py` — `except ValueError` → `except (LlmError, ValueError)`（仍 JSON）。
- 改 `backend/tests/test_*_llm.py`（4 个）。

**Part B（SSE）**
- 新增 `backend/app/api/sse.py` — `sse_with_heartbeat`。
- 新增 `backend/tests/test_sse.py`、`backend/tests/sse_helpers.py`（api 测试共用的 SSE 解析）。
- 改 `backend/app/api/routes_profile.py` / `routes_opportunity.py` / `routes_concept.py` — async + SSE。
- 改 `backend/tests/test_profile_api.py` / `test_opportunity_api.py` / `test_opportunity_frame_api.py` / `test_concept_api.py`。
- 新增 `frontend/lib/data/sse.ts` — `readSseResult` / `SseStreamError`。
- 新增 `frontend/lib/data/sse.test.ts`。
- 改 `frontend/lib/data/index.ts` — 4 个 helper 改读流。
- 改 `frontend/lib/data/api.test.ts`。

---

## Part A — 统一 LLM Client

### Task 1: 新增 `llm_client.py`（核心共享 client）

**Files:**
- Create: `backend/app/services/llm_client.py`
- Test: `backend/tests/test_llm_client.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_llm_client.py`:

```python
import httpx
import pytest
from pydantic import BaseModel

from app.services.llm_client import (
    LlmClient,
    LlmRequestError,
    LlmResponseError,
    LlmSettings,
    get_llm_client,
)


class Echo(BaseModel):
    value: str


def _settings(**over) -> LlmSettings:
    base = dict(
        base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        timeout=5.0,
        max_retries=2,
        backoff_base=0.01,
    )
    base.update(over)
    return LlmSettings(**base)


def _ok_body(value: str = "hi") -> dict:
    return {
        "choices": [
            {"message": {"tool_calls": [{"function": {"name": "echo", "arguments": f'{{"value": "{value}"}}'}}]}}
        ]
    }


def _client(handler, **set_over) -> LlmClient:
    slept: list[float] = []
    c = LlmClient(
        _settings(**set_over),
        httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=slept.append,
    )
    c._slept = slept  # type: ignore[attr-defined]  # 测试用
    return c


def _call(client: LlmClient) -> Echo:
    return client.call_tool(
        system_prompt="sys", user_message="user", tool_name="echo", response_model=Echo
    )


def test_call_tool_builds_forced_tool_payload_and_parses() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = __import__("json").loads(request.content)
        return httpx.Response(200, json=_ok_body("done"))

    client = _client(handler)
    result = _call(client)
    assert result == Echo(value="done")
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["auth"] == "Bearer secret"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["tool_choice"]["function"]["name"] == "echo"
    assert seen["body"]["tools"][0]["function"]["name"] == "echo"


def test_call_tool_retries_on_5xx_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, text="upstream busy")
        return httpx.Response(200, json=_ok_body())

    client = _client(handler)
    assert _call(client) == Echo(value="hi")
    assert calls["n"] == 3
    assert client._slept == [0.01, 0.02]  # 指数退避：base*2^0, base*2^1


def test_call_tool_does_not_retry_on_4xx() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401, text="invalid_api_key")

    client = _client(handler)
    with pytest.raises(LlmRequestError) as exc:
        _call(client)
    assert exc.value.status_code == 401
    assert calls["n"] == 1
    assert client._slept == []


def test_call_tool_exhausts_retries_and_raises_request_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = _client(handler)
    with pytest.raises(LlmRequestError):
        _call(client)
    assert client._slept == [0.01, 0.02]  # max_retries=2 → 退避两次后放弃


def test_call_tool_raises_response_error_when_no_tool_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    with pytest.raises(LlmResponseError, match="tool_call"):
        _call(_client(handler))


def test_call_tool_raises_response_error_on_validation_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        bad = {"choices": [{"message": {"tool_calls": [{"function": {"name": "echo", "arguments": "{}"}}]}}]}
        return httpx.Response(200, json=bad)

    with pytest.raises(LlmResponseError):
        _call(_client(handler))


def test_get_llm_client_returns_none_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    assert get_llm_client() is None


def test_get_llm_client_builds_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_API_KEY", "secret")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    assert isinstance(get_llm_client(), LlmClient)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_llm_client.py -q`
Expected: FAIL（`ModuleNotFoundError: app.services.llm_client`）

- [ ] **Step 3: 实现 `llm_client.py`**

Create `backend/app/services/llm_client.py`:

```python
from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LlmError(Exception):
    """统一 LLM 调用错误基类。"""


class LlmRequestError(LlmError):
    """重试耗尽后的网络/超时/5xx，或不可重试的 4xx。"""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LlmResponseError(LlmError):
    """响应结构异常 / 缺 tool_call / schema 校验失败。"""


@dataclass(frozen=True)
class LlmSettings:
    base_url: str
    api_key: str
    model: str
    timeout: float
    max_retries: int = 2
    backoff_base: float = 0.5

    @classmethod
    def from_env(cls) -> "LlmSettings":
        return cls(
            base_url=os.environ.get("LLM_BASE_URL", "").strip(),
            api_key=os.environ.get("LLM_API_KEY", "").strip(),
            model=os.environ.get("LLM_MODEL", "").strip(),
            timeout=float(os.environ.get("LLM_TIMEOUT", "30")),
            max_retries=int(os.environ.get("LLM_MAX_RETRIES", "2")),
            backoff_base=float(os.environ.get("LLM_BACKOFF_BASE", "0.5")),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)


def _tool_schema(tool_name: str, tool_description: str, response_model: type[BaseModel]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_description,
                "parameters": response_model.model_json_schema(),
            },
        }
    ]


class LlmClient:
    def __init__(
        self,
        settings: LlmSettings,
        http_client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout)
        self._sleep = sleep

    def call_tool(
        self,
        *,
        system_prompt: str,
        user_message: str,
        tool_name: str,
        response_model: type[T],
        tool_description: str = "",
    ) -> T:
        payload = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "tools": _tool_schema(tool_name, tool_description, response_model),
            "tool_choice": {"type": "function", "function": {"name": tool_name}},
        }
        data = self._post_with_retry(payload, tool_name)
        return self._parse(data, response_model)

    def _post_with_retry(self, payload: dict, tool_name: str) -> dict:
        url = f"{self._settings.base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self._settings.api_key}"}
        attempts = self._settings.max_retries + 1
        start = time.monotonic()
        last_error: LlmRequestError | None = None
        for attempt in range(attempts):
            try:
                response = self._client.post(url, headers=headers, json=payload)
            except httpx.HTTPError as error:
                last_error = LlmRequestError(f"LLM transport error: {error}")
            else:
                if response.status_code < 400:
                    logger.info(
                        "llm call ok model=%s tool=%s attempt=%d elapsed=%.3fs",
                        self._settings.model, tool_name, attempt, time.monotonic() - start,
                    )
                    return response.json()
                if response.status_code < 500:
                    logger.warning(
                        "llm call 4xx model=%s tool=%s status=%d body=%s",
                        self._settings.model, tool_name, response.status_code, response.text[:500],
                    )
                    raise LlmRequestError(
                        f"LLM request failed with {response.status_code}: {response.text}",
                        status_code=response.status_code,
                    )
                last_error = LlmRequestError(
                    f"LLM request failed with {response.status_code}: {response.text}",
                    status_code=response.status_code,
                )
            if attempt < attempts - 1:
                self._sleep(self._settings.backoff_base * (2 ** attempt))
        logger.warning(
            "llm call exhausted retries model=%s tool=%s attempts=%d",
            self._settings.model, tool_name, attempts,
        )
        assert last_error is not None  # 循环至少一次必赋值
        raise last_error

    def _parse(self, data: dict, response_model: type[T]) -> T:
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise LlmResponseError(f"Unexpected LLM response shape: {data}") from error
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            raise LlmResponseError("LLM response missing tool_call")
        try:
            arguments = tool_calls[0]["function"]["arguments"]
        except (KeyError, IndexError, TypeError) as error:
            raise LlmResponseError(f"Malformed tool_call in LLM response: {data}") from error
        try:
            return response_model.model_validate_json(arguments)
        except ValidationError as error:
            raise LlmResponseError(f"LLM tool arguments failed validation: {error}") from error


def get_llm_client() -> LlmClient | None:
    settings = LlmSettings.from_env()
    if not settings.is_configured:
        return None
    return LlmClient(settings)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_llm_client.py -q`
Expected: PASS（9 passed）

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/llm_client.py backend/tests/test_llm_client.py
git commit -m "feat(backend): add unified LlmClient with retry/logging/error types"
```

---

### Task 2: 迁移 `opportunity_llm.py` 到 `LlmClient`（并再导出 `LlmSettings`）

**Files:**
- Modify: `backend/app/services/opportunity_llm.py`
- Test: `backend/tests/test_opportunity_llm.py`

- [ ] **Step 1: 改测试为注入 `LlmClient`**

在 `backend/tests/test_opportunity_llm.py` 顶部，把构造 client 的方式从 `OpportunityLlmClient(_settings(), httpx.Client(...))` 改为先建 `LlmClient`。具体：

把 import 改为（新增 `LlmClient`，`LlmSettings` 仍从 opportunity_llm 拿以验证再导出）：

```python
from app.services.llm_client import LlmClient
from app.services.opportunity_llm import (
    LlmSettings,
    OpportunityLlmClient,
    get_opportunity_llm_client,
)
```

把每处 `OpportunityLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))` 替换为：

```python
OpportunityLlmClient(
    LlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
)
```

把断言 `pytest.raises(ValueError, ...)` 改为对应的 `LlmResponseError` / `LlmRequestError`（顶部 `from app.services.llm_client import LlmRequestError, LlmResponseError`）：
- “no tool_call” 用例 → `pytest.raises(LlmResponseError, match="tool_call")`
- HTTP 401 用例 → `pytest.raises(LlmRequestError)`

若该文件有 `test_build_tool_schema...` 用例并 import `build_tool_schema`，删除该用例与该 import（schema 构建已移入 `LlmClient` 并在 `test_llm_client.py` 覆盖）。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_opportunity_llm.py -q`
Expected: FAIL（`OpportunityLlmClient` 旧签名 `(settings, http_client)` 与新构造不符 / `build_tool_schema` 已删）

- [ ] **Step 3: 改实现**

在 `backend/app/services/opportunity_llm.py`：

删除顶部 `import os`、`from dataclasses import dataclass`、`import httpx`、`LlmSettings` 类整段定义（27–45 行那段），改为新增 import 并再导出（兼容旧 import 点：opportunity_frame_llm / concept_llm / 多个测试）：

```python
from app.services.llm_client import LlmClient, LlmSettings  # noqa: F401  (LlmSettings 再导出)
```

删除 `build_tool_schema` 函数。把 `OpportunityLlmClient` 整段替换为：

```python
class OpportunityLlmClient:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    def judge(
        self, profile: DeveloperProfile, candidates: list[CandidateOpportunityArea]
    ) -> OpportunityJudgmentBatch:
        user = f"开发者画像：\n{_profile_block(profile)}\n\n候选机会：\n{_candidate_block(candidates)}"
        return self._llm.call_tool(
            system_prompt=SYSTEM_PROMPT,
            user_message=user,
            tool_name=TOOL_NAME,
            response_model=OpportunityJudgmentBatch,
            tool_description="Return keep/reject judgments for the supplied opportunity candidates.",
        )
```

把工厂改为：

```python
def get_opportunity_llm_client() -> OpportunityLlmClient | None:
    llm = get_llm_client()
    if llm is None:
        return None
    return OpportunityLlmClient(llm)
```

并在顶部 import 处加 `from app.services.llm_client import LlmClient, LlmSettings, get_llm_client`（合并上面的再导出行）。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_opportunity_llm.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/opportunity_llm.py backend/tests/test_opportunity_llm.py
git commit -m "refactor(backend): opportunity_llm delegates to shared LlmClient"
```

---

### Task 3: 迁移 `profile_llm.py` 到 `LlmClient`

**Files:**
- Modify: `backend/app/services/profile_llm.py`
- Test: `backend/tests/test_profile_llm.py`

- [ ] **Step 1: 改测试**

在 `backend/tests/test_profile_llm.py`：

import 改为：

```python
from app.services.llm_client import LlmClient, LlmRequestError, LlmResponseError
from app.services.profile_llm import (
    ExtractedConstraint,  # 若原已 import 则保留
    ProfileExtraction,
    ProfileLlmClient,
    get_llm_client,
)
```

删除 `LlmSettings` 旧 import 改为 `from app.services.llm_client import LlmSettings`（`_settings()` 助手不变，但需补 `max_retries`/`backoff_base` 默认即可，无需显式传）。

把两处 `ProfileLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))` 替换为：

```python
ProfileLlmClient(LlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler))))
```

断言替换：
- `test_extract_raises_when_no_tool_call`：`pytest.raises(ValueError, match="tool_call")` → `pytest.raises(LlmResponseError, match="tool_call")`
- `test_extract_raises_value_error_on_http_error`：`pytest.raises(ValueError, match="401")` → `pytest.raises(LlmRequestError, match="401")`

删除 `test_build_tool_schema_exposes_function_name` 用例与 `build_tool_schema` import。保留 `test_extraction_ignores_unexpected_keys`（纯 schema 行为，不依赖 client）。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_profile_llm.py -q`
Expected: FAIL

- [ ] **Step 3: 改实现**

在 `backend/app/services/profile_llm.py`：删除 `import os`、`from dataclasses import dataclass`、`import httpx`、`LlmSettings` 类定义、`build_tool_schema` 函数。顶部加：

```python
from app.services.llm_client import LlmClient, get_llm_client
```

`ProfileLlmClient` 替换为：

```python
class ProfileLlmClient:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    def extract(self, input_data: ProfileParseInput) -> ProfileExtraction:
        return self._llm.call_tool(
            system_prompt=SYSTEM_PROMPT,
            user_message=_user_message(input_data),
            tool_name=TOOL_NAME,
            response_model=ProfileExtraction,
            tool_description="Return the structured developer profile extracted from the input.",
        )
```

工厂替换为：

```python
def get_llm_client() -> ProfileLlmClient | None:
    llm = get_llm_client_base()
    if llm is None:
        return None
    return ProfileLlmClient(llm)
```

注意命名冲突：本模块工厂也叫 `get_llm_client`（routes_profile 依赖此名）。为避免与 `llm_client.get_llm_client` 同名，import 时改别名：

```python
from app.services.llm_client import LlmClient, get_llm_client as get_llm_client_base
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_profile_llm.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/profile_llm.py backend/tests/test_profile_llm.py
git commit -m "refactor(backend): profile_llm delegates to shared LlmClient"
```

---

### Task 4: 迁移 `opportunity_frame_llm.py` 到 `LlmClient`

**Files:**
- Modify: `backend/app/services/opportunity_frame_llm.py`
- Test: `backend/tests/test_opportunity_frame_llm.py`

- [ ] **Step 1: 改测试**

在 `backend/tests/test_opportunity_frame_llm.py`：

`from app.services.opportunity_llm import LlmSettings` 改为 `from app.services.llm_client import LlmClient, LlmSettings`，并按需 `from app.services.llm_client import LlmResponseError`。

把每处 `OpportunityFrameLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))` 替换为：

```python
OpportunityFrameLlmClient(
    LlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
)
```

若有 `build_frame_tool_schema` 的用例与 import，删除（schema 构建已统一）。涉及 “no tool_call” / HTTP 错误的 `pytest.raises(ValueError)` 改为对应 `LlmResponseError` / `LlmRequestError`。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_opportunity_frame_llm.py -q`
Expected: FAIL

- [ ] **Step 3: 改实现**

在 `backend/app/services/opportunity_frame_llm.py`：删除 `import httpx`、`build_frame_tool_schema`。把第 13–17 行的 import 块：

```python
from app.services.opportunity_llm import (
    LlmSettings,
    _candidate_block,
    _profile_block,
)
```

改为（`LlmSettings` 不再需要；`_candidate_block`/`_profile_block` 仍复用；新增 `LlmClient`、`get_llm_client`）：

```python
from app.services.llm_client import LlmClient, get_llm_client
from app.services.opportunity_llm import _candidate_block, _profile_block
```

`OpportunityFrameLlmClient` 替换为：

```python
class OpportunityFrameLlmClient:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    def synthesize(
        self, profile: DeveloperProfile, area: OpportunityArea, inputs: FrameInputs
    ) -> FrameSynthesis:
        return self._llm.call_tool(
            system_prompt=SYSTEM_PROMPT,
            user_message=_user_block(profile, area, inputs),
            tool_name=TOOL_NAME,
            response_model=FrameSynthesis,
            tool_description="Synthesize the narrative fields of one opportunity frame.",
        )
```

工厂替换为：

```python
def get_opportunity_frame_llm_client() -> OpportunityFrameLlmClient | None:
    llm = get_llm_client()
    if llm is None:
        return None
    return OpportunityFrameLlmClient(llm)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_opportunity_frame_llm.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/opportunity_frame_llm.py backend/tests/test_opportunity_frame_llm.py
git commit -m "refactor(backend): opportunity_frame_llm delegates to shared LlmClient"
```

---

### Task 5: 迁移 `concept_llm.py` + 修 `routes_concept` 异常捕获

**Files:**
- Modify: `backend/app/services/concept_llm.py`
- Modify: `backend/app/api/routes_concept.py`
- Test: `backend/tests/test_concept_llm.py`

- [ ] **Step 1: 改测试**

在 `backend/tests/test_concept_llm.py`：`from app.services.opportunity_llm import LlmSettings` 改为 `from app.services.llm_client import LlmClient, LlmSettings`（按需加 `LlmResponseError` / `LlmRequestError`）。把每处 `ConceptLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))` 替换为：

```python
ConceptLlmClient(LlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler))))
```

涉及 `build_concept_tool_schema` 的用例/ import 删除；`pytest.raises(ValueError)` 改为对应 `LlmResponseError` / `LlmRequestError`。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_concept_llm.py -q`
Expected: FAIL

- [ ] **Step 3: 改实现**

在 `backend/app/services/concept_llm.py`：删除 `import httpx`、`build_concept_tool_schema`。把第 8–9 行：

```python
# 有意复用 6.5 的 LLM 设施（DRY）：LlmSettings 的 env 读取与 is_configured。
from app.services.opportunity_llm import LlmSettings
```

改为：

```python
from app.services.llm_client import LlmClient, get_llm_client
```

`ConceptLlmClient` 替换为：

```python
class ConceptLlmClient:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    def generate(self, frame: OpportunityFrame) -> ConceptGenerationBatch:
        return self._llm.call_tool(
            system_prompt=SYSTEM_PROMPT,
            user_message=_frame_block(frame),
            tool_name=TOOL_NAME,
            response_model=ConceptGenerationBatch,
            tool_description="Emit exactly three concept cards within the opportunity frame.",
        )
```

工厂替换为：

```python
def get_concept_llm_client() -> ConceptLlmClient | None:
    llm = get_llm_client()
    if llm is None:
        return None
    return ConceptLlmClient(llm)
```

在 `backend/app/api/routes_concept.py`：顶部加 `from app.services.llm_client import LlmError`；把 `except ValueError as error:` 改为 `except (LlmError, ValueError) as error:`（`ConceptCard(...)` 可能抛 `ValidationError`（`ValueError` 子类），client 抛 `LlmError`，二者都映射 502）。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_concept_llm.py tests/test_concept_api.py tests/test_concept_service.py -q`
Expected: PASS（route 仍 JSON，502/503 行为不变）

- [ ] **Step 5: 全量后端回归 + 提交**

Run: `cd backend && python -m pytest -q`
Expected: PASS（Part A 完成，全绿）

```bash
git add backend/app/services/concept_llm.py backend/app/api/routes_concept.py backend/tests/test_concept_llm.py
git commit -m "refactor(backend): concept_llm delegates to shared LlmClient; routes_concept catches LlmError"
```

---

## Part B — SSE 心跳保活

### Task 6: 新增 `sse_with_heartbeat` + 测试助手

**Files:**
- Create: `backend/app/api/sse.py`
- Create: `backend/tests/test_sse.py`
- Create: `backend/tests/sse_helpers.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_sse.py`。后端未配置 pytest-asyncio/anyio 插件，故用 `asyncio.run` 直接驱动异步生成器（不依赖任何插件）：

```python
import asyncio
import json
import time

from app.api.sse import sse_with_heartbeat
from app.services.llm_client import LlmError


def _run(work, to_event, **kw) -> list[tuple[str, str]]:
    async def drain() -> list[tuple[str, str]]:
        events: list[tuple[str, str]] = []
        async for raw in sse_with_heartbeat(work, to_event, **kw):
            block = raw.decode("utf-8").strip()
            event = data = None
            for line in block.split("\n"):
                if line.startswith("event:"):
                    event = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data = line[len("data:"):].strip()
            events.append((event or "", data or ""))
        return events

    return asyncio.run(drain())


def test_emits_heartbeats_then_result() -> None:
    def work() -> dict:
        time.sleep(0.25)  # 阻塞，跨过两次 interval
        return {"value": "done"}

    events = _run(work, lambda r: json.dumps(r), interval=0.1)
    assert ("heartbeat", "{}") in events
    assert events[-1][0] == "result"
    assert json.loads(events[-1][1]) == {"value": "done"}


def test_emits_error_event_on_llm_error() -> None:
    def work() -> dict:
        raise LlmError("boom")

    events = _run(work, lambda r: json.dumps(r), interval=0.1)
    assert events[-1][0] == "error"
    assert json.loads(events[-1][1])["detail"] == "boom"


def test_error_event_includes_code_when_configured() -> None:
    def work() -> dict:
        raise ValueError("bad")

    events = _run(
        work, lambda r: json.dumps(r),
        interval=0.1, error_types=(LlmError, ValueError), error_code=502,
    )
    payload = json.loads(events[-1][1])
    assert events[-1][0] == "error"
    assert payload["code"] == 502
    assert payload["detail"] == "bad"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_sse.py -q`
Expected: FAIL（`ModuleNotFoundError: app.api.sse`）

- [ ] **Step 3: 实现 `sse.py`**

Create `backend/app/api/sse.py`:

```python
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from typing import TypeVar

from app.services.llm_client import LlmError

logger = logging.getLogger(__name__)

T = TypeVar("T")

_HEARTBEAT = b"event: heartbeat\ndata: {}\n\n"


def _frame(event: str, data: str) -> bytes:
    return f"event: {event}\ndata: {data}\n\n".encode("utf-8")


async def sse_with_heartbeat(
    work: Callable[[], T],
    to_event: Callable[[T], str],
    *,
    interval: float = 10.0,
    error_types: tuple[type[BaseException], ...] = (LlmError,),
    error_code: int | None = None,
) -> AsyncIterator[bytes]:
    """在工作线程跑阻塞的 `work`；等待期间每 `interval` 秒发心跳；
    完成发 result 事件（`to_event` 返回已序列化的 JSON 字符串）；
    `work` 抛 `error_types` 之一时发 error 事件（可带 `code`）。其他异常向上传播（响亮失败）。"""
    task = asyncio.create_task(asyncio.to_thread(work))
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=interval)
            if done:
                break
            yield _HEARTBEAT
    except asyncio.CancelledError:
        task.cancel()
        raise
    try:
        result = task.result()
    except error_types as error:
        logger.warning("sse work failed: %s", error)
        payload: dict[str, object] = {"detail": str(error)}
        if error_code is not None:
            payload["code"] = error_code
        yield _frame("error", json.dumps(payload, ensure_ascii=False))
        return
    yield _frame("result", to_event(result))
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_sse.py -q`
Expected: PASS（3 passed）

- [ ] **Step 5: 新增 api 测试共用的 SSE 解析助手**

Create `backend/tests/sse_helpers.py`:

```python
"""api 测试共用：把 SSE 响应体解析出 result/error。"""
from __future__ import annotations

import json


def sse_events(response) -> list[tuple[str, str]]:
    events: list[tuple[str, str]] = []
    for block in response.text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event = data = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = line[len("data:"):].strip()
        if event is not None:
            events.append((event, data or ""))
    return events


def sse_result(response) -> object:
    """返回 result 事件解析后的 JSON；遇 error 事件则断言失败。"""
    for event, data in sse_events(response):
        if event == "result":
            return json.loads(data)
        if event == "error":
            raise AssertionError(f"unexpected SSE error event: {data}")
    raise AssertionError("no result event in SSE stream")


def sse_error(response) -> dict:
    """返回 error 事件解析后的 dict；无则断言失败。"""
    for event, data in sse_events(response):
        if event == "error":
            return json.loads(data)
    raise AssertionError("no error event in SSE stream")
```

- [ ] **Step 6: 提交**

```bash
git add backend/app/api/sse.py backend/tests/test_sse.py backend/tests/sse_helpers.py
git commit -m "feat(backend): add sse_with_heartbeat helper and test utilities"
```

---

### Task 7: `routes_profile` 改 SSE

**Files:**
- Modify: `backend/app/api/routes_profile.py`
- Test: `backend/tests/test_profile_api.py`

- [ ] **Step 1: 改测试**

在 `backend/tests/test_profile_api.py`：顶部加 `from tests.sse_helpers import sse_result`。

`test_parse_uses_llm_client_when_present` 改为解析 SSE：

```python
def test_parse_uses_llm_client_when_present(client: TestClient) -> None:
    app.dependency_overrides[get_llm_client] = lambda: FakeClient()
    response = client.post("/profile/parse", json={"raw_text": "我一个人做游戏"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = sse_result(response)
    assert body["draft"]["team_size"] == "solo"
    assert body["draft"]["is_complete"] is True
    assert body["draft"]["audio_ability"] == "basic"
```

`test_parse_falls_back_to_rules_when_unconfigured` 改为：

```python
def test_parse_falls_back_to_rules_when_unconfigured(client: TestClient) -> None:
    app.dependency_overrides[get_llm_client] = lambda: None
    response = client.post(
        "/profile/parse",
        json={"raw_text": (
            "我是 solo 开发者，程序能力强，美术能力弱，三个月原型。"
            "我喜欢 Balatro，想要短局，不要做在线多人，也不想做大量内容。"
        )},
    )
    assert response.status_code == 200
    assert sse_result(response)["draft"]["is_complete"] is True
```

`test_parse_rejects_blank_text_with_422` 不变（422 在请求校验阶段，仍 JSON）。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_profile_api.py -q`
Expected: FAIL（当前仍是 JSON，无 event-stream / `sse_result` 找不到 result）

- [ ] **Step 3: 改实现**

把 `backend/app/api/routes_profile.py` 整体替换为：

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.sse import sse_with_heartbeat
from app.schemas.developer_profile import ProfileParseInput
from app.services.profile_llm import ProfileLlmClient, get_llm_client
from app.services.profile_parse_service import parse_profile

router = APIRouter()

_SSE_HEADERS = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}


@router.post("/profile/parse")
async def parse_profile_endpoint(
    document: ProfileParseInput,
    client: ProfileLlmClient | None = Depends(get_llm_client),
) -> StreamingResponse:
    def work():
        return parse_profile(document, client)

    return StreamingResponse(
        sse_with_heartbeat(work, lambda r: r.model_dump_json()),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_profile_api.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/routes_profile.py backend/tests/test_profile_api.py
git commit -m "feat(backend): stream /profile/parse via SSE with heartbeat"
```

---

### Task 8: `routes_opportunity`（match + frame）改 SSE

**Files:**
- Modify: `backend/app/api/routes_opportunity.py`
- Test: `backend/tests/test_opportunity_api.py`, `backend/tests/test_opportunity_frame_api.py`

- [ ] **Step 1: 改测试**

在 `backend/tests/test_opportunity_api.py` 顶部加 `from tests.sse_helpers import sse_result`。把 `test_match_endpoint_returns_areas` 与 `test_match_endpoint_accepts_profile_without_optional_lists` 中的 `body = response.json()` / `response.json()["profile_id"]` 改为 `body = sse_result(response)` / `sse_result(response)["profile_id"]`，状态码断言保留 200。两个 422 用例（`rejects_bare_profile_body`、`rejects_malformed_profile`）不变。

在 `backend/tests/test_opportunity_frame_api.py` 顶部加 `from tests.sse_helpers import sse_result`。把 `test_frame_endpoint_returns_frame` 与 `test_frame_endpoint_degrades_without_llm` 中的 `body = response.json()` 改为 `body = sse_result(response)`，其余断言不变。422 用例不变。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_opportunity_api.py tests/test_opportunity_frame_api.py -q`
Expected: FAIL（仍 JSON）

- [ ] **Step 3: 改实现**

在 `backend/app/api/routes_opportunity.py`：顶部 import 加：

```python
from fastapi.responses import StreamingResponse

from app.api.sse import sse_with_heartbeat
```

并在 `router = APIRouter()` 下方加：

```python
_SSE_HEADERS = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
```

把 `match_endpoint` 替换为：

```python
@router.post("/opportunity/match")
async def match_endpoint(
    request: OpportunityMatchRequest,
    repository: OpportunityRepository = Depends(get_opportunity_repository),
    llm_client: OpportunityLlmClient | None = Depends(get_opportunity_llm),
) -> StreamingResponse:
    def work():
        return match_opportunities(
            request.profile, repository, llm_client, seen_ids=request.seen_ids
        )

    return StreamingResponse(
        sse_with_heartbeat(work, lambda r: r.model_dump_json()),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
```

把 `frame_endpoint` 替换为：

```python
@router.post("/opportunity/frame")
async def frame_endpoint(
    request: OpportunityFrameRequest,
    repository: OpportunityRepository = Depends(get_opportunity_repository),
    llm_client: OpportunityFrameLlmClient | None = Depends(get_opportunity_frame_llm),
) -> StreamingResponse:
    def work():
        return build_frame(request.profile, request.area, repository, llm_client)

    return StreamingResponse(
        sse_with_heartbeat(work, lambda r: r.model_dump_json()),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
```

（去掉两处原 `response_model=` 与 `OpportunityMatchResult`/`OpportunityFrame` 返回注解。清理因此变为未使用的 import：`from app.schemas.opportunity import OpportunityArea, OpportunityMatchResult` → 删 `OpportunityMatchResult`（`OpportunityArea` 仍被 `OpportunityFrameRequest` 使用，保留）；`from app.schemas.artifacts import DeveloperProfile, OpportunityFrame` → 删 `OpportunityFrame`（`DeveloperProfile` 仍被请求模型使用，保留）。）

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_opportunity_api.py tests/test_opportunity_frame_api.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/routes_opportunity.py backend/tests/test_opportunity_api.py backend/tests/test_opportunity_frame_api.py
git commit -m "feat(backend): stream /opportunity/match and /opportunity/frame via SSE"
```

---

### Task 9: `routes_concept` 改 SSE（503 保留为 HTTP、502 转 error 事件）

**Files:**
- Modify: `backend/app/api/routes_concept.py`
- Test: `backend/tests/test_concept_api.py`

- [ ] **Step 1: 改测试**

在 `backend/tests/test_concept_api.py` 顶部加 `from tests.sse_helpers import sse_result, sse_error`。

`test_generate_endpoint_returns_three_cards` 改为：

```python
def test_generate_endpoint_returns_three_cards() -> None:
    app.dependency_overrides[get_concept_llm] = lambda: StubLlm()
    try:
        client = TestClient(app)
        response = client.post("/concept/generate", json={"frame": _frame_dict()})
        assert response.status_code == 200
        body = sse_result(response)
        assert len(body) == 3
        assert body[0]["opportunity_frame_id"] == _frame_dict()["id"]
        assert body[0]["id"] == f"concept|{_frame_dict()['id']}|1"
    finally:
        app.dependency_overrides.clear()
```

`test_generate_endpoint_503_without_llm` 不变（开流前拦截，仍 503 JSON）。

`test_generate_endpoint_502_on_llm_error` 改为断言 error 事件：

```python
def test_generate_endpoint_502_on_llm_error() -> None:
    app.dependency_overrides[get_concept_llm] = lambda: BrokenLlm()
    try:
        client = TestClient(app)
        response = client.post("/concept/generate", json={"frame": _frame_dict()})
        assert response.status_code == 200  # 流已开，错误走 error 事件
        err = sse_error(response)
        assert err["code"] == 502
        assert "upstream boom" in err["detail"]
    finally:
        app.dependency_overrides.clear()
```

`test_generate_endpoint_rejects_malformed_request`（422）不变。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_concept_api.py -q`
Expected: FAIL

- [ ] **Step 3: 改实现**

把 `backend/app/api/routes_concept.py` 整体替换为：

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.sse import sse_with_heartbeat
from app.schemas.artifacts import OpportunityFrame
from app.schemas.common import StrictBaseModel
from app.services.concept_llm import ConceptLlmClient, get_concept_llm_client
from app.services.concept_service import generate_concepts
from app.services.llm_client import LlmError

router = APIRouter()

_SSE_HEADERS = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}


class ConceptGenerateRequest(StrictBaseModel):
    frame: OpportunityFrame


def get_concept_llm() -> ConceptLlmClient | None:
    # 默认 provider：返回可选概念生成 LLM 客户端。测试通过 dependency_overrides 覆盖。
    return get_concept_llm_client()


@router.post("/concept/generate")
async def generate_endpoint(
    request: ConceptGenerateRequest,
    llm_client: ConceptLlmClient | None = Depends(get_concept_llm),
) -> StreamingResponse:
    # 硬依赖 LLM：未配置 → 开流前 503（HTTP 状态保留）。
    if llm_client is None:
        raise HTTPException(status_code=503, detail="未配置 LLM，概念生成不可用。")

    def work():
        # 失败（LlmError）/产物非法（ValidationError ⊂ ValueError）→ 502 error 事件。
        return generate_concepts(request.frame, llm_client)

    def to_event(cards) -> str:
        import json
        return json.dumps([c.model_dump(mode="json") for c in cards], ensure_ascii=False)

    return StreamingResponse(
        sse_with_heartbeat(
            work, to_event, error_types=(LlmError, ValueError), error_code=502
        ),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
```

- [ ] **Step 4: 跑测试确认通过 + 全量后端回归**

Run: `cd backend && python -m pytest -q`
Expected: PASS（Part B 后端完成，全绿）

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/routes_concept.py backend/tests/test_concept_api.py
git commit -m "feat(backend): stream /concept/generate via SSE; keep 503 HTTP, 502 as error event"
```

---

### Task 10: 前端 `readSseResult` helper

**Files:**
- Create: `frontend/lib/data/sse.ts`
- Test: `frontend/lib/data/sse.test.ts`

- [ ] **Step 1: 写失败测试**

Create `frontend/lib/data/sse.test.ts`:

jsdom 下 `new Response(text).body` 可能为 null，故用显式 `ReadableStream` 构造 mock response（`readSseResult` 只用到 `response.body.getReader()`）。

```typescript
import { describe, it, expect } from "vitest";
import { readSseResult, SseStreamError } from "@/lib/data/sse";

function sseResponse(text: string, status = 200): Response {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text));
      controller.close();
    },
  });
  return { ok: status >= 200 && status < 300, status, body } as unknown as Response;
}

describe("readSseResult", () => {
  it("ignores heartbeats and resolves the result event", async () => {
    const text =
      "event: heartbeat\ndata: {}\n\n" +
      "event: heartbeat\ndata: {}\n\n" +
      'event: result\ndata: {"value":"done"}\n\n';
    const out = await readSseResult<{ value: string }>(sseResponse(text));
    expect(out.value).toBe("done");
  });

  it("throws SseStreamError with detail and code on error event", async () => {
    const text = 'event: error\ndata: {"detail":"boom","code":502}\n\n';
    await expect(readSseResult(sseResponse(text))).rejects.toMatchObject({
      message: "boom",
      code: 502,
    });
    await expect(readSseResult(sseResponse(text))).rejects.toBeInstanceOf(SseStreamError);
  });

  it("throws when the stream ends without a result event", async () => {
    const text = "event: heartbeat\ndata: {}\n\n";
    await expect(readSseResult(sseResponse(text))).rejects.toThrow();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run lib/data/sse.test.ts --pool=threads`
Expected: FAIL（`Cannot find module '@/lib/data/sse'`）

- [ ] **Step 3: 实现 `sse.ts`**

Create `frontend/lib/data/sse.ts`:

```typescript
export interface SsePayload {
  detail: string;
  code?: number;
}

export class SseStreamError extends Error {
  readonly code?: number;
  constructor(detail: string, code?: number) {
    super(detail);
    this.name = "SseStreamError";
    this.code = code;
  }
}

function parseBlock(block: string): { event: string; data: string } | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

// 读取后端 SSE 流：忽略 heartbeat，收到 result resolve，收到 error 抛 SseStreamError。
export async function readSseResult<T>(response: Response): Promise<T> {
  const body = response.body;
  if (!body) throw new Error("SSE response has no body");
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (value) buffer += decoder.decode(value, { stream: true });
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const rawBlock = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const parsed = parseBlock(rawBlock);
        if (!parsed || parsed.event === "heartbeat") continue;
        if (parsed.event === "result") return JSON.parse(parsed.data) as T;
        if (parsed.event === "error") {
          const payload = JSON.parse(parsed.data) as SsePayload;
          throw new SseStreamError(payload.detail, payload.code);
        }
      }
      if (done) break;
    }
  } finally {
    reader.releaseLock();
  }
  throw new Error("SSE stream ended without a result event");
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd frontend && npx vitest run lib/data/sse.test.ts --pool=threads`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/lib/data/sse.ts frontend/lib/data/sse.test.ts
git commit -m "feat(frontend): add readSseResult SSE stream reader"
```

---

### Task 11: 前端 `lib/data/index.ts` 四个 helper 改读 SSE

**Files:**
- Modify: `frontend/lib/data/index.ts`
- Test: `frontend/lib/data/api.test.ts`

- [ ] **Step 1: 改测试**

在 `frontend/lib/data/api.test.ts`：

顶部 import 加 `generateConcepts, ConceptGenerationError`：

```typescript
import {
  listGames,
  getNeighbors,
  searchGraphNodes,
  importGame,
  ImportError,
  matchOpportunities,
  generateConcepts,
  ConceptGenerationError,
} from "@/lib/data";
```

新增 SSE 响应助手（紧跟 `mockFetch` 之后）。jsdom 下用显式 `ReadableStream` 构造 body：

```typescript
function sseFetch(frames: string, status = 200) {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(frames));
      controller.close();
    },
  });
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    body,
  } as unknown as Response);
}
```

把 `matchOpportunities posts the profile and parses the result` 用例的 mock 从 `mockFetch(200, result)` 改为 SSE：

```typescript
  it("matchOpportunities posts the profile and parses the result", async () => {
    const result = { profile_id: "dev_profile_1", areas: [], rejected: [], warnings: ["图谱规模较小。"] };
    const fetchMock = sseFetch(`event: result\ndata: ${JSON.stringify(result)}\n\n`);
    vi.stubGlobal("fetch", fetchMock);
    const parsed = await matchOpportunities({ id: "dev_profile_1" } as never, ["opp|seen|1"]);
    expect(parsed.warnings).toEqual(["图谱规模较小。"]);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/opportunity/match");
    expect((init as RequestInit).method).toBe("POST");
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.seen_ids).toEqual(["opp|seen|1"]);
    expect(body.profile).toEqual({ id: "dev_profile_1" });
  });
```

把 `matchOpportunities throws on a 500` 用例改为非 ok 流响应：

```typescript
  it("matchOpportunities throws on a 500", async () => {
    vi.stubGlobal("fetch", sseFetch("", 500));
    await expect(matchOpportunities({ id: "x" } as never, [])).rejects.toThrow();
  });
```

新增 `generateConcepts` 用例：

```typescript
  it("generateConcepts parses the SSE result", async () => {
    const cards = [{ id: "concept|f|1", title: "A" }];
    vi.stubGlobal("fetch", sseFetch(`event: result\ndata: ${JSON.stringify(cards)}\n\n`));
    const out = await generateConcepts({ id: "f" } as never);
    expect(out[0].id).toBe("concept|f|1");
  });

  it("generateConcepts throws ConceptGenerationError(503) when unconfigured", async () => {
    vi.stubGlobal("fetch", sseFetch("", 503));
    await expect(generateConcepts({ id: "f" } as never)).rejects.toMatchObject({
      name: "ConceptGenerationError",
      status: 503,
    });
  });

  it("generateConcepts maps an error event to ConceptGenerationError(502)", async () => {
    vi.stubGlobal(
      "fetch",
      sseFetch('event: error\ndata: {"detail":"LLM 失败","code":502}\n\n'),
    );
    await expect(generateConcepts({ id: "f" } as never)).rejects.toMatchObject({
      name: "ConceptGenerationError",
      status: 502,
    });
  });
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run lib/data/api.test.ts --pool=threads`
Expected: FAIL（helper 仍走 `.json()`，SSE Response 无 `.json()` 结果 / generateConcepts 未导出符合断言的行为）

- [ ] **Step 3: 改实现**

在 `frontend/lib/data/index.ts`：

顶部加 import：

```typescript
import { readSseResult, SseStreamError } from "@/lib/data/sse";
```

`parseDeveloperProfileInput` 的 fetch 体改为（保留外层 try/catch 本地降级）：

```typescript
    const response = await fetch(`${apiBase()}/profile/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(input),
    });
    if (!response.ok) throw new Error(`profile/parse responded ${response.status}`);
    return await readSseResult<ProfileParseResult>(response);
```

`matchOpportunities` 改为：

```typescript
  const res = await fetch(`${apiBase()}/opportunity/match`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ profile, seen_ids: seenIds }),
  });
  if (!res.ok) throw new Error(`POST /opportunity/match responded ${res.status}`);
  return await readSseResult<OpportunityMatchResult>(res);
```

`buildOpportunityFrame` 改为：

```typescript
  const res = await fetch(`${apiBase()}/opportunity/frame`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ profile, area }),
  });
  if (!res.ok) throw new Error(`POST /opportunity/frame responded ${res.status}`);
  return await readSseResult<OpportunityFrame>(res);
```

`generateConcepts` 改为（保留 502/503 区分）：

```typescript
export async function generateConcepts(frame: OpportunityFrame): Promise<ConceptCard[]> {
  const res = await fetch(`${apiBase()}/concept/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ frame }),
  });
  if (!res.ok) {
    throw new ConceptGenerationError(
      `POST /concept/generate responded ${res.status}`,
      res.status,
    );
  }
  try {
    return await readSseResult<ConceptCard[]>(res);
  } catch (error) {
    if (error instanceof SseStreamError) {
      throw new ConceptGenerationError(error.message, error.code ?? 502);
    }
    throw error;
  }
}
```

- [ ] **Step 4: 跑测试确认通过 + 前端全量回归**

Run: `cd frontend && npx vitest run lib/data/api.test.ts lib/data/sse.test.ts --pool=threads`
Expected: PASS

Run: `cd frontend && npx vitest run --pool=threads`
Expected: PASS（前端全绿；上层 hook/组件因签名不变无需改动）

- [ ] **Step 5: 提交**

```bash
git add frontend/lib/data/index.ts frontend/lib/data/api.test.ts
git commit -m "feat(frontend): consume SSE streams for the four LLM endpoints"
```

---

## 收尾验证

- [ ] 后端全量：`cd backend && python -m pytest -q` → 全绿。
- [ ] 前端全量：`cd frontend && npx vitest run --pool=threads` → 全绿。
- [ ] 人工确认（可选，需配 LLM env）：起后端 + 前端，触发 `/concept/generate`，浏览器 Network 面板看到 `text/event-stream`、等待期间有 `heartbeat` 帧、最终 `result` 帧，前端正常渲染。

## 自检对照 spec

- 统一 client（call_tool/retry/log/error/config）→ Task 1。
- 四个 domain client 迁移 → Task 2–5。
- `LlmSettings` 单一来源 + 再导出兼容 → Task 1/2。
- `routes_concept` 异常类型切换 → Task 5。
- `sse_with_heartbeat` + 事件协议（heartbeat/result/error+code）→ Task 6。
- 四个 route SSE + concept 503 前置/502 code → Task 7–9。
- 前端 `readSseResult` + 四 helper 改读流 + concept 502/503 区分 → Task 10–11。
- 测试环境注意（backend cwd、vitest --pool=threads）→ 已写入各命令。
