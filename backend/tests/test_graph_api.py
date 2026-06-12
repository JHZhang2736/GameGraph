import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes_graph import get_repository
from app.schemas.graph import NeighborhoodResult, NodeSearchHit


class FakeGraphRepo:
    def list_mechanics(self) -> list[str]:
        return ["共享账户", "永久死亡", "老虎机"]

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


def test_list_mechanics_returns_names(client: TestClient) -> None:
    response = client.get("/graph/mechanics")
    assert response.status_code == 200
    assert response.json() == ["共享账户", "永久死亡", "老虎机"]


def test_search_returns_hits(client: TestClient) -> None:
    response = client.get("/graph/search", params={"q": "hollow"})
    assert response.status_code == 200
    assert response.json()[0]["node_type"] == "Game"


def test_neighbors_returns_bounded_subgraph(client: TestClient) -> None:
    response = client.get("/graph/neighbors", params={"node_id": "game_hk"})
    assert response.status_code == 200
    body = response.json()
    assert body["focus"]["id"] == "game_hk"
    assert body["truncated"] is False


def test_neighbors_parses_rel_types_csv(client: TestClient) -> None:
    response = client.get(
        "/graph/neighbors",
        params={"node_id": "game_hk", "rel_types": "HAS_MECHANIC,CLAIM"},
    )
    assert response.status_code == 200
