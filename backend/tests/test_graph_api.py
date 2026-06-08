import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes_graph import get_repository
from app.schemas.graph import NeighborhoodResult, NodeSearchHit


class FakeGraphRepo:
    def search_nodes(self, q: str, limit: int) -> list[NodeSearchHit]:
        return [NodeSearchHit(id="game_hk", label="Hollow Knight", node_type="Game")]

    def neighbors(self, node_id, hops, limit, rel_types):  # used in Task 4
        return NeighborhoodResult(
            focus={"id": node_id, "label": node_id, "node_type": "Game"},
            nodes=[],
            edges=[],
            truncated=False,
        )


@pytest.fixture()
def client() -> TestClient:
    app.dependency_overrides[get_repository] = lambda: FakeGraphRepo()
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def test_search_returns_hits(client: TestClient) -> None:
    response = client.get("/graph/search", params={"q": "hollow"})
    assert response.status_code == 200
    assert response.json()[0]["node_type"] == "Game"
