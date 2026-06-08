import json

import httpx
import pytest

from app.schemas.opportunity import (
    CandidateOpportunityArea,
    OpportunityEvidence,
    Transformation,
    TransformationType,
)
from app.schemas.artifacts import DeveloperConstraint, DeveloperProfile
from app.schemas.common import ConstraintType
from app.services.opportunity_llm import (
    LlmSettings,
    OpportunityJudgmentBatch,
    OpportunityLlmClient,
    build_tool_schema,
    get_opportunity_llm_client,
)


def _settings() -> LlmSettings:
    return LlmSettings(base_url="https://example.test/v1", api_key="secret", model="m", timeout=5.0)


def _profile() -> DeveloperProfile:
    return DeveloperProfile(
        id="profile_1",
        team_size="solo",
        time_budget="三个月",
        programming_ability="强",
        art_ability="弱",
        audio_ability="弱",
        content_production_ability="有限",
        liked_references=["Hades"],
        disliked_references_or_mechanics=["联网多人"],
        desired_player_experiences=["短局"],
        constraints=[
            DeveloperConstraint(id="c1", type=ConstraintType.HARD, statement="不做联网多人")
        ],
    )


def _candidate() -> CandidateOpportunityArea:
    return CandidateOpportunityArea(
        id="opp_1",
        anchor_game_id="game_vs",
        anchor_summary="横版割草",
        transformation=Transformation(
            type=TransformationType.SUBSTITUTE,
            dimension="Perspective",
            from_value="横版2D",
            to_value="第一人称",
        ),
        existing_combination_count=0,
        evidence=OpportunityEvidence(
            anchor_game_id="game_vs", target_value_game_ids=["game_fps"], combination_game_ids=[]
        ),
    )


def _arguments() -> str:
    return json.dumps(
        {
            "judgments": [
                {
                    "candidate_id": "opp_1",
                    "decision": "keep",
                    "risk_posture": "challenging",
                    "fit_reason": "契合短局快节奏",
                    "risk_reason": "3D 抬高美术成本",
                }
            ],
            "warnings": [],
        }
    )


def test_build_tool_schema_exposes_function_name() -> None:
    tools = build_tool_schema()
    assert tools[0]["function"]["name"] == "emit_opportunity_judgments"
    assert "parameters" in tools[0]["function"]


def test_judge_posts_request_and_parses_batch() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"tool_calls": [
                        {"function": {"name": "emit_opportunity_judgments", "arguments": _arguments()}}
                    ]}}
                ]
            },
        )

    client = OpportunityLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    batch = client.judge(_profile(), [_candidate()])

    assert isinstance(batch, OpportunityJudgmentBatch)
    assert batch.judgments[0].candidate_id == "opp_1"
    assert batch.judgments[0].decision == "keep"
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["body"]["tool_choice"]["function"]["name"] == "emit_opportunity_judgments"


def test_judge_raises_when_no_tool_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    client = OpportunityLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError, match="tool_call"):
        client.judge(_profile(), [_candidate()])


def test_get_client_returns_none_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    assert get_opportunity_llm_client() is None
