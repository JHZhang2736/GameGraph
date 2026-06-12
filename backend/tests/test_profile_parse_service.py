from app.schemas.common import ConstraintType
from app.schemas.developer_profile import ProfileParseInput
from app.services.profile_llm import (
    ExtractedConstraint,
    ExtractedSource,
    ProfileExtraction,
)
from app.services.profile_parse_service import parse_profile


class FakeClient:
    def __init__(self, extraction: ProfileExtraction | None = None, error: Exception | None = None) -> None:
        self._extraction = extraction
        self._error = error
        self.calls = 0

    def extract(self, input_data: ProfileParseInput) -> ProfileExtraction:
        self.calls += 1
        if self._error is not None:
            raise self._error
        assert self._extraction is not None
        return self._extraction


def complete_extraction() -> ProfileExtraction:
    return ProfileExtraction(
        team_size="solo",
        time_budget="three month prototype",
        programming_ability="strong",
        art_ability="weak",
        audio_ability=None,
        content_production_ability="limited",
        liked_references=["Hades"],
        disliked_references_or_mechanics=["online multiplayer"],
        desired_player_experiences=["short runs"],
        constraints=[
            ExtractedConstraint(type=ConstraintType.HARD, statement="Do not require online multiplayer.")
        ],
        field_sources=[
            ExtractedSource(field="team_size", source_text="我一个人做")
        ],
        warnings=[],
    )


def test_none_client_uses_rule_parser() -> None:
    result = parse_profile(
        ProfileParseInput(
            raw_text=(
                "我是 solo 开发者，程序能力强，美术能力弱，三个月原型。"
                "我喜欢 Balatro，想要短局，不要做在线多人，也不想做大量内容。"
            )
        ),
        None,
    )
    assert result.draft.is_complete is True
    assert result.draft.team_size == "solo"


def test_llm_fields_flow_into_draft_with_code_owned_completeness() -> None:
    result = parse_profile(ProfileParseInput(raw_text="我一个人做游戏"), FakeClient(complete_extraction()))
    assert result.draft.team_size == "solo"
    assert result.draft.audio_ability == "basic"  # defaulted, never null
    assert result.draft.is_complete is True
    assert [c.id for c in result.draft.constraints] == ["constraint_1"]


def test_llm_cannot_bypass_completeness_gate() -> None:
    extraction = complete_extraction().model_copy(update={"team_size": None})
    result = parse_profile(ProfileParseInput(raw_text="x"), FakeClient(extraction))
    assert result.draft.is_complete is False
    assert any(field.field == "team_size" for field in result.draft.missing_fields)


def test_blank_llm_string_is_treated_as_missing_not_validation_error() -> None:
    extraction = complete_extraction().model_copy(update={"team_size": "   "})
    result = parse_profile(ProfileParseInput(raw_text="x"), FakeClient(extraction))
    assert result.draft.team_size is None
    assert result.draft.is_complete is False
    assert any(field.field == "team_size" for field in result.draft.missing_fields)


def test_explicit_fields_override_llm_extraction() -> None:
    result = parse_profile(
        ProfileParseInput(
            raw_text="我一个人做游戏",
            liked_references=["Baba Is You"],
            expected_project_scale="six week prototype",
        ),
        FakeClient(complete_extraction()),
    )
    assert result.draft.liked_references == ["Baba Is You"]
    assert result.draft.time_budget == "six week prototype"
    source = next(s for s in result.draft.field_sources if s.field == "liked_references")
    assert source.source_kind == "explicit_field"


def test_llm_error_falls_back_to_rules_with_warning() -> None:
    client = FakeClient(error=RuntimeError("boom"))
    result = parse_profile(
        ProfileParseInput(
            raw_text=(
                "我是 solo 开发者，程序能力强，美术能力弱，三个月原型。"
                "我喜欢 Balatro，想要短局，不要做在线多人，也不想做大量内容。"
            )
        ),
        client,
    )
    assert client.calls == 1
    assert result.draft.is_complete is True
    assert result.warnings[0] == "LLM 解析失败，已降级为规则解析。"


def test_explicit_disliked_references_override_llm_extraction() -> None:
    result = parse_profile(
        ProfileParseInput(
            raw_text="我一个人做游戏",
            disliked_references_or_mechanics=["precision platforming"],
        ),
        FakeClient(complete_extraction()),
    )
    assert result.draft.disliked_references_or_mechanics == ["precision platforming"]
    source = next(
        s
        for s in result.draft.field_sources
        if s.field == "disliked_references_or_mechanics"
    )
    assert source.source_kind == "explicit_field"
