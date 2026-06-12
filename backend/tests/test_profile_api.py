import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes_profile import get_llm_client
from app.schemas.common import ConstraintType
from app.services.profile_llm import ExtractedConstraint, ExtractedSource, ProfileExtraction
from tests.sse_helpers import sse_result


class FakeClient:
    def extract(self, input_data) -> ProfileExtraction:
        return ProfileExtraction(
            team_size="solo",
            time_budget="three month prototype",
            programming_ability="strong",
            art_ability="weak",
            content_production_ability="limited",
            liked_references=["Hades"],
            desired_player_experiences=["short runs"],
            constraints=[
                ExtractedConstraint(type=ConstraintType.HARD, statement="Do not require online multiplayer.")
            ],
            field_sources=[
                ExtractedSource(field="team_size", source_text="我一个人做")
            ],
            warnings=[],
        )


@pytest.fixture()
def client() -> TestClient:
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def test_parse_uses_llm_client_when_present(client: TestClient) -> None:
    app.dependency_overrides[get_llm_client] = lambda: FakeClient()
    response = client.post("/profile/parse", json={"raw_text": "我一个人做游戏"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = sse_result(response)
    assert body["draft"]["team_size"] == "solo"
    assert body["draft"]["is_complete"] is True
    assert body["draft"]["audio_ability"] == "basic"


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


def test_parse_rejects_blank_text_with_422(client: TestClient) -> None:
    app.dependency_overrides[get_llm_client] = lambda: None
    response = client.post("/profile/parse", json={"raw_text": "   "})
    assert response.status_code == 422
