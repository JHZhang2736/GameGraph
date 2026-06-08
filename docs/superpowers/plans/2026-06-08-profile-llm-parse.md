# Profile LLM Parse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the deterministic developer-profile parser with an LLM-extraction + rule-adjudication backend endpoint (`POST /profile/parse`), and point the frontend at it with a local fallback.

**Architecture:** A new OpenAI-compatible LLM client (configured via env) does fuzzy field extraction with tool calling. A shared `finalize_completeness` (extracted from the existing parser) and explicit-field override run deterministically over the extraction, so `is_complete`/`missing_fields`/promotion stay code-owned. Any LLM failure or missing config falls back to the existing rule parser. The frontend `lib/data` layer swaps its local call for `fetch`, falling back to the local parser on network error.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, httpx (incl. `httpx.MockTransport`), pytest; Next.js App Router, TypeScript, Vitest.

---

## File Structure

- Modify `backend/app/services/developer_profile_parser.py`: extract `finalize_completeness`; reuse it in `parse_developer_profile_input`.
- Create `backend/app/services/profile_llm.py`: `LlmSettings`, extraction schemas, `build_tool_schema`, `ProfileLlmClient`, `get_llm_client`.
- Create `backend/app/services/profile_parse_service.py`: `parse_profile` orchestration (LLM → override → finalize, with fallback).
- Create `backend/app/api/routes_profile.py`: `POST /profile/parse`.
- Modify `backend/app/main.py`: mount the profile router.
- Create `backend/tests/test_profile_llm.py`, `backend/tests/test_profile_parse_service.py`, `backend/tests/test_profile_api.py`.
- Modify `backend/.env.example`: add `LLM_*` vars.
- Modify `frontend/lib/data/index.ts`: `parseDeveloperProfileInput` calls `fetch` with local fallback.
- Create `frontend/lib/data/parse.test.ts`: fetch success + fallback.
- Modify `frontend/vitest.setup.ts`: default-reject `fetch` so other tests stay network-free.
- Create `frontend/.env.example`: `NEXT_PUBLIC_API_BASE_URL`.

---

### Task 1: Extract shared completeness logic

**Files:**
- Modify: `backend/app/services/developer_profile_parser.py`
- Test: `backend/tests/test_developer_profile_parser.py` (add one test)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_developer_profile_parser.py`:

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `Push-Location backend; python -m pytest tests/test_developer_profile_parser.py::test_finalize_completeness_flags_only_empty_blocking_fields -v; Pop-Location`
Expected: FAIL with `ImportError: cannot import name 'finalize_completeness'`.

- [ ] **Step 3: Add `finalize_completeness` and reuse it**

In `backend/app/services/developer_profile_parser.py`, add this function above `parse_developer_profile_input` (after the `_constraints` helper):

```python
def finalize_completeness(
    values: dict[str, object],
) -> tuple[list[MissingProfileField], bool]:
    missing_fields = [
        _missing(field, f"Could not infer {field} from developer profile input.")
        for field, value in values.items()
        if field in BLOCKING_FIELDS and not value
    ]
    is_complete = not any(field.blocking for field in missing_fields)
    return missing_fields, is_complete
```

Then replace the inline missing-fields block inside `parse_developer_profile_input` (the `missing_fields = [...]` list comprehension and the `is_complete = ...` line) with:

```python
    missing_fields, is_complete = finalize_completeness(
        {
            "team_size": team_size,
            "time_budget": time_budget,
            "programming_ability": programming_ability,
            "art_ability": art_ability,
            "content_production_ability": content_production_ability,
            "liked_references": liked_references,
            "desired_player_experiences": desired_player_experiences,
            "constraints": constraints,
        }
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `Push-Location backend; python -m pytest tests/test_developer_profile_parser.py tests/test_developer_profile_contracts.py -v; Pop-Location`
Expected: PASS, all existing parser/contract tests plus the new one.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/developer_profile_parser.py backend/tests/test_developer_profile_parser.py
git commit -m "refactor: extract finalize_completeness from profile parser"
```

---

### Task 2: LLM client and extraction schema

**Files:**
- Create: `backend/app/services/profile_llm.py`
- Test: `backend/tests/test_profile_llm.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_profile_llm.py`:

```python
import json

import httpx
import pytest

from app.schemas.common import ConfidenceLevel, ConstraintType
from app.schemas.developer_profile import ProfileParseInput
from app.services.profile_llm import (
    LlmSettings,
    ProfileExtraction,
    ProfileLlmClient,
    build_tool_schema,
    get_llm_client,
)


def _settings() -> LlmSettings:
    return LlmSettings(
        base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        timeout=5.0,
    )


def _extraction_arguments() -> str:
    return json.dumps(
        {
            "team_size": "solo",
            "time_budget": "three month prototype",
            "programming_ability": "strong",
            "art_ability": "weak",
            "audio_ability": None,
            "content_production_ability": "limited",
            "liked_references": ["Hades"],
            "disliked_references_or_mechanics": ["online multiplayer"],
            "desired_player_experiences": ["short runs"],
            "constraints": [
                {"type": "hard", "statement": "Do not require online multiplayer."}
            ],
            "field_sources": [
                {"field": "team_size", "source_text": "我一个人做", "confidence": "high"}
            ],
            "warnings": [],
        }
    )


def test_build_tool_schema_exposes_function_name() -> None:
    tools = build_tool_schema()
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "emit_developer_profile"
    assert "parameters" in tools[0]["function"]


def test_extract_posts_tool_call_request_and_parses_arguments() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        body = json.loads(request.content)
        seen["body"] = body
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "emit_developer_profile",
                                        "arguments": _extraction_arguments(),
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
        )

    client = ProfileLlmClient(
        _settings(), httpx.Client(transport=httpx.MockTransport(handler))
    )
    extraction = client.extract(ProfileParseInput(raw_text="我一个人做游戏"))

    assert isinstance(extraction, ProfileExtraction)
    assert extraction.team_size == "solo"
    assert extraction.audio_ability is None
    assert extraction.constraints[0].type == ConstraintType.HARD
    assert extraction.field_sources[0].confidence == ConfidenceLevel.HIGH
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["auth"] == "Bearer secret"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["tool_choice"]["function"]["name"] == "emit_developer_profile"


def test_extract_raises_when_no_tool_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    client = ProfileLlmClient(
        _settings(), httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(ValueError, match="tool_call"):
        client.extract(ProfileParseInput(raw_text="solo"))


def test_get_llm_client_returns_none_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    assert get_llm_client() is None


def test_get_llm_client_builds_client_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_API_KEY", "secret")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    client = get_llm_client()
    assert isinstance(client, ProfileLlmClient)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `Push-Location backend; python -m pytest tests/test_profile_llm.py -v; Pop-Location`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.profile_llm'`.

- [ ] **Step 3: Implement `profile_llm.py`**

Create `backend/app/services/profile_llm.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
from pydantic import Field

from app.schemas.common import ConfidenceLevel, ConstraintType, StrictBaseModel
from app.schemas.developer_profile import ProfileParseInput

TOOL_NAME = "emit_developer_profile"

SYSTEM_PROMPT = (
    "你是独立游戏创意系统的开发者画像抽取器。"
    "从开发者的自由表达中抽取结构化画像字段，并通过工具调用返回。"
    "区分硬性约束(hard)、强偏好(strong_preference)、软偏好(soft_preference)；"
    "不要把喜欢的游戏当成约束。"
    "每个抽取出的关键字段都尽量给出原文片段作为来源。"
    "无法判断的字段返回 null 或空列表，不要编造。"
)


@dataclass(frozen=True)
class LlmSettings:
    base_url: str
    api_key: str
    model: str
    timeout: float

    @classmethod
    def from_env(cls) -> "LlmSettings":
        return cls(
            base_url=os.environ.get("LLM_BASE_URL", "").strip(),
            api_key=os.environ.get("LLM_API_KEY", "").strip(),
            model=os.environ.get("LLM_MODEL", "").strip(),
            timeout=float(os.environ.get("LLM_TIMEOUT", "30")),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)


class ExtractedConstraint(StrictBaseModel):
    type: ConstraintType
    statement: str = Field(min_length=1)


class ExtractedSource(StrictBaseModel):
    field: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
    confidence: ConfidenceLevel


class ProfileExtraction(StrictBaseModel):
    team_size: str | None = None
    time_budget: str | None = None
    programming_ability: str | None = None
    art_ability: str | None = None
    audio_ability: str | None = None
    content_production_ability: str | None = None
    liked_references: list[str] = Field(default_factory=list)
    disliked_references_or_mechanics: list[str] = Field(default_factory=list)
    desired_player_experiences: list[str] = Field(default_factory=list)
    constraints: list[ExtractedConstraint] = Field(default_factory=list)
    field_sources: list[ExtractedSource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def build_tool_schema() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": "Return the structured developer profile extracted from the input.",
                "parameters": ProfileExtraction.model_json_schema(),
            },
        }
    ]


def _user_message(input_data: ProfileParseInput) -> str:
    lines = [f"自由描述：{input_data.raw_text}"]
    if input_data.liked_references:
        lines.append(f"显式喜欢参考：{', '.join(input_data.liked_references)}")
    if input_data.disliked_references_or_mechanics:
        lines.append(
            f"显式讨厌参考或机制：{', '.join(input_data.disliked_references_or_mechanics)}"
        )
    if input_data.expected_project_scale:
        lines.append(f"显式项目规模：{input_data.expected_project_scale}")
    return "\n".join(lines)


class ProfileLlmClient:
    def __init__(self, settings: LlmSettings, http_client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout)

    def extract(self, input_data: ProfileParseInput) -> ProfileExtraction:
        payload = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_message(input_data)},
            ],
            "tools": build_tool_schema(),
            "tool_choice": {"type": "function", "function": {"name": TOOL_NAME}},
        }
        response = self._client.post(
            f"{self._settings.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self._settings.api_key}"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        tool_calls = data["choices"][0]["message"].get("tool_calls") or []
        if not tool_calls:
            raise ValueError("LLM response missing tool_call")
        arguments = tool_calls[0]["function"]["arguments"]
        return ProfileExtraction.model_validate_json(arguments)


def get_llm_client() -> ProfileLlmClient | None:
    settings = LlmSettings.from_env()
    if not settings.is_configured:
        return None
    return ProfileLlmClient(settings)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `Push-Location backend; python -m pytest tests/test_profile_llm.py -v; Pop-Location`
Expected: PASS, all 5 tests.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/profile_llm.py backend/tests/test_profile_llm.py
git commit -m "feat: add OpenAI-compatible profile LLM client"
```

---

### Task 3: Parse orchestration service

**Files:**
- Create: `backend/app/services/profile_parse_service.py`
- Test: `backend/tests/test_profile_parse_service.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_profile_parse_service.py`:

```python
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
            ExtractedSource(field="team_size", source_text="我一个人做", confidence="high")
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `Push-Location backend; python -m pytest tests/test_profile_parse_service.py -v; Pop-Location`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.profile_parse_service'`.

- [ ] **Step 3: Implement `profile_parse_service.py`**

Create `backend/app/services/profile_parse_service.py`:

```python
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


def _result_from_extraction(
    input_data: ProfileParseInput,
    extraction: ProfileExtraction,
) -> ProfileParseResult:
    time_budget = extraction.time_budget
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
            "team_size": extraction.team_size,
            "time_budget": time_budget,
            "programming_ability": extraction.programming_ability,
            "art_ability": extraction.art_ability,
            "content_production_ability": extraction.content_production_ability,
            "liked_references": liked,
            "desired_player_experiences": extraction.desired_player_experiences,
            "constraints": constraints,
        }
    )

    draft = DeveloperProfileDraft(
        id="profile_draft_current",
        team_size=extraction.team_size,
        time_budget=time_budget,
        programming_ability=extraction.programming_ability,
        art_ability=extraction.art_ability,
        audio_ability=extraction.audio_ability or "basic",
        content_production_ability=extraction.content_production_ability,
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `Push-Location backend; python -m pytest tests/test_profile_parse_service.py -v; Pop-Location`
Expected: PASS, all 5 tests.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/profile_parse_service.py backend/tests/test_profile_parse_service.py
git commit -m "feat: add profile parse orchestration with LLM and rule fallback"
```

---

### Task 4: `POST /profile/parse` endpoint

**Files:**
- Create: `backend/app/api/routes_profile.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_profile_api.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_profile_api.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes_profile import get_llm_client
from app.schemas.common import ConstraintType
from app.services.profile_llm import ExtractedConstraint, ExtractedSource, ProfileExtraction


class FakeClient:
    def extract(self, input_data) -> ProfileExtraction:
        return ProfileExtraction(
            team_size="solo",
            time_budget="three month prototype",
            programming_ability="strong",
            art_ability="weak",
            content_production_ability="limited",
            liked_references=["Hades"],
            desired_player_experiences=["short runs"],
            constraints=[
                ExtractedConstraint(type=ConstraintType.HARD, statement="Do not require online multiplayer.")
            ],
            field_sources=[
                ExtractedSource(field="team_size", source_text="我一个人做", confidence="high")
            ],
            warnings=[],
        )


@pytest.fixture()
def client() -> TestClient:
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def test_parse_uses_llm_client_when_present(client: TestClient) -> None:
    app.dependency_overrides[get_llm_client] = lambda: FakeClient()
    response = client.post("/profile/parse", json={"raw_text": "我一个人做游戏"})
    assert response.status_code == 200
    body = response.json()
    assert body["draft"]["team_size"] == "solo"
    assert body["draft"]["is_complete"] is True
    assert body["draft"]["audio_ability"] == "basic"


def test_parse_falls_back_to_rules_when_unconfigured(client: TestClient) -> None:
    app.dependency_overrides[get_llm_client] = lambda: None
    response = client.post(
        "/profile/parse",
        json={
            "raw_text": (
                "我是 solo 开发者，程序能力强，美术能力弱，三个月原型。"
                "我喜欢 Balatro，想要短局，不要做在线多人，也不想做大量内容。"
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["draft"]["is_complete"] is True


def test_parse_rejects_blank_text_with_422(client: TestClient) -> None:
    app.dependency_overrides[get_llm_client] = lambda: None
    response = client.post("/profile/parse", json={"raw_text": "   "})
    assert response.status_code == 422
```

- [ ] **Step 2: Run it to verify it fails**

Run: `Push-Location backend; python -m pytest tests/test_profile_api.py -v; Pop-Location`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.api.routes_profile'`.

- [ ] **Step 3: Implement the router and mount it**

Create `backend/app/api/routes_profile.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.schemas.developer_profile import ProfileParseInput, ProfileParseResult
from app.services.profile_llm import ProfileLlmClient, get_llm_client
from app.services.profile_parse_service import parse_profile

router = APIRouter()


@router.post("/profile/parse", response_model=ProfileParseResult)
def parse_profile_endpoint(
    document: ProfileParseInput,
    client: ProfileLlmClient | None = Depends(get_llm_client),
) -> ProfileParseResult:
    return parse_profile(document, client)
```

In `backend/app/main.py`, add the import and mount. Change:

```python
from app.api.routes_import import router
```

to:

```python
from app.api.routes_import import router
from app.api.routes_profile import router as profile_router
```

and after `app.include_router(router)` add:

```python
app.include_router(profile_router)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `Push-Location backend; python -m pytest tests/test_profile_api.py -v; Pop-Location`
Expected: PASS, all 3 tests.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/api/routes_profile.py backend/app/main.py backend/tests/test_profile_api.py
git commit -m "feat: add POST /profile/parse endpoint"
```

---

### Task 5: Backend env example + full suite

**Files:**
- Modify: `backend/.env.example`

- [ ] **Step 1: Add LLM vars to `backend/.env.example`**

Append to `backend/.env.example`:

```
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_TIMEOUT=30
```

- [ ] **Step 2: Run the full backend suite (excluding integration)**

Run: `Push-Location backend; python -m pytest; Pop-Location`
Expected: PASS. Baseline was 59 tests; after Tasks 1-4 expect 59 + 1 + 5 + 5 + 3 = 73.

- [ ] **Step 3: Commit**

```powershell
git add backend/.env.example
git commit -m "chore: document LLM env vars"
```

---

### Task 6: Frontend fetch with local fallback

**Files:**
- Modify: `frontend/lib/data/index.ts`
- Modify: `frontend/vitest.setup.ts`
- Create: `frontend/lib/data/parse.test.ts`
- Create: `frontend/.env.example`

- [ ] **Step 1: Make `fetch` default-reject in the test setup**

Append to `frontend/vitest.setup.ts`:

```typescript
import { vi } from "vitest";

// Tests must not hit the network. Suites that exercise fetch override this
// per-test (vi.stubGlobal / spyOn); everything else falls back to local logic.
vi.stubGlobal(
  "fetch",
  vi.fn(() => Promise.reject(new Error("network disabled in tests"))),
);
```

- [ ] **Step 2: Write the failing test**

Create `frontend/lib/data/parse.test.ts`:

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import { parseDeveloperProfileInput } from "@/lib/data";
import type { ProfileParseResult } from "@/lib/types";

const backendResult: ProfileParseResult = {
  draft: {
    id: "profile_draft_current",
    team_size: "solo",
    time_budget: "three month prototype",
    programming_ability: "strong",
    art_ability: "weak",
    audio_ability: "basic",
    content_production_ability: "limited",
    liked_references: ["Hades"],
    disliked_references_or_mechanics: [],
    desired_player_experiences: ["short runs"],
    constraints: [],
    missing_fields: [],
    field_sources: [],
    raw_text: "我一个人做游戏",
    is_complete: true,
  },
  warnings: [],
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("parseDeveloperProfileInput", () => {
  it("returns the backend result when the request succeeds", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(new Response(JSON.stringify(backendResult), { status: 200 })),
      ),
    );

    const result = await parseDeveloperProfileInput({ raw_text: "我一个人做游戏" });
    expect(result.draft.team_size).toBe("solo");
    expect(result.warnings).toEqual([]);
  });

  it("falls back to the local parser when the request fails", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));

    const result = await parseDeveloperProfileInput({
      raw_text:
        "我是 solo 开发者，程序能力强，美术能力弱，三个月原型。" +
        "我喜欢 Balatro，想要短局，不要做在线多人，也不想做大量内容。",
    });

    expect(result.draft.team_size).toBe("solo");
    expect(result.warnings[0]).toBe("后端不可用，已使用本地规则解析。");
  });
});
```

- [ ] **Step 3: Run it to verify it fails**

Run: `Push-Location frontend; npm test -- --run lib/data/parse.test.ts; Pop-Location`
Expected: FAIL — the success case returns the local fallback (warning present) because `parseDeveloperProfileInput` does not yet call `fetch`.

- [ ] **Step 4: Implement fetch with fallback**

In `frontend/lib/data/index.ts`, replace the existing `parseDeveloperProfileInput` function body with:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function parseDeveloperProfileInput(
  input: ProfileParseInput,
): Promise<ProfileParseResult> {
  try {
    const response = await fetch(`${API_BASE}/profile/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    if (!response.ok) throw new Error(`profile/parse responded ${response.status}`);
    return (await response.json()) as ProfileParseResult;
  } catch (error) {
    console.warn("profile/parse failed; using local parser", error);
    const local = parseLocalDeveloperProfileInput(input);
    return {
      ...local,
      warnings: ["后端不可用，已使用本地规则解析。", ...local.warnings],
    };
  }
}
```

(Leave the `settle` helper and other functions unchanged; `parseLocalDeveloperProfileInput` is already imported.)

- [ ] **Step 5: Run it to verify it passes**

Run: `Push-Location frontend; npm test -- --run lib/data/parse.test.ts; Pop-Location`
Expected: PASS, both tests.

- [ ] **Step 6: Create `frontend/.env.example`**

Create `frontend/.env.example`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 7: Run the full frontend suite + lint**

Run: `Push-Location frontend; npm test -- --run; npm run lint; Pop-Location`
Expected: PASS. The existing parser/page tests stay green (they fall back locally via the rejecting `fetch` stub). New total: 41 + 2 = 43 tests.

- [ ] **Step 8: Commit**

```powershell
git add "frontend/lib/data/index.ts" "frontend/vitest.setup.ts" "frontend/lib/data/parse.test.ts" "frontend/.env.example"
git commit -m "feat: call POST /profile/parse with local parser fallback"
```

---

### Task 7: Final verification

**Files:**
- Read: `docs/superpowers/specs/2026-06-08-profile-llm-parse-design.zh-CN.md`
- Verify: backend + frontend suites, frontend build

- [ ] **Step 1: Backend tests**

Run: `Push-Location backend; python -m pytest; Pop-Location`
Expected: PASS, 73 tests.

- [ ] **Step 2: Frontend tests + lint + build**

Run: `Push-Location frontend; npm test -- --run; npm run lint; npm run build; Pop-Location`
Expected: PASS; `/profile` compiles.

- [ ] **Step 3: Inspect scope**

Run: `git status --short; git diff --stat origin/main HEAD`
Expected: only the spec/plan docs, backend profile_llm/profile_parse_service/routes_profile/parser refactor/env, and frontend lib/data/vitest.setup/env changed. No persistence, no 6.5/6.6 files, no changes to the profile page/components/types.

- [ ] **Step 4: Commit any mechanical fixups**

If lint/build required fixes, commit them; otherwise skip.

```powershell
git add backend frontend
git commit -m "chore: polish profile LLM parse"
```

---

## Self-Review Notes

- **Spec coverage:** §5 config → Tasks 2 (LlmSettings), 5 (backend env), 6 (frontend env). §6.1 client → Task 2. §6.2 finalize_completeness → Task 1. §6.3 orchestration/override/fallback → Task 3. §6.4 route → Task 4. §7 frontend fetch+fallback → Task 6. §9 degradation matrix → Tasks 3 (error/none) + 6 (frontend fetch fail). §10 tests → Tasks 1-4, 6. Persistence (§2 out of scope) → no task, intentionally.
- **Placeholder scan:** every code step shows full code; commands have expected output. None found.
- **Type consistency:** `ProfileExtraction`, `ExtractedConstraint`, `ExtractedSource`, `build_tool_schema`, `get_llm_client`, `ProfileLlmClient.extract`, `finalize_completeness(values) -> (missing, bool)`, `parse_profile(input, client)` are used identically across Tasks 2-4 and 6. Constraint ids `constraint_{n}` and `source_kind="explicit_field"` match the service tests.
- **Decision recorded:** audio defaults to `"basic"` in the LLM path (Task 3) so a complete draft never carries a null audio that would break `promote_draft_to_profile`, matching the rule parser.
