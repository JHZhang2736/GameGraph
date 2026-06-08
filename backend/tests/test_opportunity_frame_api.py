from fastapi.testclient import TestClient

from app.api.routes_opportunity import (
    get_opportunity_frame_llm,
    get_opportunity_repository,
)
from app.main import app
from app.services.opportunity_frame_llm import FrameSynthesis
from app.services.opportunity_service import GameDesignFacts, GameDimensions


class StubRepo:
    def fetch_game_dimensions(self):
        return [
            GameDimensions("game_vs", "横版割草", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, {"护符定制"}),
            GameDimensions("game_fps", "第一人称射击", {"类肉鸽"}, {"第一人称"}, {"低多边形"}, {"能力树"}),
        ]

    def fetch_game_design_facts(self, game_ids):
        rows = [
            GameDesignFacts("game_vs", ["护符定制"], ["紧张刺激"], ["低美术成本"], ["数值滚雪球"]),
            GameDesignFacts("game_fps", ["能力树"], ["爽快射击"], ["低多边形可控"], ["快速重开"]),
        ]
        return [r for r in rows if r.game_id in game_ids]


class StubLlm:
    def synthesize(self, profile, area, inputs):
        return FrameSynthesis(
            opportunity_area="第一人称生存割草",
            secondary_transformations=["叠加能力树"],
            forbidden_directions=["看似新颖但不可行：实时联网协作"],
            fit_reason="契合", risk_reason="美术成本", warnings=[],
        )


def _profile() -> dict:
    return {
        "id": "profile_1", "team_size": "solo", "time_budget": "三个月",
        "programming_ability": "强", "art_ability": "弱", "audio_ability": "弱",
        "content_production_ability": "有限", "liked_references": ["Hades"],
        "disliked_references_or_mechanics": ["联网多人"], "desired_player_experiences": ["短局"],
        "constraints": [{"id": "c1", "type": "hard", "statement": "不做联网多人"}],
    }


def _area() -> dict:
    return {
        "id": "opp|game_vs|sub|Perspective|第一人称",
        "anchor_game_id": "game_vs", "anchor_summary": "横版割草",
        "transformation": {"type": "substitute", "dimension": "Perspective",
                           "from_value": "横版2D", "to_value": "第一人称"},
        "existing_combination_count": 0,
        "evidence": {"anchor_game_id": "game_vs", "target_value_game_ids": ["game_fps"],
                     "combination_game_ids": []},
        "risk_posture": "challenging", "fit_reason": "契合短局", "risk_reason": "3D 抬高美术成本",
    }


def test_frame_endpoint_returns_frame() -> None:
    app.dependency_overrides[get_opportunity_repository] = lambda: StubRepo()
    app.dependency_overrides[get_opportunity_frame_llm] = lambda: StubLlm()
    try:
        client = TestClient(app)
        response = client.post("/opportunity/frame", json={"profile": _profile(), "area": _area()})
        assert response.status_code == 200
        body = response.json()
        assert body["developer_profile_id"] == "profile_1"
        assert body["recommended_transformations"][0] == "将 Perspective 从「横版2D」替代为「第一人称」"
        assert body["source_game_ids"] == ["game_vs", "game_fps"]
        assert any("违反硬约束" in x for x in body["forbidden_directions"])
    finally:
        app.dependency_overrides.clear()


def test_frame_endpoint_degrades_without_llm() -> None:
    app.dependency_overrides[get_opportunity_repository] = lambda: StubRepo()
    app.dependency_overrides[get_opportunity_frame_llm] = lambda: None
    try:
        client = TestClient(app)
        response = client.post("/opportunity/frame", json={"profile": _profile(), "area": _area()})
        assert response.status_code == 200
        body = response.json()
        assert any("未配置 LLM" in w for w in body["warnings"])
    finally:
        app.dependency_overrides.clear()


def test_frame_endpoint_rejects_malformed_request() -> None:
    app.dependency_overrides[get_opportunity_repository] = lambda: StubRepo()
    app.dependency_overrides[get_opportunity_frame_llm] = lambda: StubLlm()
    try:
        client = TestClient(app)
        response = client.post("/opportunity/frame", json={"profile": _profile()})  # 缺 area
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
