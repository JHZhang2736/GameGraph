from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.routes_import import get_repository
from app.graph.game_repository import GameRepository
from app.schemas.graph import NeighborhoodResult, NodeSearchHit

router = APIRouter()


@router.get("/graph/mechanics", response_model=list[str])
def list_mechanics(
    repository: GameRepository = Depends(get_repository),
) -> list[str]:
    return repository.list_mechanics()


@router.get("/graph/search", response_model=list[NodeSearchHit])
def search_graph(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    repository: GameRepository = Depends(get_repository),
) -> list[NodeSearchHit]:
    return repository.search_nodes(q, limit)


@router.get("/graph/neighbors", response_model=NeighborhoodResult)
def graph_neighbors(
    node_id: str = Query(min_length=1),
    # 仅支持 1 跳邻域；多跳通过前端「点击节点展开」增量实现
    hops: int = Query(default=1, ge=1, le=1),
    limit: int = Query(default=150, ge=1, le=500),
    rel_types: str | None = Query(default=None),
    repository: GameRepository = Depends(get_repository),
) -> NeighborhoodResult:
    parsed = [t for t in rel_types.split(",") if t] if rel_types else None
    result = repository.neighbors(node_id, hops, limit, parsed)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    return result
