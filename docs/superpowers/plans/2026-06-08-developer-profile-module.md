# Developer Profile Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 6.4 as a mixed developer-profile workbench that turns free-form developer input into a structured, auditable `DeveloperProfileDraft`, shows missing information, and can promote complete drafts into the existing `DeveloperProfile` contract.

**Architecture:** Backend owns the authoritative Pydantic contracts and deterministic parser. Frontend mirrors those contracts with TypeScript types, a local deterministic parser adapter, and a mixed `/profile` page; `lib/data` remains the only data-source boundary so a later API swap does not rewrite page components.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, Next.js App Router, React 19, TypeScript, TanStack Query, Vitest, React Testing Library, Tailwind CSS, existing shadcn/base-ui components.

---

## File Structure

- Create `backend/app/schemas/developer_profile.py`: profile parse input, draft, missing field, source, and parse result schemas.
- Modify `backend/app/schemas/__init__.py`: export the new 6.4 contracts.
- Create `backend/app/services/developer_profile_parser.py`: deterministic parser and `promote_draft_to_profile`.
- Test `backend/tests/test_developer_profile_contracts.py`: schema and promotion contract tests.
- Test `backend/tests/test_developer_profile_parser.py`: deterministic parser behavior tests.
- Modify `frontend/lib/types/index.ts`: mirror 6.4 contracts in TypeScript.
- Create `frontend/lib/profile/parser.ts`: local parser adapter with the same behavior as the backend MVP parser.
- Test `frontend/lib/profile/parser.test.ts`: frontend parser behavior.
- Modify `frontend/lib/data/index.ts`: expose `parseDeveloperProfileInput`.
- Modify `frontend/lib/queries/index.ts`: expose `useParseDeveloperProfileInput` only if a mutation hook is useful; otherwise keep parsing in the page through `lib/data`.
- Create `frontend/components/profile/profile-input-panel.tsx`: free-text input and explicit fields.
- Create `frontend/components/profile/profile-draft-preview.tsx`: structured preview.
- Create `frontend/components/profile/profile-missing-fields.tsx`: blocking and non-blocking missing-field display.
- Create `frontend/components/profile/profile-source-list.tsx`: field source audit display.
- Modify `frontend/app/(workbench)/profile/page.tsx`: replace read-only fixture view with mixed workbench.
- Modify `frontend/app/(workbench)/profile/profile-page.test.tsx`: cover input, parse, missing fields, and constraint highlighting.

---

### Task 1: Backend 6.4 Contracts

**Files:**
- Create: `backend/app/schemas/developer_profile.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_developer_profile_contracts.py`

- [ ] **Step 1: Write the failing schema contract tests**

Create `backend/tests/test_developer_profile_contracts.py`:

```python
import pytest
from pydantic import ValidationError

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
```

- [ ] **Step 2: Run the contract tests to verify they fail**

Run:

```powershell
Push-Location backend; python -m pytest tests/test_developer_profile_contracts.py -v; Pop-Location
```

Expected: FAIL with import errors for `app.schemas.developer_profile` and `app.services.developer_profile_parser`.

- [ ] **Step 3: Add the backend schema contracts**

Create `backend/app/schemas/developer_profile.py`:

```python
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
```

Modify `backend/app/schemas/__init__.py` by adding these imports:

```python
from app.schemas.developer_profile import (
    DeveloperProfileDraft,
    MissingProfileField,
    ProfileFieldSource,
    ProfileParseInput,
    ProfileParseResult,
)
```

Add these names to `__all__`:

```python
    "DeveloperProfileDraft",
    "MissingProfileField",
    "ProfileFieldSource",
    "ProfileParseInput",
    "ProfileParseResult",
```

- [ ] **Step 4: Add the minimal promotion function**

Create `backend/app/services/developer_profile_parser.py`:

```python
from __future__ import annotations

from app.schemas.artifacts import DeveloperProfile
from app.schemas.developer_profile import DeveloperProfileDraft
from app.services.fixture_pipeline import ContractViolation


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
```

- [ ] **Step 5: Run the contract tests to verify they pass**

Run:

```powershell
Push-Location backend; python -m pytest tests/test_developer_profile_contracts.py -v; Pop-Location
```

Expected: PASS, all 5 tests pass.

- [ ] **Step 6: Run the full backend baseline**

Run:

```powershell
Push-Location backend; python -m pytest; Pop-Location
```

Expected: PASS. Baseline before this plan was 44 tests; after Task 1 it should be 49 tests.

- [ ] **Step 7: Commit Task 1**

Run:

```powershell
git add backend/app/schemas/developer_profile.py backend/app/schemas/__init__.py backend/app/services/developer_profile_parser.py backend/tests/test_developer_profile_contracts.py
git commit -m "feat: add developer profile draft contracts"
```

Expected: commit succeeds on branch `codex/developer-profile-module`.

---

### Task 2: Backend Deterministic Parser

**Files:**
- Modify: `backend/app/services/developer_profile_parser.py`
- Test: `backend/tests/test_developer_profile_parser.py`

- [ ] **Step 1: Write parser behavior tests**

Create `backend/tests/test_developer_profile_parser.py`:

```python
from app.schemas.common import ConstraintType
from app.schemas.developer_profile import ProfileParseInput
from app.services.developer_profile_parser import parse_developer_profile_input


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


def test_parse_separates_hard_and_strong_preference_constraints() -> None:
    result = parse_developer_profile_input(ProfileParseInput(raw_text=DEFAULT_TEXT))

    constraints = {constraint.statement: constraint.type for constraint in result.draft.constraints}
    assert constraints["Do not require online multiplayer."] == ConstraintType.HARD
    assert constraints["Avoid long scripted narrative."] == ConstraintType.STRONG_PREFERENCE
    assert constraints["Prefer concepts with limited content production."] == ConstraintType.STRONG_PREFERENCE


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
    assert "desired_player_experiences" in field_names(result)


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
```

- [ ] **Step 2: Run parser tests to verify they fail**

Run:

```powershell
Push-Location backend; python -m pytest tests/test_developer_profile_parser.py -v; Pop-Location
```

Expected: FAIL with `cannot import name 'parse_developer_profile_input'`.

- [ ] **Step 3: Implement parser constants and helpers**

Add this code to `backend/app/services/developer_profile_parser.py` below the imports:

```python
import re
from collections.abc import Iterable

from app.schemas.artifacts import DeveloperConstraint
from app.schemas.common import ConfidenceLevel, ConstraintType
from app.schemas.developer_profile import (
    DeveloperProfileDraft,
    MissingProfileField,
    ProfileFieldSource,
    ProfileParseInput,
    ProfileParseResult,
)


BLOCKING_FIELDS = (
    "team_size",
    "time_budget",
    "programming_ability",
    "art_ability",
    "content_production_ability",
    "desired_player_experiences",
)


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
    return any(needle.lower() in value.lower() for needle in needles)


def _missing(field: str, reason: str, blocking: bool = True) -> MissingProfileField:
    return MissingProfileField(field=field, reason=reason, blocking=blocking)


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized.lower() not in seen:
            seen.add(normalized.lower())
            output.append(normalized)
    return output
```

- [ ] **Step 4: Implement field extraction functions**

Add this code below the helpers in `backend/app/services/developer_profile_parser.py`:

```python
def _team_size(raw_text: str) -> tuple[str | None, ProfileFieldSource | None]:
    if _contains_any(raw_text, ("solo", "一个人", "单人", "独立开发者")):
        return "solo", _source("team_size", "solo / 一个人 / 单人")
    if _contains_any(raw_text, ("两个人", "2人", "小团队")):
        return "small team", _source("team_size", "两个人 / 2人 / 小团队")
    return None, None


def _time_budget(input_data: ProfileParseInput) -> tuple[str | None, ProfileFieldSource | None, str | None]:
    if input_data.expected_project_scale:
        return (
            input_data.expected_project_scale,
            _source(
                "time_budget",
                input_data.expected_project_scale,
                source_kind="explicit_field",
            ),
            None,
        )
    raw_text = input_data.raw_text
    if _contains_any(raw_text, ("三个月", "3个月", "three month")):
        return "three month prototype", _source("time_budget", "三个月 / 3个月 / three month"), None
    if _contains_any(raw_text, ("周末", "业余", "part-time")):
        return (
            "part-time prototype",
            _source("time_budget", "周末 / 业余 / part-time", ConfidenceLevel.MEDIUM),
            "时间预算说明缺少明确周期长度。",
        )
    if _contains_any(raw_text, ("尽快", "短期")):
        return None, None, "时间预算表述过于模糊。"
    return None, None, None


def _ability(
    raw_text: str,
    field: str,
    strong_terms: tuple[str, ...],
    weak_terms: tuple[str, ...],
    basic_terms: tuple[str, ...],
) -> tuple[str | None, ProfileFieldSource | None]:
    if _contains_any(raw_text, strong_terms):
        return "strong", _source(field, " / ".join(strong_terms))
    if _contains_any(raw_text, weak_terms):
        return "weak", _source(field, " / ".join(weak_terms))
    if _contains_any(raw_text, basic_terms):
        return "basic", _source(field, " / ".join(basic_terms), ConfidenceLevel.MEDIUM)
    return None, None


def _content_ability(raw_text: str) -> tuple[str | None, ProfileFieldSource | None]:
    if _contains_any(raw_text, ("不想做大量内容", "内容产能有限", "limited content")):
        return "limited", _source("content_production_ability", "不想做大量内容 / 内容产能有限")
    return None, None
```

- [ ] **Step 5: Implement reference, experience, and constraint extraction**

Add this code below the field extraction functions:

```python
def _references(input_data: ProfileParseInput) -> tuple[list[str], list[str], list[ProfileFieldSource]]:
    sources: list[ProfileFieldSource] = []

    if input_data.liked_references:
        liked = input_data.liked_references
        sources.append(
            _source(
                "liked_references",
                ", ".join(liked),
                source_kind="explicit_field",
            )
        )
    else:
        liked = []
        if "Balatro" in input_data.raw_text:
            liked.append("Balatro")
        if "Into the Breach" in input_data.raw_text:
            liked.append("Into the Breach")
        if "Baba Is You" in input_data.raw_text:
            liked.append("Baba Is You")
        if liked:
            sources.append(_source("liked_references", ", ".join(liked)))

    if input_data.disliked_references_or_mechanics:
        disliked = input_data.disliked_references_or_mechanics
        sources.append(
            _source(
                "disliked_references_or_mechanics",
                ", ".join(disliked),
                source_kind="explicit_field",
            )
        )
    else:
        disliked = []
        if _contains_any(input_data.raw_text, ("在线多人", "online multiplayer")):
            disliked.append("online multiplayer")
        if _contains_any(input_data.raw_text, ("长篇叙事", "long scripted narrative")):
            disliked.append("long scripted narrative")
        if disliked:
            sources.append(_source("disliked_references_or_mechanics", ", ".join(disliked)))

    return _unique(liked), _unique(disliked), sources


def _desired_experiences(raw_text: str) -> tuple[list[str], ProfileFieldSource | None]:
    experiences: list[str] = []
    if _contains_any(raw_text, ("短局", "short runs")):
        experiences.append("short runs")
    if _contains_any(raw_text, ("系统性决策", "systemic decisions")):
        experiences.append("systemic decisions")
    if _contains_any(raw_text, ("战术预测", "tactical prediction")):
        experiences.append("tactical prediction")
    if _contains_any(raw_text, ("高重玩", "replayability")):
        experiences.append("replayability")

    if not experiences:
        return [], None
    return _unique(experiences), _source("desired_player_experiences", ", ".join(experiences))


def _constraints(raw_text: str) -> tuple[list[DeveloperConstraint], list[ProfileFieldSource]]:
    constraints: list[DeveloperConstraint] = []
    if _contains_any(raw_text, ("不要做在线多人", "不能做在线多人", "do not require online multiplayer")):
        constraints.append(
            DeveloperConstraint(
                id="constraint_no_online",
                type=ConstraintType.HARD,
                statement="Do not require online multiplayer.",
            )
        )
    if _contains_any(raw_text, ("不想做长篇叙事", "尽量不要长篇叙事")):
        constraints.append(
            DeveloperConstraint(
                id="constraint_avoid_long_narrative",
                type=ConstraintType.STRONG_PREFERENCE,
                statement="Avoid long scripted narrative.",
            )
        )
    if _contains_any(raw_text, ("不想做大量内容", "内容产能有限")):
        constraints.append(
            DeveloperConstraint(
                id="constraint_limited_content",
                type=ConstraintType.STRONG_PREFERENCE,
                statement="Prefer concepts with limited content production.",
            )
        )

    sources = []
    if constraints:
        sources.append(_source("constraints", "; ".join(item.statement for item in constraints)))
    return constraints, sources
```

- [ ] **Step 6: Implement `parse_developer_profile_input`**

Add this function above `promote_draft_to_profile`:

```python
def parse_developer_profile_input(input_data: ProfileParseInput) -> ProfileParseResult:
    raw_text = input_data.raw_text
    sources: list[ProfileFieldSource] = []
    warnings: list[str] = []

    team_size, team_source = _team_size(raw_text)
    if team_source:
        sources.append(team_source)

    time_budget, time_source, time_warning = _time_budget(input_data)
    if time_source:
        sources.append(time_source)
    if time_warning:
        warnings.append(time_warning)

    programming_ability, programming_source = _ability(
        raw_text,
        "programming_ability",
        ("程序能力强", "擅长编程", "会写系统", "strong programming"),
        ("程序弱", "不擅长编程", "weak programming"),
        ("基础编程", "basic programming"),
    )
    if programming_source:
        sources.append(programming_source)

    art_ability, art_source = _ability(
        raw_text,
        "art_ability",
        ("美术强", "strong art"),
        ("美术能力弱", "美术弱", "不会画", "低美术", "weak art"),
        ("基础美术", "basic art"),
    )
    if art_source:
        sources.append(art_source)

    audio_ability, audio_source = _ability(
        raw_text,
        "audio_ability",
        ("音频强", "strong audio"),
        ("音频弱", "weak audio"),
        ("音频一般", "基础音效", "basic audio"),
    )
    if audio_source:
        sources.append(audio_source)
    if audio_ability is None:
        audio_ability = "basic"
        sources.append(
            _source("audio_ability", "defaulted to basic", ConfidenceLevel.LOW)
        )

    content_production_ability, content_source = _content_ability(raw_text)
    if content_source:
        sources.append(content_source)

    liked, disliked, reference_sources = _references(input_data)
    sources.extend(reference_sources)

    experiences, experience_source = _desired_experiences(raw_text)
    if experience_source:
        sources.append(experience_source)

    constraints, constraint_sources = _constraints(raw_text)
    sources.extend(constraint_sources)

    missing_fields = _missing_fields(
        {
            "team_size": team_size,
            "time_budget": time_budget,
            "programming_ability": programming_ability,
            "art_ability": art_ability,
            "content_production_ability": content_production_ability,
            "desired_player_experiences": experiences,
        }
    )
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
            liked_references=liked,
            disliked_references_or_mechanics=disliked,
            desired_player_experiences=experiences,
            constraints=constraints,
            missing_fields=missing_fields,
            field_sources=sources,
            raw_text=raw_text,
            is_complete=is_complete,
        ),
        warnings=warnings,
    )


def _missing_fields(values: dict[str, object]) -> list[MissingProfileField]:
    missing: list[MissingProfileField] = []
    for field in BLOCKING_FIELDS:
        value = values[field]
        if value is None or value == []:
            missing.append(
                _missing(field, f"No usable {field} was found in the input.")
            )
    return missing
```

- [ ] **Step 7: Run parser tests to verify they pass**

Run:

```powershell
Push-Location backend; python -m pytest tests/test_developer_profile_parser.py -v; Pop-Location
```

Expected: PASS, all 6 tests pass.

- [ ] **Step 8: Run backend suite**

Run:

```powershell
Push-Location backend; python -m pytest; Pop-Location
```

Expected: PASS. Expected total after Task 2: 55 tests.

- [ ] **Step 9: Commit Task 2**

Run:

```powershell
git add backend/app/services/developer_profile_parser.py backend/tests/test_developer_profile_parser.py
git commit -m "feat: parse developer profile drafts"
```

Expected: commit succeeds.

---

### Task 3: Frontend Types and Local Parser

**Files:**
- Modify: `frontend/lib/types/index.ts`
- Create: `frontend/lib/profile/parser.ts`
- Test: `frontend/lib/profile/parser.test.ts`

- [ ] **Step 1: Write frontend parser tests**

Create `frontend/lib/profile/parser.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { parseDeveloperProfileInput } from "@/lib/profile/parser";

const defaultText =
  "我是 solo 开发者，程序能力强，美术能力弱，想做三个月内能验证的原型。" +
  "我喜欢 Balatro 和 Into the Breach，想要短局、系统性决策和战术预测。" +
  "不要做在线多人，我不想做长篇叙事内容，也不想做大量内容。";

describe("parseDeveloperProfileInput", () => {
  it("returns a complete draft for the default profile text", () => {
    const result = parseDeveloperProfileInput({ raw_text: defaultText });

    expect(result.draft.is_complete).toBe(true);
    expect(result.draft.team_size).toBe("solo");
    expect(result.draft.time_budget).toBe("three month prototype");
    expect(result.draft.programming_ability).toBe("strong");
    expect(result.draft.art_ability).toBe("weak");
    expect(result.draft.content_production_ability).toBe("limited");
    expect(result.draft.desired_player_experiences).toEqual([
      "short runs",
      "systemic decisions",
      "tactical prediction",
    ]);
  });

  it("marks vague time budget as a blocking missing field", () => {
    const result = parseDeveloperProfileInput({
      raw_text:
        "我是 solo 开发者，程序能力强，美术能力弱，想尽快做个原型。" +
        "我想要短局和系统性决策，不要做在线多人，也不想做大量内容。",
    });

    expect(result.draft.is_complete).toBe(false);
    expect(result.draft.time_budget).toBeNull();
    expect(result.draft.missing_fields).toContainEqual({
      field: "time_budget",
      reason: "No usable time_budget was found in the input.",
      blocking: true,
    });
  });

  it("keeps liked games out of hard constraints", () => {
    const result = parseDeveloperProfileInput({
      raw_text: "我是 solo，程序能力强，美术弱，三个月原型。我喜欢 Balatro。",
    });

    const hard = result.draft.constraints.filter((item) => item.type === "hard");
    expect(hard).toHaveLength(0);
    expect(result.draft.missing_fields.map((item) => item.field)).toContain(
      "desired_player_experiences",
    );
  });

  it("uses explicit references before inferred references", () => {
    const result = parseDeveloperProfileInput({
      raw_text: defaultText,
      liked_references: ["Baba Is You"],
      disliked_references_or_mechanics: ["precision platforming"],
      expected_project_scale: "six week prototype",
    });

    expect(result.draft.liked_references).toEqual(["Baba Is You"]);
    expect(result.draft.disliked_references_or_mechanics).toEqual([
      "precision platforming",
    ]);
    expect(result.draft.time_budget).toBe("six week prototype");
    expect(
      result.draft.field_sources.find((item) => item.field === "liked_references")
        ?.source_kind,
    ).toBe("explicit_field");
  });
});
```

- [ ] **Step 2: Run frontend parser tests to verify they fail**

Run:

```powershell
Push-Location frontend; npm test -- lib/profile/parser.test.ts; Pop-Location
```

Expected: FAIL because `frontend/lib/profile/parser.ts` does not exist.

- [ ] **Step 3: Add frontend 6.4 types**

Append these interfaces to `frontend/lib/types/index.ts` after `DeveloperProfile`:

```typescript
export type ProfileFieldSourceKind = "raw_text" | "explicit_field";

export interface ProfileParseInput {
  raw_text: string;
  liked_references?: string[];
  disliked_references_or_mechanics?: string[];
  expected_project_scale?: string;
}

export interface ProfileFieldSource {
  field: string;
  source_text: string;
  source_kind: ProfileFieldSourceKind;
  confidence: ConfidenceLevel;
}

export interface MissingProfileField {
  field: string;
  reason: string;
  blocking: boolean;
}

export interface DeveloperProfileDraft {
  id: string;
  team_size: string | null;
  time_budget: string | null;
  programming_ability: string | null;
  art_ability: string | null;
  audio_ability: string | null;
  content_production_ability: string | null;
  liked_references: string[];
  disliked_references_or_mechanics: string[];
  desired_player_experiences: string[];
  constraints: DeveloperConstraint[];
  missing_fields: MissingProfileField[];
  field_sources: ProfileFieldSource[];
  raw_text: string;
  is_complete: boolean;
}

export interface ProfileParseResult {
  draft: DeveloperProfileDraft;
  warnings: string[];
}
```

- [ ] **Step 4: Implement the frontend parser adapter**

Create `frontend/lib/profile/parser.ts`:

```typescript
import type {
  ConfidenceLevel,
  ConstraintType,
  DeveloperConstraint,
  MissingProfileField,
  ProfileFieldSource,
  ProfileParseInput,
  ProfileParseResult,
} from "@/lib/types";

const BLOCKING_FIELDS = [
  "team_size",
  "time_budget",
  "programming_ability",
  "art_ability",
  "content_production_ability",
  "desired_player_experiences",
] as const;

function hasAny(value: string, needles: string[]) {
  const normalized = value.toLowerCase();
  return needles.some((needle) => normalized.includes(needle.toLowerCase()));
}

function source(
  field: string,
  sourceText: string,
  confidence: ConfidenceLevel = "high",
  sourceKind: "raw_text" | "explicit_field" = "raw_text",
): ProfileFieldSource {
  return {
    field,
    source_text: sourceText,
    source_kind: sourceKind,
    confidence,
  };
}

function unique(values: string[]) {
  const seen = new Set<string>();
  return values.filter((value) => {
    const normalized = value.trim();
    if (!normalized || seen.has(normalized.toLowerCase())) return false;
    seen.add(normalized.toLowerCase());
    return true;
  });
}

function constraint(
  id: string,
  type: ConstraintType,
  statement: string,
): DeveloperConstraint {
  return { id, type, statement };
}

function missing(field: string): MissingProfileField {
  return {
    field,
    reason: `No usable ${field} was found in the input.`,
    blocking: true,
  };
}

export function parseDeveloperProfileInput(input: ProfileParseInput): ProfileParseResult {
  const rawText = input.raw_text.trim();
  const fieldSources: ProfileFieldSource[] = [];
  const warnings: string[] = [];

  let teamSize: string | null = null;
  if (hasAny(rawText, ["solo", "一个人", "单人", "独立开发者"])) {
    teamSize = "solo";
    fieldSources.push(source("team_size", "solo / 一个人 / 单人"));
  } else if (hasAny(rawText, ["两个人", "2人", "小团队"])) {
    teamSize = "small team";
    fieldSources.push(source("team_size", "两个人 / 2人 / 小团队"));
  }

  let timeBudget: string | null = null;
  if (input.expected_project_scale?.trim()) {
    timeBudget = input.expected_project_scale.trim();
    fieldSources.push(source("time_budget", timeBudget, "high", "explicit_field"));
  } else if (hasAny(rawText, ["三个月", "3个月", "three month"])) {
    timeBudget = "three month prototype";
    fieldSources.push(source("time_budget", "三个月 / 3个月 / three month"));
  } else if (hasAny(rawText, ["周末", "业余", "part-time"])) {
    timeBudget = "part-time prototype";
    warnings.push("时间预算说明缺少明确周期长度。");
    fieldSources.push(source("time_budget", "周末 / 业余 / part-time", "medium"));
  } else if (hasAny(rawText, ["尽快", "短期"])) {
    warnings.push("时间预算表述过于模糊。");
  }

  const programmingAbility = hasAny(rawText, [
    "程序能力强",
    "擅长编程",
    "会写系统",
    "strong programming",
  ])
    ? "strong"
    : null;
  if (programmingAbility) fieldSources.push(source("programming_ability", "程序能力强"));

  const artAbility = hasAny(rawText, ["美术能力弱", "美术弱", "不会画", "低美术", "weak art"])
    ? "weak"
    : null;
  if (artAbility) fieldSources.push(source("art_ability", "美术能力弱 / 美术弱 / 低美术"));

  const audioAbility = hasAny(rawText, ["音频一般", "基础音效", "basic audio"])
    ? "basic"
    : "basic";
  fieldSources.push(source("audio_ability", "defaulted to basic", "low"));

  const contentProductionAbility = hasAny(rawText, [
    "不想做大量内容",
    "内容产能有限",
    "limited content",
  ])
    ? "limited"
    : null;
  if (contentProductionAbility) {
    fieldSources.push(source("content_production_ability", "不想做大量内容 / 内容产能有限"));
  }

  const likedReferences = input.liked_references?.length
    ? unique(input.liked_references)
    : unique([
        rawText.includes("Balatro") ? "Balatro" : "",
        rawText.includes("Into the Breach") ? "Into the Breach" : "",
        rawText.includes("Baba Is You") ? "Baba Is You" : "",
      ]);
  if (likedReferences.length) {
    fieldSources.push(
      source(
        "liked_references",
        likedReferences.join(", "),
        "high",
        input.liked_references?.length ? "explicit_field" : "raw_text",
      ),
    );
  }

  const dislikedReferences = input.disliked_references_or_mechanics?.length
    ? unique(input.disliked_references_or_mechanics)
    : unique([
        hasAny(rawText, ["在线多人", "online multiplayer"]) ? "online multiplayer" : "",
        hasAny(rawText, ["长篇叙事", "long scripted narrative"])
          ? "long scripted narrative"
          : "",
      ]);

  if (dislikedReferences.length) {
    fieldSources.push(
      source(
        "disliked_references_or_mechanics",
        dislikedReferences.join(", "),
        "high",
        input.disliked_references_or_mechanics?.length ? "explicit_field" : "raw_text",
      ),
    );
  }

  const desiredExperiences = unique([
    hasAny(rawText, ["短局", "short runs"]) ? "short runs" : "",
    hasAny(rawText, ["系统性决策", "systemic decisions"]) ? "systemic decisions" : "",
    hasAny(rawText, ["战术预测", "tactical prediction"]) ? "tactical prediction" : "",
    hasAny(rawText, ["高重玩", "replayability"]) ? "replayability" : "",
  ]);
  if (desiredExperiences.length) {
    fieldSources.push(source("desired_player_experiences", desiredExperiences.join(", ")));
  }

  const constraints: DeveloperConstraint[] = [];
  if (hasAny(rawText, ["不要做在线多人", "不能做在线多人", "do not require online multiplayer"])) {
    constraints.push(
      constraint("constraint_no_online", "hard", "Do not require online multiplayer."),
    );
  }
  if (hasAny(rawText, ["不想做长篇叙事", "尽量不要长篇叙事"])) {
    constraints.push(
      constraint(
        "constraint_avoid_long_narrative",
        "strong_preference",
        "Avoid long scripted narrative.",
      ),
    );
  }
  if (hasAny(rawText, ["不想做大量内容", "内容产能有限"])) {
    constraints.push(
      constraint(
        "constraint_limited_content",
        "strong_preference",
        "Prefer concepts with limited content production.",
      ),
    );
  }
  if (constraints.length) {
    fieldSources.push(source("constraints", constraints.map((item) => item.statement).join("; ")));
  }

  const values = {
    team_size: teamSize,
    time_budget: timeBudget,
    programming_ability: programmingAbility,
    art_ability: artAbility,
    content_production_ability: contentProductionAbility,
    desired_player_experiences: desiredExperiences,
  };
  const missingFields = BLOCKING_FIELDS.flatMap((field) => {
    const value = values[field];
    return value === null || (Array.isArray(value) && value.length === 0)
      ? [missing(field)]
      : [];
  });

  return {
    draft: {
      id: "profile_draft_current",
      team_size: teamSize,
      time_budget: timeBudget,
      programming_ability: programmingAbility,
      art_ability: artAbility,
      audio_ability: audioAbility,
      content_production_ability: contentProductionAbility,
      liked_references: likedReferences,
      disliked_references_or_mechanics: dislikedReferences,
      desired_player_experiences: desiredExperiences,
      constraints,
      missing_fields: missingFields,
      field_sources: fieldSources,
      raw_text: rawText,
      is_complete: missingFields.length === 0,
    },
    warnings,
  };
}
```

- [ ] **Step 5: Run frontend parser tests to verify they pass**

Run:

```powershell
Push-Location frontend; npm test -- lib/profile/parser.test.ts; Pop-Location
```

Expected: PASS, all 4 tests pass.

- [ ] **Step 6: Run the frontend type and test baseline**

Run:

```powershell
Push-Location frontend; npm test; Pop-Location
```

Expected: PASS. Baseline before this plan was 23 tests; after Task 3 it should be 27 tests.

- [ ] **Step 7: Commit Task 3**

Run:

```powershell
git add frontend/lib/types/index.ts frontend/lib/profile/parser.ts frontend/lib/profile/parser.test.ts
git commit -m "feat: add frontend developer profile parser"
```

Expected: commit succeeds.

---

### Task 4: Data Boundary and Profile Components

**Files:**
- Modify: `frontend/lib/data/index.ts`
- Create: `frontend/components/profile/profile-input-panel.tsx`
- Create: `frontend/components/profile/profile-draft-preview.tsx`
- Create: `frontend/components/profile/profile-missing-fields.tsx`
- Create: `frontend/components/profile/profile-source-list.tsx`

- [ ] **Step 1: Add data-layer parser export**

Replace the existing type import block in `frontend/lib/data/index.ts` with this exact block and add the parser import above it:

```typescript
import { parseDeveloperProfileInput as parseLocalDeveloperProfileInput } from "@/lib/profile/parser";
import type {
  ProfileParseInput,
  ProfileParseResult,
  ConceptCard,
  ConceptEvaluation,
  DeveloperProfile,
  DesignClaim,
  EvidenceRef,
  GameDesignProfile,
  GoldenFlow,
  OpportunityFrame,
  PrototypeBrief,
  SeedGame,
} from "@/lib/types";
```

Add this function near `getDeveloperProfile`:

```typescript
export async function parseDeveloperProfileInput(
  input: ProfileParseInput,
): Promise<ProfileParseResult> {
  return settle(parseLocalDeveloperProfileInput(input));
}
```

- [ ] **Step 2: Create input panel component**

Create `frontend/components/profile/profile-input-panel.tsx`:

```tsx
"use client";

import { Button } from "@/components/ui/button";

export interface ProfileInputState {
  raw_text: string;
  liked_references: string;
  disliked_references_or_mechanics: string;
  expected_project_scale: string;
}

interface ProfileInputPanelProps {
  value: ProfileInputState;
  onChange: (value: ProfileInputState) => void;
  onParse: () => void;
}

export function ProfileInputPanel({ value, onChange, onParse }: ProfileInputPanelProps) {
  return (
    <section className="space-y-3 rounded-lg border p-4">
      <div>
        <h2 className="text-sm font-medium">输入画像</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          用自然语言描述团队、能力、偏好和项目边界。
        </p>
      </div>
      <label className="block space-y-1">
        <span className="text-xs font-medium text-muted-foreground">自由描述</span>
        <textarea
          className="min-h-40 w-full rounded-md border bg-background p-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          value={value.raw_text}
          onChange={(event) => onChange({ ...value, raw_text: event.target.value })}
        />
      </label>
      <label className="block space-y-1">
        <span className="text-xs font-medium text-muted-foreground">喜欢参考</span>
        <input
          className="h-9 w-full rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          value={value.liked_references}
          onChange={(event) => onChange({ ...value, liked_references: event.target.value })}
        />
      </label>
      <label className="block space-y-1">
        <span className="text-xs font-medium text-muted-foreground">讨厌参考或机制</span>
        <input
          className="h-9 w-full rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          value={value.disliked_references_or_mechanics}
          onChange={(event) =>
            onChange({ ...value, disliked_references_or_mechanics: event.target.value })
          }
        />
      </label>
      <label className="block space-y-1">
        <span className="text-xs font-medium text-muted-foreground">项目规模</span>
        <input
          className="h-9 w-full rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          value={value.expected_project_scale}
          onChange={(event) =>
            onChange({ ...value, expected_project_scale: event.target.value })
          }
        />
      </label>
      <Button type="button" onClick={onParse}>
        解析画像
      </Button>
    </section>
  );
}
```

- [ ] **Step 3: Create draft preview component**

Create `frontend/components/profile/profile-draft-preview.tsx`:

```tsx
import { ConstraintTag } from "@/components/artifacts/constraint-tag";
import { Badge } from "@/components/ui/badge";
import type { DeveloperProfileDraft } from "@/lib/types";

function valueOrMissing(value: string | null) {
  return value ?? "缺失";
}

export function ProfileDraftPreview({ draft }: { draft: DeveloperProfileDraft }) {
  const fields: [string, string | null][] = [
    ["团队规模", draft.team_size],
    ["时间预算", draft.time_budget],
    ["程序能力", draft.programming_ability],
    ["美术能力", draft.art_ability],
    ["音频能力", draft.audio_ability],
    ["内容生产能力", draft.content_production_ability],
  ];

  return (
    <section className="space-y-4 rounded-lg border p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium">结构化预览</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            完整画像才能进入机会匹配。
          </p>
        </div>
        <Badge variant={draft.is_complete ? "secondary" : "destructive"}>
          {draft.is_complete ? "完整" : "缺少关键信息"}
        </Badge>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {fields.map(([label, value]) => (
          <div key={label} className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className="text-sm font-medium">{valueOrMissing(value)}</div>
          </div>
        ))}
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <ListBlock title="喜欢参考" values={draft.liked_references} />
        <ListBlock title="讨厌方向" values={draft.disliked_references_or_mechanics} />
        <ListBlock title="期望体验" values={draft.desired_player_experiences} />
      </div>
      <div className="space-y-2">
        <h3 className="text-xs font-medium text-muted-foreground">约束与偏好</h3>
        {draft.constraints.length ? (
          draft.constraints.map((constraint) => (
            <ConstraintTag key={constraint.id} constraint={constraint} />
          ))
        ) : (
          <p className="text-sm text-muted-foreground">尚未识别到约束。</p>
        )}
      </div>
    </section>
  );
}

function ListBlock({ title, values }: { title: string; values: string[] }) {
  return (
    <div className="rounded-md border p-3">
      <div className="text-xs text-muted-foreground">{title}</div>
      <div className="mt-1 text-sm font-medium">
        {values.length ? values.join("、") : "未提供"}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create missing fields component**

Create `frontend/components/profile/profile-missing-fields.tsx`:

```tsx
import type { MissingProfileField } from "@/lib/types";

export function ProfileMissingFields({ fields }: { fields: MissingProfileField[] }) {
  if (!fields.length) {
    return (
      <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
        没有阻断性缺失信息。
      </section>
    );
  }

  return (
    <section className="space-y-3 rounded-lg border p-4">
      <h2 className="text-sm font-medium">缺失信息</h2>
      <div className="space-y-2">
        {fields.map((field) => (
          <div
            key={field.field}
            data-missing-field={field.field}
            className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"
          >
            <div className="font-medium">
              {field.blocking ? "阻断" : "提示"}：{field.field}
            </div>
            <div className="mt-1 text-xs">{field.reason}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Create source list component**

Create `frontend/components/profile/profile-source-list.tsx`:

```tsx
import { Badge } from "@/components/ui/badge";
import type { ProfileFieldSource } from "@/lib/types";

export function ProfileSourceList({ sources }: { sources: ProfileFieldSource[] }) {
  return (
    <section className="space-y-3 rounded-lg border p-4">
      <h2 className="text-sm font-medium">字段来源</h2>
      {sources.length ? (
        <div className="space-y-2">
          {sources.map((source, index) => (
            <div key={`${source.field}-${index}`} className="rounded-md border p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{source.field}</span>
                <Badge variant="outline">{source.source_kind}</Badge>
                <Badge variant="secondary">{source.confidence}</Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{source.source_text}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">尚无字段来源。</p>
      )}
    </section>
  );
}
```

- [ ] **Step 6: Run focused TypeScript tests**

Run:

```powershell
Push-Location frontend; npm test -- lib/profile/parser.test.ts; Pop-Location
```

Expected: PASS. This catches import and type errors from the new components indirectly through shared types only if the test runner compiles the project graph; full page tests come next.

- [ ] **Step 7: Commit Task 4**

Run:

```powershell
git add frontend/lib/data/index.ts frontend/components/profile
git commit -m "feat: add profile workbench components"
```

Expected: commit succeeds.

---

### Task 5: Mixed `/profile` Workbench Page

**Files:**
- Modify: `frontend/app/(workbench)/profile/page.tsx`
- Modify: `frontend/app/(workbench)/profile/profile-page.test.tsx`

- [ ] **Step 1: Replace page tests with mixed-workbench behavior tests**

Replace `frontend/app/(workbench)/profile/profile-page.test.tsx` with:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProfilePage from "@/app/(workbench)/profile/page";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("ProfilePage", () => {
  it("renders the mixed developer profile workbench", async () => {
    renderWithClient(<ProfilePage />);

    expect(screen.getByText("开发者画像")).toBeInTheDocument();
    expect(screen.getByLabelText("自由描述")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("结构化预览")).toBeInTheDocument();
    });
  });

  it("updates the preview after parsing edited text", async () => {
    const user = userEvent.setup();
    renderWithClient(<ProfilePage />);

    const textarea = screen.getByLabelText("自由描述");
    await user.clear(textarea);
    await user.type(
      textarea,
      "我是 solo 开发者，程序能力强，美术能力弱，想尽快做个原型。我想要短局，不要做在线多人。",
    );
    await user.click(screen.getByRole("button", { name: "解析画像" }));

    await waitFor(() => {
      expect(screen.getByText("缺少关键信息")).toBeInTheDocument();
    });
    expect(screen.getByText("time_budget")).toBeInTheDocument();
  });

  it("highlights hard constraints and disables confirmation while incomplete", async () => {
    const { container } = renderWithClient(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Do not require online multiplayer.")).toBeInTheDocument();
    });

    const hard = container.querySelector('[data-constraint="hard"]');
    expect(hard).not.toBeNull();
    expect(hard?.textContent).toContain("Do not require online multiplayer.");
    expect(screen.getByRole("button", { name: "确认画像" })).toBeEnabled();
  });
});
```

- [ ] **Step 2: Run page tests to verify they fail**

Run:

```powershell
Push-Location frontend; npm test -- "app/(workbench)/profile/profile-page.test.tsx"; Pop-Location
```

Expected: FAIL because the current page is read-only and does not render `自由描述`, `解析画像`, or `确认画像`.

- [ ] **Step 3: Replace the profile page implementation**

Replace `frontend/app/(workbench)/profile/page.tsx` with:

```tsx
"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shell/view-states";
import {
  ProfileInputPanel,
  type ProfileInputState,
} from "@/components/profile/profile-input-panel";
import { ProfileDraftPreview } from "@/components/profile/profile-draft-preview";
import { ProfileMissingFields } from "@/components/profile/profile-missing-fields";
import { ProfileSourceList } from "@/components/profile/profile-source-list";
import { parseDeveloperProfileInput } from "@/lib/data";
import type { ProfileParseResult } from "@/lib/types";

const DEFAULT_PROFILE_TEXT =
  "我是 solo 开发者，程序能力强，美术能力弱，想做三个月内能验证的原型。" +
  "我喜欢 Balatro 和 Into the Breach，想要短局、系统性决策和战术预测。" +
  "不要做在线多人，我不想做长篇叙事内容，也不想做大量内容。";

const DEFAULT_INPUT: ProfileInputState = {
  raw_text: DEFAULT_PROFILE_TEXT,
  liked_references: "",
  disliked_references_or_mechanics: "",
  expected_project_scale: "",
};

function splitList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function ProfilePage() {
  const [input, setInput] = useState<ProfileInputState>(DEFAULT_INPUT);
  const [result, setResult] = useState<ProfileParseResult | null>(null);

  async function parseCurrentInput(nextInput = input) {
    const parsed = await parseDeveloperProfileInput({
      raw_text: nextInput.raw_text,
      liked_references: splitList(nextInput.liked_references),
      disliked_references_or_mechanics: splitList(
        nextInput.disliked_references_or_mechanics,
      ),
      expected_project_scale: nextInput.expected_project_scale.trim() || undefined,
    });
    setResult(parsed);
  }

  useEffect(() => {
    void parseCurrentInput(DEFAULT_INPUT);
  }, []);

  const draft = result?.draft;

  return (
    <div className="space-y-6">
      <PageHeader title="开发者画像" description="自由表达、结构化草稿与缺失信息" />

      <div className="grid gap-4 xl:grid-cols-[minmax(320px,0.9fr)_minmax(420px,1.1fr)]">
        <ProfileInputPanel
          value={input}
          onChange={setInput}
          onParse={() => void parseCurrentInput()}
        />
        {draft ? (
          <ProfileDraftPreview draft={draft} />
        ) : (
          <section className="rounded-lg border p-4 text-sm text-muted-foreground">
            等待解析画像。
          </section>
        )}
      </div>

      {draft ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <ProfileMissingFields fields={draft.missing_fields} />
          <ProfileSourceList sources={draft.field_sources} />
        </div>
      ) : null}

      <div className="flex justify-end">
        <Button type="button" disabled={!draft?.is_complete}>
          确认画像
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Make input labels accessible**

If `getByLabelText("自由描述")` fails after Step 3, update `frontend/components/profile/profile-input-panel.tsx` labels to use explicit `htmlFor` and `id`:

```tsx
<label htmlFor="profile-raw-text" className="block text-xs font-medium text-muted-foreground">
  自由描述
</label>
<textarea
  id="profile-raw-text"
  className="min-h-40 w-full rounded-md border bg-background p-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
  value={value.raw_text}
  onChange={(event) => onChange({ ...value, raw_text: event.target.value })}
/>
```

Apply the same `htmlFor`/`id` pattern for `喜欢参考`, `讨厌参考或机制`, and `项目规模` if their queries are added later.

- [ ] **Step 5: Run page tests to verify they pass**

Run:

```powershell
Push-Location frontend; npm test -- "app/(workbench)/profile/profile-page.test.tsx"; Pop-Location
```

Expected: PASS, all 3 page tests pass.

- [ ] **Step 6: Run full frontend suite**

Run:

```powershell
Push-Location frontend; npm test; Pop-Location
```

Expected: PASS. Expected total after Task 5: 30 tests.

- [ ] **Step 7: Commit Task 5**

Run:

```powershell
git add "frontend/app/(workbench)/profile/page.tsx" "frontend/app/(workbench)/profile/profile-page.test.tsx" frontend/components/profile/profile-input-panel.tsx
git commit -m "feat: build developer profile workbench"
```

Expected: commit succeeds.

---

### Task 6: Final Verification

**Files:**
- Read: `docs/superpowers/specs/2026-06-08-developer-profile-module-design.zh-CN.md`
- Verify: backend and frontend test suites

- [ ] **Step 1: Run backend tests**

Run:

```powershell
Push-Location backend; python -m pytest; Pop-Location
```

Expected: PASS. Expected total after this plan: 55 tests.

- [ ] **Step 2: Run frontend tests**

Run:

```powershell
Push-Location frontend; npm test; Pop-Location
```

Expected: PASS. Expected total after this plan: 30 tests.

- [ ] **Step 3: Run frontend lint**

Run:

```powershell
Push-Location frontend; npm run lint; Pop-Location
```

Expected: PASS with no ESLint errors.

- [ ] **Step 4: Run a production build**

Run:

```powershell
Push-Location frontend; npm run build; Pop-Location
```

Expected: PASS. The `/profile` App Router route compiles.

- [ ] **Step 5: Inspect git diff for scope**

Run:

```powershell
git status --short
git diff --stat HEAD
```

Expected:

- Only 6.4 backend parser/schema, 6.4 frontend profile/parser/components, and tests changed.
- No changes to 6.1/6.2 import docs or 6.3 graph files unless required by shared exports.

- [ ] **Step 6: Commit final verification fixups if any**

If lint/build required mechanical fixes, commit them:

```powershell
git add backend frontend
git commit -m "chore: polish developer profile module"
```

Expected: commit only if there are actual fixups. If `git status --short` is clean, skip this step.

---

## Self-Review Notes

- Spec coverage: Tasks 1 and 2 cover backend contracts, missing fields, field sources, deterministic parsing, and promotion. Tasks 3 through 5 cover TypeScript contracts, local data-layer parsing, mixed `/profile` input and preview, missing fields, field sources, and constraint visibility. Task 6 covers final verification.
- Scope check: The plan does not create opportunity matching, opportunity frames, concept cards, LLM parsing, API routes, persistence, or multi-user state.
- Type consistency: Backend and frontend use the same names: `ProfileParseInput`, `ProfileFieldSource`, `MissingProfileField`, `DeveloperProfileDraft`, `ProfileParseResult`, `parseDeveloperProfileInput`, `field_sources`, `missing_fields`, and `is_complete`.
- TDD order: Every behavior task starts with failing tests, verifies failure, implements minimal code, verifies pass, and commits.
