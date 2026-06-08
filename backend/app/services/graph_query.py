from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.schemas.common import EvidenceRef
from app.schemas.graph import GraphEdgeDTO, GraphNodeDTO, NeighborhoodResult


@dataclass
class NeighborRow:
    rel_type: str
    rel_props: dict = field(default_factory=dict)
    neighbor_label: str = ""
    neighbor_key: str = ""
    neighbor_display: str = ""


def _evidence(rel_props: dict) -> list[EvidenceRef]:
    raw = rel_props.get("evidence_json")
    if not raw:
        return []
    return [EvidenceRef.model_validate(item) for item in json.loads(raw)]


def _edge(focus_id: str, row: NeighborRow) -> GraphEdgeDTO:
    props = row.rel_props
    claim_id = props.get("claim_id")
    edge_id = claim_id or f"{focus_id}-{row.rel_type}-{row.neighbor_key}"
    return GraphEdgeDTO(
        id=edge_id,
        source=focus_id,
        target=row.neighbor_key,
        relation=props.get("relation") or row.rel_type,
        confidence=props.get("confidence"),
        quality_status=props.get("quality_status"),
        claim_id=claim_id,
        evidence=_evidence(props),
    )


def build_neighborhood(
    focus: dict, rows: list[NeighborRow], limit: int
) -> NeighborhoodResult:
    capped = rows[:limit]
    nodes = [
        GraphNodeDTO(
            id=row.neighbor_key,
            label=row.neighbor_display,
            node_type=row.neighbor_label,
        )
        for row in capped
    ]
    edges = [_edge(focus["id"], row) for row in capped]
    return NeighborhoodResult(
        focus=GraphNodeDTO(**focus),
        nodes=nodes,
        edges=edges,
        truncated=len(rows) > limit,
    )
