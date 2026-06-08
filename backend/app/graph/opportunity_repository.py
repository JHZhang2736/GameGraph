from __future__ import annotations

from neo4j import Driver

from app.services.opportunity_service import GameDimensions

_FETCH_QUERY = """
MATCH (g:Game)
RETURN g.id AS game_id,
       coalesce(g.one_sentence_summary, '') AS summary,
       [(g)-[:HAS_GENRE]->(x) | x.name] AS genres,
       [(g)-[:HAS_PERSPECTIVE]->(x) | x.name] AS perspectives,
       [(g)-[:HAS_ART_STYLE]->(x) | x.name] AS art_styles,
       [(g)-[:HAS_MECHANIC]->(x) | x.name] AS mechanics
"""


class OpportunityRepository:
    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def fetch_game_dimensions(self) -> list[GameDimensions]:
        with self._driver.session() as session:
            return session.execute_read(self._read_dimensions)

    @staticmethod
    def _read_dimensions(tx) -> list[GameDimensions]:
        result = tx.run(_FETCH_QUERY)
        return [
            GameDimensions(
                game_id=record["game_id"],
                summary=record["summary"],
                genres=set(record["genres"]),
                perspectives=set(record["perspectives"]),
                art_styles=set(record["art_styles"]),
                mechanics=set(record["mechanics"]),
            )
            for record in result
        ]
