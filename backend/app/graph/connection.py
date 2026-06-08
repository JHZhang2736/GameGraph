from __future__ import annotations

import os
from dataclasses import dataclass

from neo4j import Driver, GraphDatabase


@dataclass(frozen=True)
class Neo4jSettings:
    uri: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "Neo4jSettings":
        return cls(
            uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            user=os.environ.get("NEO4J_USER", "neo4j"),
            password=os.environ["NEO4J_PASSWORD"],
        )


def create_driver(settings: Neo4jSettings | None = None) -> Driver:
    resolved = settings or Neo4jSettings.from_env()
    return GraphDatabase.driver(resolved.uri, auth=(resolved.user, resolved.password))
