from __future__ import annotations

from typing import Any

from app.schemas.import_document import GameImportDocument
from app.services.fixture_pipeline import ContractViolation


def check_import_contracts(document: GameImportDocument) -> None:
    if document.profile.game_id != document.candidate.id:
        raise ContractViolation("profile.game_id must match candidate.id")


def validate_import_document(raw: dict[str, Any]) -> GameImportDocument:
    document = GameImportDocument.model_validate(raw)
    check_import_contracts(document)
    return document
