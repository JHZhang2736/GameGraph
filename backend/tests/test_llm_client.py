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
