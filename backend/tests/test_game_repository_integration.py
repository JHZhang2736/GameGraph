import json
import os
from pathlib import Path

import pytest

from app.graph.connection import Neo4jSettings, create_driver
from app.graph.game_repository import GameRepository
from app.schemas.import_document import GameImportDocument

pytestmark = pytest.mark.integration


def animal_well_document() -> GameImportDocument:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "app" / "fixtures" / "games" / "animal_well.json"
    )
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    return GameImportDocument.model_validate(raw)


@pytest.fixture()
def driver():
    if "NEO4J_PASSWORD" not in os.environ:
        pytest.skip("NEO4J_PASSWORD not set; skipping Neo4j integration test")
    drv = create_driver(Neo4jSettings.from_env())
    try:
        drv.verify_connectivity()
    except Exception:
        pytest.skip("Neo4j is not reachable; skipping integration test")
    yield drv
    with drv.session() as session:
        session.run(
            "MATCH (g:Game {id: $id}) DETACH DELETE g", id="game_animal_well"
        )
    drv.close()


def test_upsert_then_read_round_trips(driver) -> None:
    repo = GameRepository(driver)
    document = animal_well_document()

    summary = repo.upsert_game(document)
    assert summary.game_id == "game_animal_well"

    read = repo.get_game("game_animal_well")
    assert read is not None
    assert read.candidate.id == "game_animal_well"
    assert read.profile.game_id == "game_animal_well"


def test_reimport_is_idempotent(driver) -> None:
    repo = GameRepository(driver)
    document = animal_well_document()

    repo.upsert_game(document)
    repo.upsert_game(document)

    mechanic_count = len(document.profile.main_mechanics)
    with driver.session() as session:
        record = session.run(
            "MATCH (g:Game {id: $id})-[r]->() RETURN count(r) AS edge_count",
            id="game_animal_well",
        ).single()
    assert record["edge_count"] > 0
    with driver.session() as session:
        mech = session.run(
            "MATCH (:Game {id: $id})-[r:HAS_MECHANIC]->() RETURN count(r) AS c",
            id="game_animal_well",
        ).single()
    assert mech["c"] == mechanic_count
