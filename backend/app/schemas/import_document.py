from __future__ import annotations

from pydantic import Field

from app.schemas.artifacts import DesignClaim, GameDesignProfile, SeedGame
from app.schemas.common import StrictBaseModel


class GameImportDocument(StrictBaseModel):
    candidate: SeedGame
    profile: GameDesignProfile
    claims: list[DesignClaim] = Field(default_factory=list)
