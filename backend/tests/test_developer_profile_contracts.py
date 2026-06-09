import pytest
from pydantic import ValidationError

from app.schemas.artifacts import DeveloperProfile
from app.schemas.common import ConfidenceLevel, ConstraintType
from app.schemas.developer_profile import (
    DeveloperProfileDraft,
    MissingProfileField,
    ProfileFieldSource,
    ProfileParseInput,
)
from app.services.developer_profile_parser import promote_draft_to_profile


def complete_draft() -> DeveloperProfileDraft:
    return DeveloperProfileDraft(
        id="profile_draft_solo_systems",
        team_size="solo",
        time_budget="three month prototype",
        programming_ability="strong",
        art_ability="weak",
        audio_ability="basic",
        content_production_ability="limited",
        liked_references=["Balatro", "Into the Breach"],
        disliked_references_or_mechanics=["online multiplayer"],
        desired_player_experiences=["short runs", "systemic decisions"],
        constraints=[
            {
                "id": "constraint_no_online",
                "type": ConstraintType.HARD,
                "statement": "Do not require online multiplayer.",
            }
        ],
        missing_fields=[],
        field_sources=[
            ProfileFieldSource(
                field="team_size",
                source_text="我是 solo 开发者",
                source_kind="raw_text",
                confidence=ConfidenceLevel.HIGH,
            )
        ],
        raw_text="我是 solo 开发者，程序能力强，美术能力弱，三个月原型。",
        is_complete=True,
    )


def test_profile_parse_input_rejects_blank_text() -> None:
    with pytest.raises(ValidationError):
        ProfileParseInput(raw_text="   ")


def test_profile_parse_input_rejects_blank_explicit_list_items() -> None:
    with pytest.raises(ValidationError):
        ProfileParseInput(raw_text="solo", liked_references=["Balatro", "  "])


def test_developer_profile_draft_accepts_incomplete_values() -> None:
    draft = DeveloperProfileDraft(
        id="profile_draft_incomplete",
        team_size="solo",
        time_budget=None,
        programming_ability=None,
        art_ability="weak",
        audio_ability="basic",
        content_production_ability=None,
        liked_references=[],
        disliked_references_or_mechanics=[],
        desired_player_experiences=[],
        constraints=[],
        missing_fields=[
            MissingProfileField(
                field="time_budget",
                reason="No concrete project duration was provided.",
                blocking=True,
            )
        ],
        field_sources=[],
        raw_text="我是 solo 开发者。",
        is_complete=False,
    )

    assert draft.time_budget is None
    assert draft.missing_fields[0].blocking is True
    assert draft.is_complete is False


def test_promote_draft_to_profile_rejects_incomplete_draft() -> None:
    draft = complete_draft().model_copy(
        update={
            "time_budget": None,
            "missing_fields": [
                MissingProfileField(
                    field="time_budget",
                    reason="No concrete project duration was provided.",
                    blocking=True,
                )
            ],
            "is_complete": False,
        }
    )

    with pytest.raises(ValueError, match="DeveloperProfileDraft is incomplete"):
        promote_draft_to_profile(draft)


def test_promote_draft_to_profile_returns_existing_profile_contract() -> None:
    profile = promote_draft_to_profile(complete_draft())

    assert profile.id == "profile_draft_solo_systems"
    assert profile.team_size == "solo"
    assert profile.time_budget == "three month prototype"
    assert profile.constraints[0].type == ConstraintType.HARD
    assert not hasattr(profile, "missing_fields")


def test_developer_profile_allows_empty_optional_lists() -> None:
    # 只有 6 个标量能力字段必填；liked_references / desired_player_experiences /
    # constraints / disliked_references_or_mechanics 均可选（可空、可省略）。
    profile = DeveloperProfile(
        id="profile_min",
        team_size="solo",
        time_budget="three month prototype",
        programming_ability="strong",
        art_ability="weak",
        audio_ability="basic",
        content_production_ability="limited",
    )
    assert profile.liked_references == []
    assert profile.disliked_references_or_mechanics == []
    assert profile.desired_player_experiences == []
    assert profile.constraints == []


def test_promote_draft_to_profile_allows_empty_optional_lists() -> None:
    # 一个完整（5 个 blocking 字段齐全）但可选列表为空的 draft 应能 promote 成功，
    # 不再因 DeveloperProfile 的 min_length 在 promote 时崩。
    draft = complete_draft().model_copy(
        update={
            "liked_references": [],
            "disliked_references_or_mechanics": [],
            "desired_player_experiences": [],
            "constraints": [],
        }
    )
    profile = promote_draft_to_profile(draft)
    assert profile.liked_references == []
    assert profile.constraints == []
