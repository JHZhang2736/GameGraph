from app.services.graph_query import NeighborRow, build_neighborhood


def _focus() -> dict:
    return {"id": "game_hk", "label": "Hollow Knight", "node_type": "Game"}


def test_structural_edge_has_no_confidence_and_uses_rel_type_as_relation():
    rows = [
        NeighborRow(
            rel_type="HAS_MECHANIC",
            rel_props={},
            neighbor_label="Mechanic",
            neighbor_key="precise platforming",
            neighbor_display="precise platforming",
            source_key="game_hk",
            target_key="precise platforming",
        )
    ]
    result = build_neighborhood(_focus(), rows, limit=150)
    assert result.focus.id == "game_hk"
    assert len(result.nodes) == 1
    assert result.nodes[0].node_type == "Mechanic"
    assert result.nodes[0].id == "precise platforming"
    edge = result.edges[0]
    assert edge.relation == "HAS_MECHANIC"
    assert edge.confidence is None
    assert edge.source == "game_hk"
    assert edge.target == "precise platforming"
    assert result.truncated is False


def test_claim_edge_carries_relation_confidence_and_evidence():
    rows = [
        NeighborRow(
            rel_type="CLAIM",
            rel_props={
                "claim_id": "claim_1",
                "relation": "reinforces",
                "confidence": "low",
                "quality_status": "weak_evidence",
                "evidence_json": '[{"title":"GDC talk","notes":"n","url":"http://x"}]',
            },
            neighbor_label="Concept",
            neighbor_key="exploration flow",
            neighbor_display="exploration flow",
            source_key="game_hk",
            target_key="exploration flow",
        )
    ]
    edge = build_neighborhood(_focus(), rows, limit=150).edges[0]
    assert edge.relation == "reinforces"
    assert edge.confidence == "low"
    assert edge.quality_status == "weak_evidence"
    assert edge.claim_id == "claim_1"
    assert edge.evidence[0].title == "GDC talk"
    assert edge.id == "claim_1"


def test_incoming_edge_keeps_real_direction_when_focus_is_target():
    # Focus is a Mechanic; the related Game points INTO it (Game)-[HAS_MECHANIC]->(Mechanic).
    # The edge must keep its real direction (game -> mechanic), not focus -> neighbor.
    focus = {"id": "牌组构筑", "label": "牌组构筑", "node_type": "Mechanic"}
    rows = [
        NeighborRow(
            rel_type="HAS_MECHANIC",
            rel_props={},
            neighbor_label="Game",
            neighbor_key="game_balatro",
            neighbor_display="Balatro",
            source_key="game_balatro",
            target_key="牌组构筑",
        )
    ]
    result = build_neighborhood(focus, rows, limit=150)
    assert result.nodes[0].id == "game_balatro"
    assert result.nodes[0].node_type == "Game"
    edge = result.edges[0]
    assert edge.source == "game_balatro"
    assert edge.target == "牌组构筑"


def test_truncated_flag_set_when_rows_capped():
    rows = [
        NeighborRow(
            "HAS_MECHANIC",
            {},
            "Mechanic",
            f"m{i}",
            f"m{i}",
            source_key="game_hk",
            target_key=f"m{i}",
        )
        for i in range(3)
    ]
    result = build_neighborhood(_focus(), rows, limit=2)
    assert len(result.nodes) == 2
    assert result.truncated is True
