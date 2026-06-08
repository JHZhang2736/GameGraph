import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes_import import get_repository
from app.schemas.import_document import GameImportDocument
from app.services.import_service import ImportSummary, summarize


class FakeRepository:
    def __init__(self) -> None:
        self.saved: dict[str, GameImportDocument] = {}

    def upsert_game(self, document: GameImportDocument) -> ImportSummary:
        self.saved[document.candidate.id] = document
        return summarize(document)

    def get_game(self, game_id: str) -> GameImportDocument | None:
        return self.saved.get(game_id)


@pytest.fixture()
def fake_repo() -> FakeRepository:
    return FakeRepository()


@pytest.fixture()
def client(fake_repo: FakeRepository) -> TestClient:
    app.dependency_overrides[get_repository] = lambda: fake_repo
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def animal_well_payload() -> dict:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "app" / "fixtures" / "games" / "animal_well.json"
    )
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_import_game_returns_summary(client: TestClient) -> None:
    response = client.post("/import/game", json=animal_well_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["game_id"] == "game_animal_well"
    assert body["mechanics_written"] == 7
    assert body["tags_written"] == 3
    assert body["claims_written"] == 2


def test_import_game_rejects_invalid_schema_with_422(client: TestClient) -> None:
    payload = animal_well_payload()
    payload["profile"]["main_mechanics"] = []
    response = client.post("/import/game", json=payload)
    assert response.status_code == 422


def test_import_game_rejects_contract_violation_with_409(client: TestClient) -> None:
    payload = animal_well_payload()
    payload["profile"]["game_id"] = "game_other"
    response = client.post("/import/game", json=payload)
    assert response.status_code == 409
    assert "profile.game_id must match candidate.id" in response.json()["detail"]


def test_get_game_returns_imported_document(client: TestClient) -> None:
    client.post("/import/game", json=animal_well_payload())
    response = client.get("/games/game_animal_well")
    assert response.status_code == 200
    assert response.json()["candidate"]["id"] == "game_animal_well"


def test_get_game_returns_404_when_missing(client: TestClient) -> None:
    response = client.get("/games/game_unknown")
    assert response.status_code == 404
