from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.graph.connection import create_driver
from app.graph.game_repository import GameRepository
from app.schemas.graph import GameSummary
from app.schemas.import_document import GameImportDocument
from app.services.import_service import ImportSummary, check_import_contracts

router = APIRouter()

_driver = None


def get_repository() -> GameRepository:
    # 默认 provider：惰性创建单例 driver。测试通过 dependency_overrides 覆盖本函数。
    global _driver
    if _driver is None:
        _driver = create_driver()
    return GameRepository(_driver)


@router.post("/import/game", response_model=ImportSummary)
def import_game(
    document: GameImportDocument,
    repository: GameRepository = Depends(get_repository),
) -> ImportSummary:
    check_import_contracts(document)
    return repository.upsert_game(document)


@router.get("/games", response_model=list[GameSummary])
def list_games(
    repository: GameRepository = Depends(get_repository),
) -> list[GameSummary]:
    return repository.list_games()


@router.get("/games/{game_id}", response_model=GameImportDocument)
def get_game(
    game_id: str,
    repository: GameRepository = Depends(get_repository),
) -> GameImportDocument:
    document = repository.get_game(game_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")
    return document
