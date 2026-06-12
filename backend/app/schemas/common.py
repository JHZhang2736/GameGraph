from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


NonEmptyStr = Annotated[str, Field(min_length=1)]


class StrictBaseModel(BaseModel):
    """Base model shared by contract schemas."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class ConstraintType(StrEnum):
    HARD = "hard"
    STRONG_PREFERENCE = "strong_preference"
    SOFT_PREFERENCE = "soft_preference"
