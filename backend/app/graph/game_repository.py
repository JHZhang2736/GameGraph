from __future__ import annotations

from neo4j import Driver

from app.schemas.graph import GameSummary
from app.schemas.import_document import GameImportDocument
from app.services.import_service import (
    EdgeMerge,
    GraphWritePlan,
    ImportSummary,
    NodeMerge,
    PROFILE_LIST_EDGES,
    build_graph_write_plan,
    summarize,
)

# 允许写入的 (rel_type -> 目标 label) 白名单，防止动态 Cypher 注入
_ALLOWED_EDGES: dict[str, str] = {
    rel_type: label for rel_type, label in PROFILE_LIST_EDGES.values()
}
_ALLOWED_EDGES["TAGGED"] = "ReferenceTag"
_ALLOWED_EDGES["CLAIM"] = "Concept"

_ALLOWED_NODE_LABELS = {"Game", *_ALLOWED_EDGES.values()}

# 节点 key 的字段名也会被插值进 Cypher，限制为已知常量名以防注入
_ALLOWED_KEY_FIELDS = {"id", "name"}


class GameRepository:
    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def upsert_game(self, document: GameImportDocument) -> ImportSummary:
        plan = build_graph_write_plan(document)
        with self._driver.session() as session:
            session.execute_write(self._write_plan, plan)
        return summarize(document)

    def list_games(self) -> list[GameSummary]:
        with self._driver.session() as session:
            rows = session.execute_read(self._read_games)
        return [GameSummary(**row) for row in rows]

    @staticmethod
    def _read_games(tx) -> list[dict]:
        result = tx.run(
            "MATCH (g:Game) RETURN g.id AS id, g.title AS title, "
            "g.short_description AS short_description, g.confidence AS confidence, "
            "g.quality_status AS quality_status ORDER BY g.title"
        )
        return [dict(record) for record in result]

    def get_game(self, game_id: str) -> GameImportDocument | None:
        with self._driver.session() as session:
            record = session.execute_read(self._read_game, game_id)
        if record is None:
            return None
        return GameImportDocument.model_validate_json(record)

    @staticmethod
    def _write_plan(tx, plan: GraphWritePlan) -> None:
        # 1) 幂等：先删该 Game 的全部出边
        tx.run(
            "MATCH (g:Game {id: $game_id})-[r]->() DELETE r",
            game_id=plan.game_id,
        )
        # 2) MERGE 节点
        for node in plan.nodes:
            _validate_node(node)
            (key_field, key_value), = node.key.items()
            tx.run(
                f"MERGE (n:{node.label} {{{key_field}: $key}}) SET n += $props",
                key=key_value,
                props=node.properties,
            )
        # 3) MERGE 边
        for edge in plan.edges:
            _validate_edge(edge)
            (from_field, from_value), = edge.from_key.items()
            (to_field, to_value), = edge.to_key.items()
            tx.run(
                f"MATCH (a:{edge.from_label} {{{from_field}: $from_value}}) "
                f"MERGE (b:{edge.to_label} {{{to_field}: $to_value}}) "
                f"MERGE (a)-[r:{edge.rel_type}]->(b) SET r += $props",
                from_value=from_value,
                to_value=to_value,
                props=edge.properties,
            )

    @staticmethod
    def _read_game(tx, game_id: str) -> str | None:
        result = tx.run(
            "MATCH (g:Game {id: $game_id}) RETURN g.document_json AS document_json",
            game_id=game_id,
        )
        record = result.single()
        if record is None:
            return None
        return record["document_json"]


def _validate_key(key: dict[str, str], field_label: str) -> None:
    if len(key) != 1:
        raise ValueError(f"{field_label} must contain exactly one field")
    (field_name,) = key
    if field_name not in _ALLOWED_KEY_FIELDS:
        raise ValueError(f"Unexpected key field: {field_name}")


def _validate_node(node: NodeMerge) -> None:
    if node.label not in _ALLOWED_NODE_LABELS:
        raise ValueError(f"Unexpected node label: {node.label}")
    _validate_key(node.key, "NodeMerge.key")


def _validate_edge(edge: EdgeMerge) -> None:
    if edge.from_label not in _ALLOWED_NODE_LABELS:
        raise ValueError(f"Unexpected from_label: {edge.from_label}")
    if _ALLOWED_EDGES.get(edge.rel_type) != edge.to_label:
        raise ValueError(f"Unexpected edge: {edge.rel_type} -> {edge.to_label}")
    _validate_key(edge.from_key, "EdgeMerge.from_key")
    _validate_key(edge.to_key, "EdgeMerge.to_key")
