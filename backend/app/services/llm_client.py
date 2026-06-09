from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
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


def _parse_extra_body(raw: str) -> dict:
    # provider 专属顶层参数（如 Qwen 的 enable_thinking、DashScope 限流项），由 LLM_EXTRA_BODY
    # 以 JSON 对象提供。非法/非对象时记 warning 并忽略，避免一个配置错误让每次请求 500。
    raw = raw.strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM_EXTRA_BODY is not valid JSON; ignoring: %r", raw)
        return {}
    if not isinstance(parsed, dict):
        logger.warning("LLM_EXTRA_BODY must be a JSON object; ignoring: %r", raw)
        return {}
    return parsed


@dataclass(frozen=True)
class LlmSettings:
    base_url: str
    api_key: str
    model: str
    timeout: float
    max_retries: int = 2
    backoff_base: float = 0.5
    max_invalid_retries: int = 1
    extra_body: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "LlmSettings":
        return cls(
            base_url=os.environ.get("LLM_BASE_URL", "").strip(),
            api_key=os.environ.get("LLM_API_KEY", "").strip(),
            model=os.environ.get("LLM_MODEL", "").strip(),
            timeout=float(os.environ.get("LLM_TIMEOUT", "30")),
            max_retries=int(os.environ.get("LLM_MAX_RETRIES", "2")),
            backoff_base=float(os.environ.get("LLM_BACKOFF_BASE", "0.5")),
            max_invalid_retries=int(os.environ.get("LLM_MAX_INVALID_RETRIES", "1")),
            extra_body=_parse_extra_body(os.environ.get("LLM_EXTRA_BODY", "")),
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
            # extra_body 先铺底，核心字段在后覆盖，保证 model/messages/tools/tool_choice 不被改写
            **self._settings.extra_body,
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "tools": _tool_schema(tool_name, tool_description, response_model),
            "tool_choice": {"type": "function", "function": {"name": tool_name}},
        }
        attempts = self._settings.max_invalid_retries + 1
        last_error: LlmResponseError | None = None
        for attempt in range(attempts):
            data = self._post_with_retry(payload, tool_name)
            try:
                return self._parse(data, response_model)
            except LlmResponseError as error:
                last_error = error
                logger.warning(
                    "llm invalid response model=%s tool=%s attempt=%d/%d: %s",
                    self._settings.model, tool_name, attempt + 1, attempts, error,
                )
        assert last_error is not None  # 循环至少一次必赋值
        raise last_error

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
