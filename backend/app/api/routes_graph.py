from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.routes_import import get_repository
from app.graph.game_repository import GameRepository
from app.schemas.graph import NodeSearchHit

router = APIRouter()


@router.get("/graph/search", response_model=list[NodeSearchHit])
def search_graph(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    repository: GameRepository = Depends(get_repository),
) -> list[NodeSearchHit]:
    return repository.search_nodes(q, limit)
