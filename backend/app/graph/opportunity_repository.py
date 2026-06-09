from __future__ import annotations

from neo4j import Driver

from app.services.opportunity_service import GameDesignFacts, GameDimensions

_FETCH_QUERY = """
MATCH (g:Game)
RETURN g.id AS game_id,
       coalesce(g.one_sentence_summary, g.title, g.id) AS summary,
       [(g)-[:HAS_GENRE]->(x) | x.name] AS genres,
       [(g)-[:HAS_PERSPECTIVE]->(x) | x.name] AS perspectives,
       [(g)-[:HAS_ART_STYLE]->(x) | x.name] AS art_styles,
       [(g)-[:HAS_MECHANIC]->(x) | x.name] AS mechanics
"""

_FACTS_QUERY = """
MATCH (g:Game) WHERE g.id IN $game_ids
RETURN g.id AS game_id,
       [(g)-[:HAS_MECHANIC]->(x)        | x.name] AS mechanics,
       [(g)-[:DELIVERS_EXPERIENCE]->(x) | x.name] AS experiences,
       [(g)-[:CONSTRAINED_BY]->(x)      | x.name] AS constraints,
       [(g)-[:USES_INNOVATION]->(x)     | x.name] AS innovation_patterns
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
            if record["game_id"] is not None
        ]

    def fetch_game_design_facts(self, game_ids: list[str]) -> list[GameDesignFacts]:
        with self._driver.session() as session:
            return session.execute_read(self._read_facts, game_ids)

    @staticmethod
    def _read_facts(tx, game_ids: list[str]) -> list[GameDesignFacts]:
        result = tx.run(_FACTS_QUERY, game_ids=game_ids)
        return [
            GameDesignFacts(
                game_id=record["game_id"],
                mechanics=list(record["mechanics"]),
                experiences=list(record["experiences"]),
                constraints=list(record["constraints"]),
                innovation_patterns=list(record["innovation_patterns"]),
            )
            for record in result
            if record["game_id"] is not None
        ]
