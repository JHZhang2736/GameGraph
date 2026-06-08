import json

import httpx
import pytest

from app.schemas.artifacts import DeveloperConstraint, DeveloperProfile
from app.schemas.common import ConstraintType
from app.schemas.opportunity import (
    CandidateOpportunityArea,
    OpportunityArea,
    OpportunityEvidence,
    RiskPosture,
    Transformation,
    TransformationType,
)
from app.services.opportunity_frame_llm import (
    FrameInputs,
    FrameSynthesis,
    OpportunityFrameLlmClient,
    build_frame_tool_schema,
    get_opportunity_frame_llm_client,
)
from app.services.opportunity_llm import LlmSettings


def _settings() -> LlmSettings:
    return LlmSettings(base_url="https://example.test/v1", api_key="secret", model="m", timeout=5.0)


def _profile() -> DeveloperProfile:
    return DeveloperProfile(
        id="profile_1", team_size="solo", time_budget="三个月",
        programming_ability="强", art_ability="弱", audio_ability="弱",
        content_production_ability="有限", liked_references=["Hades"],
        disliked_references_or_mechanics=["联网多人"], desired_player_experiences=["短局"],
        constraints=[DeveloperConstraint(id="c1", type=ConstraintType.HARD, statement="不做联网多人")],
    )


def _area() -> OpportunityArea:
    return OpportunityArea(
        id="opp|game_vs|sub|Perspective|第一人称",
        anchor_game_id="game_vs", anchor_summary="横版割草",
        transformation=Transformation(type=TransformationType.SUBSTITUTE, dimension="Perspective",
                                      from_value="横版2D", to_value="第一人称"),
        existing_combination_count=0,
        evidence=OpportunityEvidence(anchor_game_id="game_vs", target_value_game_ids=["game_fps"],
                                     combination_game_ids=[]),
        risk_posture=RiskPosture.CHALLENGING, fit_reason="契合短局", risk_reason="3D 抬高美术成本",
    )


def _pool() -> list[CandidateOpportunityArea]:
    return [
        CandidateOpportunityArea(
            id="opp|game_vs|comb|Mechanic|能力树",
            anchor_game_id="game_vs", anchor_summary="横版割草",
            transformation=Transformation(type=TransformationType.COMBINE, dimension="Mechanic",
                                          from_value=None, to_value="能力树"),
            existing_combination_count=1,
            evidence=OpportunityEvidence(anchor_game_id="game_vs", target_value_game_ids=["game_fps"],
                                         combination_game_ids=["game_fps"]),
        )
    ]


def _inputs() -> FrameInputs:
    return FrameInputs(
        related_mechanics=["护符定制", "能力树"],
        related_player_experiences=["紧张刺激"],
        related_constraints=["低美术成本"],
        related_innovation_patterns=["数值滚雪球"],
        secondary_pool=_pool(),
    )


def _arguments() -> str:
    return json.dumps(
        {
            "opportunity_area": "第一人称生存割草",
            "secondary_transformations": ["叠加能力树以延长单局成长"],
            "forbidden_directions": ["看似新颖但不可行：实时联网协作割草"],
            "fit_reason": "契合 solo 程序强、短局快节奏",
            "risk_reason": "第一人称抬高美术与运动眩晕风险",
            "warnings": [],
        }
    )


def test_build_frame_tool_schema_exposes_function_name() -> None:
    tools = build_frame_tool_schema()
    assert tools[0]["function"]["name"] == "emit_opportunity_frame"
    assert tools[0]["function"]["parameters"]["properties"]


def test_synthesize_posts_request_and_parses() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"tool_calls": [
            {"function": {"name": "emit_opportunity_frame", "arguments": _arguments()}}
        ]}}]})

    client = OpportunityFrameLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    synth = client.synthesize(_profile(), _area(), _inputs())

    assert isinstance(synth, FrameSynthesis)
    assert synth.opportunity_area == "第一人称生存割草"
    assert synth.secondary_transformations == ["叠加能力树以延长单局成长"]
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["body"]["tool_choice"]["function"]["name"] == "emit_opportunity_frame"
    assert seen["body"]["messages"][0]["role"] == "system"


def test_synthesize_raises_when_no_tool_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    client = OpportunityFrameLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError, match="tool_call"):
        client.synthesize(_profile(), _area(), _inputs())


def test_synthesize_raises_value_error_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid_api_key"}})

    client = OpportunityFrameLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError, match="401"):
        client.synthesize(_profile(), _area(), _inputs())


def test_get_client_returns_none_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    assert get_opportunity_frame_llm_client() is None
