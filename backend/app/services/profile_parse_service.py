from __future__ import annotations

from app.schemas.artifacts import DeveloperConstraint
from app.schemas.common import ConfidenceLevel
from app.schemas.developer_profile import (
    DeveloperProfileDraft,
    ProfileFieldSource,
    ProfileParseInput,
    ProfileParseResult,
)
from app.services.developer_profile_parser import (
    finalize_completeness,
    parse_developer_profile_input,
)
from app.services.profile_llm import ProfileExtraction, ProfileLlmClient


def parse_profile(
    input_data: ProfileParseInput,
    client: ProfileLlmClient | None,
) -> ProfileParseResult:
    if client is None:
        return parse_developer_profile_input(input_data)
    try:
        extraction = client.extract(input_data)
        return _result_from_extraction(input_data, extraction)
    except Exception:
        fallback = parse_developer_profile_input(input_data)
        return ProfileParseResult(
            draft=fallback.draft,
            warnings=["LLM 解析失败，已降级为规则解析。", *fallback.warnings],
        )


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _result_from_extraction(
    input_data: ProfileParseInput,
    extraction: ProfileExtraction,
) -> ProfileParseResult:
    team_size = _clean(extraction.team_size)
    time_budget = _clean(extraction.time_budget)
    programming_ability = _clean(extraction.programming_ability)
    art_ability = _clean(extraction.art_ability)
    content_production_ability = _clean(extraction.content_production_ability)
    audio_ability = _clean(extraction.audio_ability) or "basic"
    liked = list(extraction.liked_references)
    disliked = list(extraction.disliked_references_or_mechanics)

    field_sources = [
        ProfileFieldSource(
            field=source.field,
            source_text=source.source_text,
            source_kind="raw_text",
            confidence=source.confidence,
        )
        for source in extraction.field_sources
    ]

    if input_data.liked_references:
        liked = list(input_data.liked_references)
        field_sources.append(
            ProfileFieldSource(
                field="liked_references",
                source_text=", ".join(liked),
                source_kind="explicit_field",
                confidence=ConfidenceLevel.HIGH,
            )
        )
    if input_data.disliked_references_or_mechanics:
        disliked = list(input_data.disliked_references_or_mechanics)
        field_sources.append(
            ProfileFieldSource(
                field="disliked_references_or_mechanics",
                source_text=", ".join(disliked),
                source_kind="explicit_field",
                confidence=ConfidenceLevel.HIGH,
            )
        )
    if input_data.expected_project_scale:
        time_budget = input_data.expected_project_scale
        field_sources.append(
            ProfileFieldSource(
                field="time_budget",
                source_text=time_budget,
                source_kind="explicit_field",
                confidence=ConfidenceLevel.HIGH,
            )
        )

    constraints = [
        DeveloperConstraint(
            id=f"constraint_{index + 1}",
            type=item.type,
            statement=item.statement,
        )
        for index, item in enumerate(extraction.constraints)
    ]

    missing_fields, is_complete = finalize_completeness(
        {
            "team_size": team_size,
            "time_budget": time_budget,
            "programming_ability": programming_ability,
            "art_ability": art_ability,
            "content_production_ability": content_production_ability,
            "liked_references": liked,
            "desired_player_experiences": extraction.desired_player_experiences,
            "constraints": constraints,
        }
    )

    draft = DeveloperProfileDraft(
        id="profile_draft_current",
        team_size=team_size,
        time_budget=time_budget,
        programming_ability=programming_ability,
        art_ability=art_ability,
        audio_ability=audio_ability,
        content_production_ability=content_production_ability,
        liked_references=liked,
        disliked_references_or_mechanics=disliked,
        desired_player_experiences=list(extraction.desired_player_experiences),
        constraints=constraints,
        missing_fields=missing_fields,
        field_sources=field_sources,
        raw_text=input_data.raw_text,
        is_complete=is_complete,
    )
    return ProfileParseResult(draft=draft, warnings=list(extraction.warnings))
