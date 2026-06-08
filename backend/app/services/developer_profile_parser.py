from __future__ import annotations

from collections.abc import Iterable

from app.schemas.artifacts import DeveloperConstraint, DeveloperProfile
from app.schemas.common import ConfidenceLevel, ConstraintType
from app.schemas.developer_profile import (
    DeveloperProfileDraft,
    MissingProfileField,
    ProfileFieldSource,
    ProfileParseInput,
    ProfileParseResult,
)
from app.services.fixture_pipeline import ContractViolation


BLOCKING_FIELDS = {
    "team_size",
    "time_budget",
    "programming_ability",
    "art_ability",
    "content_production_ability",
    "desired_player_experiences",
}


def _source(
    field: str,
    source_text: str,
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
    source_kind: str = "raw_text",
) -> ProfileFieldSource:
    return ProfileFieldSource(
        field=field,
        source_text=source_text,
        source_kind=source_kind,
        confidence=confidence,
    )


def _contains_any(value: str, needles: Iterable[str]) -> bool:
    normalized = value.lower()
    return any(needle.lower() in normalized for needle in needles)


def _missing(field: str, reason: str, blocking: bool = True) -> MissingProfileField:
    return MissingProfileField(field=field, reason=reason, blocking=blocking)


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value not in seen:
            unique_values.append(value)
            seen.add(value)
    return unique_values


def _team_size(raw_text: str) -> tuple[str | None, ProfileFieldSource | None]:
    if _contains_any(raw_text, ["solo", "一个人", "单人", "独立开发者"]):
        return "solo", _source("team_size", raw_text)
    if _contains_any(raw_text, ["两个人", "2人", "小团队"]):
        return "small team", _source("team_size", raw_text)
    return None, None


def _time_budget(
    input_data: ProfileParseInput,
) -> tuple[str | None, ProfileFieldSource | None, list[str]]:
    if input_data.expected_project_scale:
        return (
            input_data.expected_project_scale,
            _source(
                "time_budget",
                input_data.expected_project_scale,
                source_kind="explicit_field",
            ),
            [],
        )

    raw_text = input_data.raw_text
    if _contains_any(raw_text, ["三个月", "3个月", "three month"]):
        return "three month prototype", _source("time_budget", raw_text), []
    if _contains_any(raw_text, ["周末", "业余", "part-time"]):
        return (
            "part-time prototype",
            _source("time_budget", raw_text, ConfidenceLevel.MEDIUM),
            ["Interpreted time budget as part-time prototype."],
        )
    if _contains_any(raw_text, ["尽快", "短期"]):
        return None, None, ["Time budget is vague and needs clarification."]
    return None, None, []


def _ability(
    raw_text: str,
    field: str,
    strong_terms: Iterable[str],
    weak_terms: Iterable[str],
    basic_terms: Iterable[str],
) -> tuple[str | None, ProfileFieldSource | None]:
    if _contains_any(raw_text, strong_terms):
        return "strong", _source(field, raw_text)
    if _contains_any(raw_text, weak_terms):
        return "weak", _source(field, raw_text)
    if _contains_any(raw_text, basic_terms):
        return "basic", _source(field, raw_text)
    return None, None


def _content_ability(raw_text: str) -> tuple[str | None, ProfileFieldSource | None]:
    if _contains_any(raw_text, ["不想做大量内容", "内容产能有限", "limited content"]):
        return "limited", _source("content_production_ability", raw_text)
    return None, None


def _references(
    input_data: ProfileParseInput,
) -> tuple[list[str], list[str], list[ProfileFieldSource]]:
    sources: list[ProfileFieldSource] = []
    if input_data.liked_references:
        liked_references = _unique(input_data.liked_references)
        sources.append(
            _source(
                "liked_references",
                ", ".join(liked_references),
                source_kind="explicit_field",
            )
        )
    else:
        liked_references = _unique(
            reference
            for reference in ["Balatro", "Into the Breach", "Baba Is You"]
            if _contains_any(input_data.raw_text, [reference])
        )
        if liked_references:
            sources.append(_source("liked_references", input_data.raw_text))

    if input_data.disliked_references_or_mechanics:
        disliked = _unique(input_data.disliked_references_or_mechanics)
        sources.append(
            _source(
                "disliked_references_or_mechanics",
                ", ".join(disliked),
                source_kind="explicit_field",
            )
        )
    else:
        disliked = _unique(
            reference
            for reference, terms in {
                "online multiplayer": ["在线多人", "online multiplayer"],
                "long scripted narrative": ["长篇叙事", "long scripted narrative"],
            }.items()
            if _contains_any(input_data.raw_text, terms)
        )
        if disliked:
            sources.append(
                _source("disliked_references_or_mechanics", input_data.raw_text)
            )

    return liked_references, disliked, sources


def _desired_experiences(raw_text: str) -> tuple[list[str], ProfileFieldSource | None]:
    experiences = _unique(
        experience
        for experience, terms in {
            "short runs": ["短局", "short runs"],
            "systemic decisions": ["系统性决策", "systemic decisions"],
            "tactical prediction": ["战术预测", "tactical prediction"],
            "replayability": ["高重玩", "replayability"],
        }.items()
        if _contains_any(raw_text, terms)
    )
    if not experiences:
        return [], None
    return experiences, _source("desired_player_experiences", raw_text)


def _constraints(
    raw_text: str,
) -> tuple[list[DeveloperConstraint], ProfileFieldSource | None]:
    constraints: list[DeveloperConstraint] = []
    if _contains_any(
        raw_text,
        ["不要做在线多人", "不能做在线多人", "do not require online multiplayer"],
    ):
        constraints.append(
            DeveloperConstraint(
                id="constraint_no_online",
                type=ConstraintType.HARD,
                statement="Do not require online multiplayer.",
            )
        )
    if _contains_any(raw_text, ["不想做长篇叙事", "尽量不要长篇叙事"]):
        constraints.append(
            DeveloperConstraint(
                id="constraint_avoid_long_narrative",
                type=ConstraintType.STRONG_PREFERENCE,
                statement="Avoid long scripted narrative.",
            )
        )
    if _contains_any(raw_text, ["不想做大量内容", "内容产能有限"]):
        constraints.append(
            DeveloperConstraint(
                id="constraint_limited_content",
                type=ConstraintType.STRONG_PREFERENCE,
                statement="Prefer concepts with limited content production.",
            )
        )

    if not constraints:
        return [], None
    return constraints, _source("constraints", raw_text)


def parse_developer_profile_input(input_data: ProfileParseInput) -> ProfileParseResult:
    raw_text = input_data.raw_text
    field_sources: list[ProfileFieldSource] = []
    warnings: list[str] = []

    team_size, team_source = _team_size(raw_text)
    if team_source:
        field_sources.append(team_source)

    time_budget, time_source, time_warnings = _time_budget(input_data)
    if time_source:
        field_sources.append(time_source)
    warnings.extend(time_warnings)

    programming_ability, programming_source = _ability(
        raw_text,
        "programming_ability",
        strong_terms=[
            "程序能力强",
            "程序强",
            "擅长编程",
            "会写系统",
            "strong programming",
        ],
        weak_terms=["程序能力弱", "程序弱", "weak programming"],
        basic_terms=["程序基础", "basic programming"],
    )
    if programming_source:
        field_sources.append(programming_source)

    art_ability, art_source = _ability(
        raw_text,
        "art_ability",
        strong_terms=["美术能力强", "美术强", "strong art"],
        weak_terms=["美术能力弱", "美术弱", "不会画", "低美术", "weak art"],
        basic_terms=["美术基础", "basic art"],
    )
    if art_source:
        field_sources.append(art_source)

    audio_ability, audio_source = _ability(
        raw_text,
        "audio_ability",
        strong_terms=["音频能力强", "音频强", "strong audio"],
        weak_terms=["音频能力弱", "音频弱", "weak audio"],
        basic_terms=["音频基础", "音频一般", "基础音效", "basic audio"],
    )
    if audio_source:
        field_sources.append(audio_source)
    else:
        audio_ability = "basic"
        field_sources.append(
            _source(
                "audio_ability",
                "defaulted to basic",
                ConfidenceLevel.LOW,
            )
        )

    content_production_ability, content_source = _content_ability(raw_text)
    if content_source:
        field_sources.append(content_source)

    liked_references, disliked_references_or_mechanics, reference_sources = _references(
        input_data
    )
    field_sources.extend(reference_sources)

    desired_player_experiences, desired_source = _desired_experiences(raw_text)
    if desired_source:
        field_sources.append(desired_source)

    constraints, constraints_source = _constraints(raw_text)
    if constraints_source:
        field_sources.append(constraints_source)

    missing_fields = [
        _missing(field, f"Could not infer {field} from developer profile input.")
        for field, value in {
            "team_size": team_size,
            "time_budget": time_budget,
            "programming_ability": programming_ability,
            "art_ability": art_ability,
            "content_production_ability": content_production_ability,
            "desired_player_experiences": desired_player_experiences,
        }.items()
        if field in BLOCKING_FIELDS and not value
    ]
    is_complete = not any(field.blocking for field in missing_fields)

    return ProfileParseResult(
        draft=DeveloperProfileDraft(
            id="profile_draft_current",
            team_size=team_size,
            time_budget=time_budget,
            programming_ability=programming_ability,
            art_ability=art_ability,
            audio_ability=audio_ability,
            content_production_ability=content_production_ability,
            liked_references=liked_references,
            disliked_references_or_mechanics=disliked_references_or_mechanics,
            desired_player_experiences=desired_player_experiences,
            constraints=constraints,
            missing_fields=missing_fields,
            field_sources=field_sources,
            raw_text=raw_text,
            is_complete=is_complete,
        ),
        warnings=warnings,
    )


def promote_draft_to_profile(draft: DeveloperProfileDraft) -> DeveloperProfile:
    if not draft.is_complete:
        raise ContractViolation("DeveloperProfileDraft is incomplete")

    return DeveloperProfile(
        id=draft.id,
        team_size=_required(draft.team_size, "team_size"),
        time_budget=_required(draft.time_budget, "time_budget"),
        programming_ability=_required(draft.programming_ability, "programming_ability"),
        art_ability=_required(draft.art_ability, "art_ability"),
        audio_ability=_required(draft.audio_ability, "audio_ability"),
        content_production_ability=_required(
            draft.content_production_ability,
            "content_production_ability",
        ),
        liked_references=draft.liked_references,
        disliked_references_or_mechanics=draft.disliked_references_or_mechanics,
        desired_player_experiences=draft.desired_player_experiences,
        constraints=draft.constraints,
    )


def _required(value: str | None, field: str) -> str:
    if value is None:
        raise ContractViolation(f"DeveloperProfileDraft missing required field: {field}")
    return value
