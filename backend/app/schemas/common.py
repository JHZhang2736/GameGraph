from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictBaseModel(BaseModel):
    """Base model shared by contract schemas."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QualityStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    WEAK_EVIDENCE = "weak_evidence"
    CONFLICTING = "conflicting"


class ConstraintType(StrEnum):
    HARD = "hard"
    STRONG_PREFERENCE = "strong_preference"
    SOFT_PREFERENCE = "soft_preference"


class EvidenceRef(StrictBaseModel):
    title: str = Field(min_length=1)
    url: str | None = Field(default=None, min_length=1)
    quote_or_summary: str | None = Field(default=None, min_length=1)
    notes: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_reference_payload(self) -> Self:
        if not self.url and not self.quote_or_summary:
            raise ValueError("EvidenceRef requires url or quote_or_summary")
        return self
