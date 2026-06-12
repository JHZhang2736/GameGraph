from __future__ import annotations

from app.schemas.common import StrictBaseModel


class GameSummary(StrictBaseModel):
    id: str
    title: str
    short_description: str


class GraphNodeDTO(StrictBaseModel):
    id: str
    label: str
    node_type: str


class GraphEdgeDTO(StrictBaseModel):
    id: str
    source: str
    target: str
    relation: str
    claim_id: str | None = None


class NeighborhoodResult(StrictBaseModel):
    focus: GraphNodeDTO
    nodes: list[GraphNodeDTO]
    edges: list[GraphEdgeDTO]
    truncated: bool = False


class NodeSearchHit(StrictBaseModel):
    id: str
    label: str
    node_type: str
