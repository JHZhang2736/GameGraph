import json
import os
from pathlib import Path

import pytest

from app.graph.connection import Neo4jSettings, create_driver
from app.graph.game_repository import GameRepository
from app.graph.opportunity_repository import OpportunityRepository
from app.schemas.import_document import GameImportDocument

pytestmark = pytest.mark.integration


def _document(name: str) -> GameImportDocument:
    path = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "games" / f"{name}.json"
    return GameImportDocument.model_validate(json.loads(path.read_text(encoding="utf-8")))


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
        session.run("MATCH (g:Game {id: $id}) DETACH DELETE g", id="game_animal_well")
    drv.close()


def test_fetch_game_dimensions_returns_anchor_values(driver) -> None:
    GameRepository(driver).upsert_game(_document("animal_well"))
    rows = OpportunityRepository(driver).fetch_game_dimensions()
    aw = next(r for r in rows if r.game_id == "game_animal_well")
    assert aw.summary
    assert "类银河城" in aw.genres
    assert "多用途道具" in aw.mechanics
    assert aw.perspectives  # 非空


def test_fetch_game_design_facts_returns_profile_lists(driver) -> None:
    GameRepository(driver).upsert_game(_document("animal_well"))
    facts = OpportunityRepository(driver).fetch_game_design_facts(["game_animal_well"])
    aw = next(f for f in facts if f.game_id == "game_animal_well")
    assert aw.mechanics       # HAS_MECHANIC 非空
    assert aw.experiences     # DELIVERS_EXPERIENCE 非空
    assert aw.constraints     # CONSTRAINED_BY 非空
    assert aw.innovation_patterns  # USES_INNOVATION 非空


@pytest.fixture()
def driver_gwyf(driver):
    """Extend the base driver fixture with gamble_with_your_friends cleanup."""
    yield driver
    with driver.session() as session:
        session.run(
            "MATCH (g:Game {id: $id}) DETACH DELETE g",
            id="game_gamble_with_your_friends",
        )


def test_fetch_game_dimensions_returns_theme_and_game_feel(driver_gwyf) -> None:
    GameRepository(driver_gwyf).upsert_game(_document("gamble_with_your_friends"))
    rows = OpportunityRepository(driver_gwyf).fetch_game_dimensions()
    gwyf = next(r for r in rows if r.game_id == "game_gamble_with_your_friends")
    assert isinstance(gwyf.theme, set) and gwyf.theme        # HAS_THEME 非空
    assert isinstance(gwyf.game_feel, set) and gwyf.game_feel  # HAS_GAME_FEEL 非空
