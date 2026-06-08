from __future__ import annotations

from app.schemas.common import (
    ConfidenceLevel,
    EvidenceRef,
    QualityStatus,
    StrictBaseModel,
)


class GameSummary(StrictBaseModel):
    id: str
    title: str
    short_description: str
    confidence: ConfidenceLevel
    quality_status: QualityStatus


class GraphNodeDTO(StrictBaseModel):
    id: str
    label: str
    node_type: str


class GraphEdgeDTO(StrictBaseModel):
    id: str
    source: str
    target: str
    relation: str
    confidence: ConfidenceLevel | None = None
    quality_status: QualityStatus | None = None
    claim_id: str | None = None
    evidence: list[EvidenceRef] = []


class NeighborhoodResult(StrictBaseModel):
    focus: GraphNodeDTO
    nodes: list[GraphNodeDTO]
    edges: list[GraphEdgeDTO]
    truncated: bool = False


class NodeSearchHit(StrictBaseModel):
    id: str
    label: str
    node_type: str
