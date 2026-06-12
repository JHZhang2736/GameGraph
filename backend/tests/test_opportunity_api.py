from fastapi.testclient import TestClient

from app.api.routes_opportunity import get_opportunity_repository, get_opportunity_llm
from tests.sse_helpers import sse_result
from app.main import app
from app.schemas.opportunity import RiskPosture
from app.services.opportunity_llm import OpportunityJudgment, OpportunityJudgmentBatch
from app.services.opportunity_service import GameDimensions


class StubRepo:
    def fetch_game_dimensions(self) -> list[GameDimensions]:
        # 使用能触发协同规则的真实词汇，确保 enumerate_opportunities 产生 recipe 候选：
        # game_perma 有「永久死亡」(高方差失败源)；game_party 有「共享账户」(社交放大器)。
        # 规则 social_high_variance_comedy (高方差失败源 × 社交放大器 → 欢乐混乱) 被命中。
        return [
            GameDimensions("game_perma", "肉鸽幸存者", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, {"永久死亡"}),
            GameDimensions("game_party", "派对合作", {"派对游戏"}, {"第三人称"}, {"低多边形"}, {"共享账户"}),
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
        "disliked_references_or_mechanics": ["联网多人"], "desired_player_experiences": ["欢乐混乱"],
        "constraints": [{"id": "c1", "type": "hard", "statement": "不做联网多人"}],
    }


def test_match_endpoint_returns_areas() -> None:
    app.dependency_overrides[get_opportunity_repository] = lambda: StubRepo()
    app.dependency_overrides[get_opportunity_llm] = lambda: StubLlm()
    try:
        client = TestClient(app)
        response = client.post("/opportunity/match", json={"profile": _profile_payload(), "seen_ids": []})
        assert response.status_code == 200
        body = sse_result(response)
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
        assert sse_result(response)["profile_id"] == "profile_1"
    finally:
        app.dependency_overrides.clear()
