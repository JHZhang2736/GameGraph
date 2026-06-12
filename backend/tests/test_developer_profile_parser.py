from app.schemas.common import ConstraintType
from app.schemas.developer_profile import ProfileParseInput
from app.services.developer_profile_parser import (
    parse_developer_profile_input,
    promote_draft_to_profile,
)


DEFAULT_TEXT = (
    "我是 solo 开发者，程序能力强，美术能力弱，想做三个月内能验证的原型。"
    "我喜欢 Balatro 和 Into the Breach，想要短局、系统性决策和战术预测。"
    "不要做在线多人，我不想做长篇叙事内容，也不想做大量内容。"
)


def field_names(result):
    return {field.field for field in result.draft.missing_fields}


def test_parse_default_text_returns_complete_draft() -> None:
    result = parse_developer_profile_input(ProfileParseInput(raw_text=DEFAULT_TEXT))

    assert result.draft.is_complete is True
    assert result.draft.team_size == "solo"
    assert result.draft.time_budget == "three month prototype"
    assert result.draft.programming_ability == "strong"
    assert result.draft.art_ability == "weak"
    assert result.draft.audio_ability == "basic"
    assert result.draft.content_production_ability == "limited"
    assert result.draft.liked_references == ["Balatro", "Into the Breach"]
    assert result.draft.desired_player_experiences == [
        "short runs",
        "systemic decisions",
        "tactical prediction",
    ]


def test_parser_complete_draft_can_be_promoted_to_profile() -> None:
    result = parse_developer_profile_input(ProfileParseInput(raw_text=DEFAULT_TEXT))

    profile = promote_draft_to_profile(result.draft)

    assert profile.id == "profile_draft_current"
    assert profile.liked_references == ["Balatro", "Into the Breach"]
    assert [constraint.id for constraint in profile.constraints] == [
        "constraint_no_online",
        "constraint_avoid_long_narrative",
        "constraint_limited_content",
    ]


def test_optional_fields_absent_keeps_draft_complete() -> None:
    # No liked games, desired experiences, or constraints stated — all optional,
    # so a profile with the five required fields is still complete.
    result = parse_developer_profile_input(
        ProfileParseInput(
            raw_text="我是 solo 开发者，程序强，美术弱，三个月原型，limited content。"
        )
    )

    assert result.draft.is_complete is True
    missing = field_names(result)
    assert "liked_references" not in missing
    assert "desired_player_experiences" not in missing
    assert "constraints" not in missing


def test_parse_separates_hard_and_strong_preference_constraints() -> None:
    result = parse_developer_profile_input(ProfileParseInput(raw_text=DEFAULT_TEXT))

    constraints = {constraint.statement: constraint.type for constraint in result.draft.constraints}
    assert constraints["Do not require online multiplayer."] == ConstraintType.HARD
    assert constraints["Avoid long scripted narrative."] == ConstraintType.STRONG_PREFERENCE
    assert (
        constraints["Prefer concepts with limited content production."]
        == ConstraintType.STRONG_PREFERENCE
    )


def test_liked_games_do_not_create_hard_constraints() -> None:
    result = parse_developer_profile_input(
        ProfileParseInput(raw_text="我是 solo，程序强，美术弱，三个月原型。我喜欢 Balatro。")
    )

    hard_constraints = [
        constraint.statement
        for constraint in result.draft.constraints
        if constraint.type == ConstraintType.HARD
    ]

    assert hard_constraints == []
    missing = field_names(result)
    # Desired experiences are optional now; the unstated required field still blocks.
    assert "desired_player_experiences" not in missing
    assert "content_production_ability" in missing


def test_vague_time_budget_is_blocking_missing_field() -> None:
    result = parse_developer_profile_input(
        ProfileParseInput(
            raw_text=(
                "我是 solo 开发者，程序能力强，美术能力弱，想尽快做个原型。"
                "我想要短局和系统性决策，不要做在线多人，也不想做大量内容。"
            )
        )
    )

    missing = {field.field: field for field in result.draft.missing_fields}
    assert result.draft.is_complete is False
    assert missing["time_budget"].blocking is True
    assert result.draft.time_budget is None


def test_explicit_fields_override_raw_text_references() -> None:
    result = parse_developer_profile_input(
        ProfileParseInput(
            raw_text=DEFAULT_TEXT,
            liked_references=["Baba Is You"],
            disliked_references_or_mechanics=["precision platforming"],
            expected_project_scale="six week prototype",
        )
    )

    assert result.draft.liked_references == ["Baba Is You"]
    assert result.draft.disliked_references_or_mechanics == ["precision platforming"]
    assert result.draft.time_budget == "six week prototype"
    source = next(
        item for item in result.draft.field_sources if item.field == "liked_references"
    )
    assert source.source_kind == "explicit_field"


def test_key_fields_have_sources() -> None:
    result = parse_developer_profile_input(ProfileParseInput(raw_text=DEFAULT_TEXT))

    sourced_fields = {source.field for source in result.draft.field_sources}
    assert {
        "team_size",
        "time_budget",
        "programming_ability",
        "art_ability",
        "content_production_ability",
        "liked_references",
        "desired_player_experiences",
        "constraints",
    }.issubset(sourced_fields)


def test_parse_programming_and_art_chinese_aliases() -> None:
    first_result = parse_developer_profile_input(
        ProfileParseInput(
            raw_text="我是 solo 开发者，擅长编程，不会画，三个月原型。不想做大量内容，想要短局。"
        )
    )
    second_result = parse_developer_profile_input(
        ProfileParseInput(
            raw_text="我是 solo 开发者，会写系统，低美术，三个月原型。不想做大量内容，想要短局。"
        )
    )

    assert first_result.draft.programming_ability == "strong"
    assert first_result.draft.art_ability == "weak"
    assert second_result.draft.programming_ability == "strong"
    assert second_result.draft.art_ability == "weak"


def test_parse_explicit_audio_basic_aliases_with_inferred_source() -> None:
    first_result = parse_developer_profile_input(
        ProfileParseInput(
            raw_text="我是 solo 开发者，程序强，美术弱，音频一般，三个月原型。不想做大量内容，想要短局。"
        )
    )
    second_result = parse_developer_profile_input(
        ProfileParseInput(
            raw_text="我是 solo 开发者，程序强，美术弱，基础音效，三个月原型。不想做大量内容，想要短局。"
        )
    )

    for result in [first_result, second_result]:
        assert result.draft.audio_ability == "basic"
        source = next(
            item for item in result.draft.field_sources if item.field == "audio_ability"
        )
        assert source.source_text != "defaulted to basic"


def test_finalize_completeness_flags_only_empty_blocking_fields() -> None:
    from app.services.developer_profile_parser import finalize_completeness

    missing, is_complete = finalize_completeness(
        {
            "team_size": "solo",
            "time_budget": None,
            "programming_ability": "strong",
            "art_ability": "weak",
            "content_production_ability": "limited",
            "liked_references": ["Balatro"],
            "desired_player_experiences": ["short runs"],
            "constraints": [object()],
        }
    )

    assert is_complete is False
    names = {field.field: field for field in missing}
    assert set(names) == {"time_budget"}
    assert names["time_budget"].blocking is True
    assert names["time_budget"].reason == (
        "Could not infer time_budget from developer profile input."
    )
