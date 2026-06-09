from fastapi.testclient import TestClient

from app.api.routes_opportunity import get_opportunity_repository, get_opportunity_llm
from app.main import app
from app.schemas.opportunity import RiskPosture
from app.services.opportunity_llm import OpportunityJudgment, OpportunityJudgmentBatch
from app.services.opportunity_service import GameDimensions


class StubRepo:
    def fetch_game_dimensions(self) -> list[GameDimensions]:
        return [
            GameDimensions("game_vs", "横版割草", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, {"护符定制"}),
            GameDimensions("game_fps", "第一人称射击", {"射击"}, {"第一人称"}, {"低多边形"}, {"能力树"}),
        ]


class StubLlm:
    def judge(self, profile, candidates):
        return OpportunityJudgmentBatch(
            judgments=[
                OpportunityJudgment(
                    candidate_id=candidates[0].id, decision="keep",
                    risk_posture=RiskPosture.BALANCED, fit_reason="契合", risk_reason="可控",
                )
            ],
            warnings=[],
        )


def _profile_payload() -> dict:
    return {
        "id": "profile_1", "team_size": "solo", "time_budget": "三个月",
        "programming_ability": "强", "art_ability": "弱", "audio_ability": "弱",
        "content_production_ability": "有限", "liked_references": ["Hades"],
        "disliked_references_or_mechanics": ["联网多人"], "desired_player_experiences": ["短局"],
        "constraints": [{"id": "c1", "type": "hard", "statement": "不做联网多人"}],
    }


def test_match_endpoint_returns_areas() -> None:
    app.dependency_overrides[get_opportunity_repository] = lambda: StubRepo()
    app.dependency_overrides[get_opportunity_llm] = lambda: StubLlm()
    try:
        client = TestClient(app)
        response = client.post("/opportunity/match", json={"profile": _profile_payload(), "seen_ids": []})
        assert response.status_code == 200
        body = response.json()
        assert body["profile_id"] == "profile_1"
        assert len(body["areas"]) >= 1
        assert body["areas"][0]["risk_posture"] == "balanced"
    finally:
        app.dependency_overrides.clear()


def test_match_endpoint_rejects_bare_profile_body() -> None:
    app.dependency_overrides[get_opportunity_repository] = lambda: StubRepo()
    app.dependency_overrides[get_opportunity_llm] = lambda: StubLlm()
    try:
        client = TestClient(app)
        resp = client.post("/opportunity/match", json=_profile_payload())
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_match_endpoint_rejects_malformed_profile() -> None:
    app.dependency_overrides[get_opportunity_repository] = lambda: StubRepo()
    app.dependency_overrides[get_opportunity_llm] = lambda: StubLlm()
    try:
        client = TestClient(app)
        response = client.post("/opportunity/match", json={"profile": {"id": "profile_1"}, "seen_ids": []})  # 缺必填字段
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_match_endpoint_accepts_profile_without_optional_lists() -> None:
    # 复现 bug：只填 6 个必填标量、可选列表全部省略 → 应 200，而非 422
    payload = {
        "id": "profile_1", "team_size": "solo", "time_budget": "三个月",
        "programming_ability": "强", "art_ability": "弱", "audio_ability": "弱",
        "content_production_ability": "有限",
    }
    app.dependency_overrides[get_opportunity_repository] = lambda: StubRepo()
    app.dependency_overrides[get_opportunity_llm] = lambda: StubLlm()
    try:
        client = TestClient(app)
        response = client.post("/opportunity/match", json={"profile": payload, "seen_ids": []})
        assert response.status_code == 200
        assert response.json()["profile_id"] == "profile_1"
    finally:
        app.dependency_overrides.clear()
