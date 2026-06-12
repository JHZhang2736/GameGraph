import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes_import import get_repository
from app.schemas.graph import GameSummary


class FakeRepo:
    def list_games(self) -> list[GameSummary]:
        return [
            GameSummary(
                id="game_hk",
                title="Hollow Knight",
                short_description="metroidvania",
            )
        ]


@pytest.fixture()
def client() -> TestClient:
    app.dependency_overrides[get_repository] = lambda: FakeRepo()
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def test_list_games_returns_summaries(client: TestClient) -> None:
    response = client.get("/games")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == "game_hk"
    assert body[0]["title"] == "Hollow Knight"
    assert body[0]["short_description"] == "metroidvania"
