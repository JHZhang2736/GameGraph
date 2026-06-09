import json

import httpx
import pytest

from app.schemas.artifacts import OpportunityFrame
from app.services.concept_llm import (
    ConceptGenerationBatch,
    ConceptLlmClient,
    build_concept_tool_schema,
    get_concept_llm_client,
)
from app.services.opportunity_llm import LlmSettings


def _settings() -> LlmSettings:
    return LlmSettings(base_url="https://example.test/v1", api_key="secret", model="m", timeout=5.0)


def _frame() -> OpportunityFrame:
    return OpportunityFrame(
        id="frame|opp|game_vs|sub|Perspective|第一人称",
        developer_profile_id="profile_1",
        opportunity_area="第一人称生存割草",
        source_game_ids=["game_vs", "game_fps"],
        related_mechanics=["护符定制", "能力树"],
        related_player_experiences=["紧张刺激"],
        related_constraints=["低美术成本"],
        related_innovation_patterns=["数值滚雪球"],
        recommended_transformations=["将 Perspective 从「横版2D」替代为「第一人称」"],
        forbidden_directions=["违反硬约束：不做联网多人"],
        evidence_path=["锚点 game_vs 提供成熟配方"],
        fit_reason="契合短局",
        risk_reason="3D 抬高美术成本",
    )


def _draft_dict(title: str) -> dict:
    return {
        "title": title,
        "one_sentence_concept": "用护符构筑在第一人称视角下扛过夜晚的兽潮",
        "core_fantasy": "孤身在黑暗中靠 build 滚雪球翻盘",
        "core_loop": "探索→拾取护符→构筑→应对兽潮→升级",
        "main_player_decisions": ["先拿哪枚护符", "何时冒险深入"],
        "main_mechanics": ["护符定制", "能力树"],
        "reference_sources": ["game_vs", "game_fps"],
        "difference_from_references": "把横版割草搬到第一人称的近身紧张视野",
        "fit_reason": "契合 solo 程序强、短局",
        "production_risks": ["第一人称美术成本"],
        "design_risks": ["视角切换削弱割草爽快"],
        "novelty_reason": "第一人称割草在策展库稀缺",
        "suggested_prototype_scope": "单关卡 + 3 枚护符 + 一波兽潮",
    }


def _arguments() -> str:
    return json.dumps({"concepts": [_draft_dict(f"概念{i}") for i in (1, 2, 3)]})


def test_build_concept_tool_schema_exposes_function_name() -> None:
    tools = build_concept_tool_schema()
    assert tools[0]["function"]["name"] == "emit_concept_cards"
    assert tools[0]["function"]["parameters"]["properties"]


def test_generate_posts_request_and_parses() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"tool_calls": [
            {"function": {"name": "emit_concept_cards", "arguments": _arguments()}}
        ]}}]})

    client = ConceptLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    batch = client.generate(_frame())

    assert isinstance(batch, ConceptGenerationBatch)
    assert len(batch.concepts) == 3
    assert batch.concepts[0].title == "概念1"
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["body"]["tool_choice"]["function"]["name"] == "emit_concept_cards"
    assert seen["body"]["messages"][0]["role"] == "system"
    assert "不做联网多人" in seen["body"]["messages"][1]["content"]


def test_generate_raises_when_no_tool_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    client = ConceptLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError, match="tool_call"):
        client.generate(_frame())


def test_generate_raises_value_error_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid_api_key"}})

    client = ConceptLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError, match="401"):
        client.generate(_frame())


def test_get_client_returns_none_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    assert get_concept_llm_client() is None


def test_generate_raises_on_malformed_tool_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"tool_calls": [
            {"id": "call_1"}  # 缺 "function" 键
        ]}}]})

    client = ConceptLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError, match="Malformed tool_call"):
        client.generate(_frame())
