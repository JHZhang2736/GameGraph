import json

import httpx
import pytest

from app.schemas.common import ConstraintType
from app.schemas.developer_profile import ProfileParseInput
from app.services.llm_client import LlmClient, LlmRequestError, LlmResponseError, LlmSettings
from app.services.profile_llm import (
    ProfileExtraction,
    ProfileLlmClient,
    get_llm_client,
)


def _settings() -> LlmSettings:
    return LlmSettings(
        base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        timeout=5.0,
    )


def _extraction_arguments() -> str:
    return json.dumps(
        {
            "team_size": "solo",
            "time_budget": "three month prototype",
            "programming_ability": "strong",
            "art_ability": "weak",
            "audio_ability": None,
            "content_production_ability": "limited",
            "liked_references": ["Hades"],
            "disliked_references_or_mechanics": ["online multiplayer"],
            "desired_player_experiences": ["short runs"],
            "constraints": [
                {"type": "hard", "statement": "Do not require online multiplayer."}
            ],
            "field_sources": [
                {"field": "team_size", "source_text": "我一个人做"}
            ],
            "warnings": [],
        }
    )


def test_extract_posts_tool_call_request_and_parses_arguments() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        body = json.loads(request.content)
        seen["body"] = body
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "emit_developer_profile",
                                        "arguments": _extraction_arguments(),
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
        )

    client = ProfileLlmClient(
        LlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    )
    extraction = client.extract(ProfileParseInput(raw_text="我一个人做游戏"))

    assert isinstance(extraction, ProfileExtraction)
    assert extraction.team_size == "solo"
    assert extraction.audio_ability is None
    assert extraction.constraints[0].type == ConstraintType.HARD
    assert extraction.field_sources[0].source_text == "我一个人做"
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["auth"] == "Bearer secret"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["tool_choice"]["function"]["name"] == "emit_developer_profile"


def test_extract_raises_when_no_tool_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    client = ProfileLlmClient(
        LlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    )
    with pytest.raises(LlmResponseError, match="tool_call"):
        client.extract(ProfileParseInput(raw_text="solo"))


def test_get_llm_client_returns_none_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    assert get_llm_client() is None


def test_get_llm_client_builds_client_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_API_KEY", "secret")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    client = get_llm_client()
    assert isinstance(client, ProfileLlmClient)


def test_extract_raises_value_error_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid_api_key"}})

    client = ProfileLlmClient(
        LlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    )
    with pytest.raises(LlmRequestError, match="401"):
        client.extract(ProfileParseInput(raw_text="solo"))


def test_extraction_ignores_unexpected_keys() -> None:
    extraction = ProfileExtraction.model_validate(
        {"team_size": "solo", "reasoning": "the developer said 我一个人", "extra": 1}
    )
    assert extraction.team_size == "solo"
