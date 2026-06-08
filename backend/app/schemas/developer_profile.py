from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from app.schemas.artifacts import DeveloperConstraint
from app.schemas.common import ConfidenceLevel, NonEmptyStr, StrictBaseModel


SourceKind = Literal["raw_text", "explicit_field"]


class ProfileParseInput(StrictBaseModel):
    raw_text: str = Field(min_length=1)
    liked_references: list[NonEmptyStr] = Field(default_factory=list)
    disliked_references_or_mechanics: list[NonEmptyStr] = Field(default_factory=list)
    expected_project_scale: str | None = Field(default=None, min_length=1)


class ProfileFieldSource(StrictBaseModel):
    field: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
    source_kind: SourceKind
    confidence: ConfidenceLevel


class MissingProfileField(StrictBaseModel):
    field: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    blocking: bool


class DeveloperProfileDraft(StrictBaseModel):
    id: str = Field(min_length=1)
    team_size: str | None = Field(default=None, min_length=1)
    time_budget: str | None = Field(default=None, min_length=1)
    programming_ability: str | None = Field(default=None, min_length=1)
    art_ability: str | None = Field(default=None, min_length=1)
    audio_ability: str | None = Field(default=None, min_length=1)
    content_production_ability: str | None = Field(default=None, min_length=1)
    liked_references: list[NonEmptyStr] = Field(default_factory=list)
    disliked_references_or_mechanics: list[NonEmptyStr] = Field(default_factory=list)
    desired_player_experiences: list[NonEmptyStr] = Field(default_factory=list)
    constraints: list[DeveloperConstraint] = Field(default_factory=list)
    missing_fields: list[MissingProfileField] = Field(default_factory=list)
    field_sources: list[ProfileFieldSource] = Field(default_factory=list)
    raw_text: str = Field(min_length=1)
    is_complete: bool

    @model_validator(mode="after")
    def completeness_matches_blocking_missing_fields(self) -> Self:
        has_blocking_missing_field = any(field.blocking for field in self.missing_fields)
        if self.is_complete == has_blocking_missing_field:
            raise ValueError("is_complete must match blocking missing fields")
        return self


class ProfileParseResult(StrictBaseModel):
    draft: DeveloperProfileDraft
    warnings: list[NonEmptyStr] = Field(default_factory=list)
