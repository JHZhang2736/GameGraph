# Backend Fixture Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first backend contract slice: Pydantic v2 artifact schemas, a deterministic golden fixture flow, and pytest coverage for cross-artifact rules.

**Architecture:** Create a small `backend/` Python package with schema models under `app/schemas`, a pure in-memory fixture pipeline under `app/services`, and one `golden_flow.json` fixture. The pipeline does not call APIs, Neo4j, or an LLM; it validates typed artifacts and checks contract rules.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, JSON fixtures.

---

## File Structure

- Create `backend/pyproject.toml`: backend package metadata, runtime dependencies, pytest settings.
- Create `backend/app/__init__.py`: marks the backend app package.
- Create `backend/app/schemas/__init__.py`: exports schema types for tests and later route code.
- Create `backend/app/schemas/common.py`: shared enums, strict base model, and `EvidenceRef`.
- Create `backend/app/schemas/artifacts.py`: core artifact models for the fixture flow.
- Create `backend/app/services/__init__.py`: marks the service package.
- Create `backend/app/services/fixture_pipeline.py`: fixture loading, graph relation construction, pipeline result, and contract validation.
- Create `backend/app/fixtures/golden_flow.json`: one complete deterministic fixture.
- Create `backend/tests/test_project_structure.py`: verifies backend skeleton and test discovery.
- Create `backend/tests/test_artifact_contracts.py`: schema contract tests.
- Create `backend/tests/test_fixture_pipeline.py`: golden flow and cross-artifact rule tests.

Run commands from repository root: `D:\Files\GameGraph`.

---

### Task 1: Backend Package Skeleton And Test Tooling

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/tests/test_project_structure.py`

- [ ] **Step 1: Create backend dependency metadata**

Create `backend/pyproject.toml` with this content:

```toml
[project]
name = "gamegraph-backend"
version = "0.1.0"
description = "Backend contract slice for the GameGraph fixture pipeline"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.7,<3",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2,<9",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Install backend test dependencies**

Run:

```powershell
python -m pip install -e "backend[dev]"
```

Expected: pip installs `pydantic` and `pytest`, and reports `Successfully installed` or `Requirement already satisfied`.

- [ ] **Step 3: Write the failing project structure test**

Create `backend/tests/test_project_structure.py` with this content:

```python
from pathlib import Path


def test_backend_package_structure_exists() -> None:
    backend_root = Path(__file__).resolve().parents[1]

    assert (backend_root / "app").is_dir()
    assert (backend_root / "app" / "schemas").is_dir()
    assert (backend_root / "app" / "services").is_dir()
```

- [ ] **Step 4: Run the structure test and verify it fails**

Run:

```powershell
python -m pytest backend/tests/test_project_structure.py -v
```

Expected: `FAILED` because `backend/app`, `backend/app/schemas`, and `backend/app/services` do not exist yet.

- [ ] **Step 5: Create package skeleton files**

Create these files with the shown content.

`backend/app/__init__.py`:

```python
"""GameGraph backend package."""
```

`backend/app/schemas/__init__.py`:

```python
"""Pydantic schemas for GameGraph backend artifacts."""
```

`backend/app/services/__init__.py`:

```python
"""Service-layer helpers for deterministic backend workflows."""
```

- [ ] **Step 6: Run the structure test and verify it passes**

Run:

```powershell
python -m pytest backend/tests/test_project_structure.py -v
```

Expected: `1 passed`.

- [ ] **Step 7: Commit the skeleton**

```powershell
git add backend/pyproject.toml backend/app/__init__.py backend/app/schemas/__init__.py backend/app/services/__init__.py backend/tests/test_project_structure.py
git commit -m "Add backend package skeleton"
```

---

### Task 2: Shared Schema Types

**Files:**
- Create: `backend/app/schemas/common.py`
- Modify: `backend/app/schemas/__init__.py`
- Create: `backend/tests/test_artifact_contracts.py`

- [ ] **Step 1: Write failing tests for shared schema types**

Create `backend/tests/test_artifact_contracts.py` with this content:

```python
import pytest
from pydantic import ValidationError

from app.schemas.common import (
    ConfidenceLevel,
    ConstraintType,
    EvidenceRef,
    QualityStatus,
)


def test_shared_enums_expose_expected_values() -> None:
    assert ConfidenceLevel.LOW == "low"
    assert ConfidenceLevel.MEDIUM == "medium"
    assert ConfidenceLevel.HIGH == "high"
    assert QualityStatus.REVIEWED == "reviewed"
    assert ConstraintType.HARD == "hard"


def test_evidence_ref_accepts_url_or_summary() -> None:
    with_url = EvidenceRef(
        title="Steam page",
        url="https://store.steampowered.com/app/example",
        notes="Primary store reference.",
    )
    with_summary = EvidenceRef(
        title="Design note",
        quote_or_summary="The game uses a compact tactical board.",
        notes="Manual curation note.",
    )

    assert with_url.url == "https://store.steampowered.com/app/example"
    assert with_summary.quote_or_summary == "The game uses a compact tactical board."


def test_evidence_ref_rejects_missing_reference_payload() -> None:
    with pytest.raises(ValidationError, match="EvidenceRef requires url or quote_or_summary"):
        EvidenceRef(title="Empty source", notes="No reference payload.")


def test_evidence_ref_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        EvidenceRef(
            title="Unexpected source",
            url="https://example.com",
            notes="Unknown fields should not be accepted.",
            confidence="high",
        )
```

- [ ] **Step 2: Run shared schema tests and verify they fail**

Run:

```powershell
python -m pytest backend/tests/test_artifact_contracts.py -v
```

Expected: `FAILED` with `ModuleNotFoundError: No module named 'app.schemas.common'`.

- [ ] **Step 3: Implement shared schema types**

Create `backend/app/schemas/common.py` with this content:

```python
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
```

- [ ] **Step 4: Export shared schema types**

Replace `backend/app/schemas/__init__.py` with this content:

```python
from app.schemas.common import (
    ConfidenceLevel,
    ConstraintType,
    EvidenceRef,
    QualityStatus,
    StrictBaseModel,
)

__all__ = [
    "ConfidenceLevel",
    "ConstraintType",
    "EvidenceRef",
    "QualityStatus",
    "StrictBaseModel",
]
```

- [ ] **Step 5: Run shared schema tests and verify they pass**

Run:

```powershell
python -m pytest backend/tests/test_artifact_contracts.py -v
```

Expected: `4 passed`.

- [ ] **Step 6: Commit shared schema types**

```powershell
git add backend/app/schemas/common.py backend/app/schemas/__init__.py backend/tests/test_artifact_contracts.py
git commit -m "Add shared backend schema types"
```

---

### Task 3: Core Artifact Schemas

**Files:**
- Create: `backend/app/schemas/artifacts.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/tests/test_artifact_contracts.py`

- [ ] **Step 1: Extend schema tests for core artifacts**

Replace `backend/tests/test_artifact_contracts.py` with this content:

```python
import pytest
from pydantic import ValidationError

from app.schemas.artifacts import (
    ConceptCard,
    DesignClaim,
    DeveloperConstraint,
    DeveloperProfile,
    GraphRelation,
    OpportunityFrame,
    PrototypeBrief,
    SeedGame,
)
from app.schemas.common import (
    ConfidenceLevel,
    ConstraintType,
    EvidenceRef,
    QualityStatus,
)


def evidence() -> EvidenceRef:
    return EvidenceRef(
        title="Design source",
        quote_or_summary="The design uses compact rules and readable state.",
        notes="Fixture evidence.",
    )


def test_shared_enums_expose_expected_values() -> None:
    assert ConfidenceLevel.LOW == "low"
    assert ConfidenceLevel.MEDIUM == "medium"
    assert ConfidenceLevel.HIGH == "high"
    assert QualityStatus.REVIEWED == "reviewed"
    assert ConstraintType.HARD == "hard"


def test_evidence_ref_accepts_url_or_summary() -> None:
    with_url = EvidenceRef(
        title="Steam page",
        url="https://store.steampowered.com/app/example",
        notes="Primary store reference.",
    )
    with_summary = EvidenceRef(
        title="Design note",
        quote_or_summary="The game uses a compact tactical board.",
        notes="Manual curation note.",
    )

    assert with_url.url == "https://store.steampowered.com/app/example"
    assert with_summary.quote_or_summary == "The game uses a compact tactical board."


def test_evidence_ref_rejects_missing_reference_payload() -> None:
    with pytest.raises(ValidationError, match="EvidenceRef requires url or quote_or_summary"):
        EvidenceRef(title="Empty source", notes="No reference payload.")


def test_evidence_ref_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        EvidenceRef(
            title="Unexpected source",
            url="https://example.com",
            notes="Unknown fields should not be accepted.",
            confidence="high",
        )


def test_seed_game_requires_source_refs() -> None:
    with pytest.raises(ValidationError):
        SeedGame(
            id="game_empty",
            title="Empty Game",
            source_refs=[],
            short_description="A fixture game.",
            selection_reason="Used to prove source validation.",
        )


def test_design_claim_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        DesignClaim(
            id="claim_without_evidence",
            subject="Balatro",
            relation="uses",
            object="familiar rules",
            explanation="Missing evidence should fail.",
            evidence=[],
            confidence=ConfidenceLevel.HIGH,
            quality_status=QualityStatus.REVIEWED,
        )


def test_core_artifacts_accept_minimal_valid_payloads() -> None:
    seed_game = SeedGame(
        id="game_balatro",
        title="Balatro",
        source_refs=[evidence()],
        short_description="Poker-inspired roguelike deckbuilder.",
        selection_reason="Strong example of familiar rules transformed into system depth.",
    )
    claim = DesignClaim(
        id="claim_balatro_familiar_rules",
        subject="Balatro",
        relation="uses",
        object="familiar poker rules",
        explanation="Familiar card semantics reduce onboarding cost.",
        evidence=[evidence()],
        confidence=ConfidenceLevel.HIGH,
        quality_status=QualityStatus.REVIEWED,
    )
    relation = GraphRelation(
        id="rel_claim_balatro_familiar_rules",
        source_node="Balatro",
        relation="uses",
        target_node="familiar poker rules",
        claim_id=claim.id,
        evidence=claim.evidence,
        confidence=claim.confidence,
        quality_status=claim.quality_status,
    )
    profile = DeveloperProfile(
        id="profile_solo_systems",
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
            DeveloperConstraint(
                id="constraint_no_online",
                type=ConstraintType.HARD,
                statement="Do not require online multiplayer.",
            )
        ],
    )
    frame = OpportunityFrame(
        id="frame_rule_tactics",
        developer_profile_id=profile.id,
        opportunity_area="Low-art, short-run tactical rule manipulation.",
        source_game_ids=[seed_game.id],
        related_mechanics=["rule modification"],
        related_player_experiences=["tactical prediction"],
        related_constraints=["low art budget"],
        related_innovation_patterns=["compress a tactical space into symbolic rules"],
        recommended_transformations=["combine rule editing with short tactical encounters"],
        forbidden_directions=["online multiplayer"],
        evidence_path=[relation.id],
        fit_reason="The area emphasizes systems over asset volume.",
        risk_reason="Players may not understand rule consequences quickly.",
    )
    concept = ConceptCard(
        id="concept_ruleforge_tactics",
        opportunity_frame_id=frame.id,
        title="Ruleforge Tactics",
        one_sentence_concept="A short-run tactics game where players win by editing battlefield rules.",
        core_fantasy="Outsmarting a small battlefield by rewriting its laws.",
        core_loop="Inspect encounter, draft rule cards, resolve consequences, adjust strategy.",
        main_player_decisions=["which rule to alter", "when to commit a rule change"],
        main_mechanics=["rule cards", "compact grid", "predictable enemy intents"],
        reference_sources=["Balatro", "Into the Breach", "Baba Is You"],
        difference_from_references="It turns rule editing into short tactical runs rather than puzzle levels.",
        fit_reason="It can start with symbolic presentation and minimal animation.",
        production_risks=["rules need clear feedback"],
        design_risks=["players may feel outcomes are arbitrary"],
        novelty_reason="Combines tactical forecasting with editable encounter laws.",
        suggested_prototype_scope="4x4 grid, three unit types, six rule cards, five encounters.",
    )
    brief = PrototypeBrief(
        id="brief_ruleforge_tactics",
        concept_card_id=concept.id,
        largest_risk_hypothesis="Players can understand and enjoy changing battlefield rules within minutes.",
        minimum_prototype_scope="4x4 grid, three unit types, six rule cards, five encounters.",
        target_playtest_duration="10 minutes",
        success_signals=["player explains rule consequences after one run"],
        failure_signals=["player says outcomes feel arbitrary"],
        do_not_build_yet=["campaign progression", "polished art"],
    )

    assert relation.claim_id == claim.id
    assert frame.developer_profile_id == profile.id
    assert concept.opportunity_frame_id == frame.id
    assert brief.concept_card_id == concept.id


def test_prototype_brief_requires_success_and_failure_signals() -> None:
    with pytest.raises(ValidationError):
        PrototypeBrief(
            id="brief_invalid",
            concept_card_id="concept_ruleforge_tactics",
            largest_risk_hypothesis="Players can understand the rules.",
            minimum_prototype_scope="Small grid prototype.",
            target_playtest_duration="10 minutes",
            success_signals=[],
            failure_signals=[],
            do_not_build_yet=["campaign progression"],
        )
```

- [ ] **Step 2: Run artifact tests and verify they fail**

Run:

```powershell
python -m pytest backend/tests/test_artifact_contracts.py -v
```

Expected: `FAILED` with `ModuleNotFoundError: No module named 'app.schemas.artifacts'`.

- [ ] **Step 3: Implement core artifact schemas**

Create `backend/app/schemas/artifacts.py` with this content:

```python
from __future__ import annotations

from pydantic import Field

from app.schemas.common import (
    ConfidenceLevel,
    ConstraintType,
    EvidenceRef,
    QualityStatus,
    StrictBaseModel,
)


class DeveloperConstraint(StrictBaseModel):
    id: str = Field(min_length=1)
    type: ConstraintType
    statement: str = Field(min_length=1)


class SeedGame(StrictBaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_refs: list[EvidenceRef] = Field(min_length=1)
    short_description: str = Field(min_length=1)
    selection_reason: str = Field(min_length=1)


class DesignClaim(StrictBaseModel):
    id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    object: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)
    confidence: ConfidenceLevel
    quality_status: QualityStatus


class GraphRelation(StrictBaseModel):
    id: str = Field(min_length=1)
    source_node: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    target_node: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)
    confidence: ConfidenceLevel
    quality_status: QualityStatus


class DeveloperProfile(StrictBaseModel):
    id: str = Field(min_length=1)
    team_size: str = Field(min_length=1)
    time_budget: str = Field(min_length=1)
    programming_ability: str = Field(min_length=1)
    art_ability: str = Field(min_length=1)
    audio_ability: str = Field(min_length=1)
    content_production_ability: str = Field(min_length=1)
    liked_references: list[str] = Field(min_length=1)
    disliked_references_or_mechanics: list[str]
    desired_player_experiences: list[str] = Field(min_length=1)
    constraints: list[DeveloperConstraint] = Field(min_length=1)


class OpportunityFrame(StrictBaseModel):
    id: str = Field(min_length=1)
    developer_profile_id: str = Field(min_length=1)
    opportunity_area: str = Field(min_length=1)
    source_game_ids: list[str] = Field(min_length=1)
    related_mechanics: list[str] = Field(min_length=1)
    related_player_experiences: list[str] = Field(min_length=1)
    related_constraints: list[str] = Field(min_length=1)
    related_innovation_patterns: list[str] = Field(min_length=1)
    recommended_transformations: list[str] = Field(min_length=1)
    forbidden_directions: list[str] = Field(min_length=1)
    evidence_path: list[str] = Field(min_length=1)
    fit_reason: str = Field(min_length=1)
    risk_reason: str = Field(min_length=1)


class ConceptCard(StrictBaseModel):
    id: str = Field(min_length=1)
    opportunity_frame_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    one_sentence_concept: str = Field(min_length=1)
    core_fantasy: str = Field(min_length=1)
    core_loop: str = Field(min_length=1)
    main_player_decisions: list[str] = Field(min_length=1)
    main_mechanics: list[str] = Field(min_length=1)
    reference_sources: list[str] = Field(min_length=1)
    difference_from_references: str = Field(min_length=1)
    fit_reason: str = Field(min_length=1)
    production_risks: list[str] = Field(min_length=1)
    design_risks: list[str] = Field(min_length=1)
    novelty_reason: str = Field(min_length=1)
    suggested_prototype_scope: str = Field(min_length=1)


class PrototypeBrief(StrictBaseModel):
    id: str = Field(min_length=1)
    concept_card_id: str = Field(min_length=1)
    largest_risk_hypothesis: str = Field(min_length=1)
    minimum_prototype_scope: str = Field(min_length=1)
    target_playtest_duration: str = Field(min_length=1)
    success_signals: list[str] = Field(min_length=1)
    failure_signals: list[str] = Field(min_length=1)
    do_not_build_yet: list[str] = Field(min_length=1)
```

- [ ] **Step 4: Export artifact schemas**

Replace `backend/app/schemas/__init__.py` with this content:

```python
from app.schemas.artifacts import (
    ConceptCard,
    DesignClaim,
    DeveloperConstraint,
    DeveloperProfile,
    GraphRelation,
    OpportunityFrame,
    PrototypeBrief,
    SeedGame,
)
from app.schemas.common import (
    ConfidenceLevel,
    ConstraintType,
    EvidenceRef,
    QualityStatus,
    StrictBaseModel,
)

__all__ = [
    "ConceptCard",
    "ConfidenceLevel",
    "ConstraintType",
    "DesignClaim",
    "DeveloperConstraint",
    "DeveloperProfile",
    "EvidenceRef",
    "GraphRelation",
    "OpportunityFrame",
    "PrototypeBrief",
    "QualityStatus",
    "SeedGame",
    "StrictBaseModel",
]
```

- [ ] **Step 5: Run artifact tests and verify they pass**

Run:

```powershell
python -m pytest backend/tests/test_artifact_contracts.py -v
```

Expected: `8 passed`.

- [ ] **Step 6: Commit artifact schemas**

```powershell
git add backend/app/schemas/artifacts.py backend/app/schemas/__init__.py backend/tests/test_artifact_contracts.py
git commit -m "Add core backend artifact schemas"
```

---

### Task 4: Golden Fixture Data

**Files:**
- Create: `backend/app/fixtures/golden_flow.json`
- Modify: `backend/tests/test_artifact_contracts.py`

- [ ] **Step 1: Add a failing test that validates the golden fixture models**

Append this test to `backend/tests/test_artifact_contracts.py`:

```python

def test_golden_fixture_core_payloads_match_artifact_schemas() -> None:
    import json
    from pathlib import Path

    fixture_path = (
        Path(__file__).resolve().parents[1] / "app" / "fixtures" / "golden_flow.json"
    )
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))

    seed_games = [SeedGame.model_validate(item) for item in raw["seed_games"]]
    design_claims = [DesignClaim.model_validate(item) for item in raw["design_claims"]]
    developer_profile = DeveloperProfile.model_validate(raw["developer_profile"])
    opportunity_frame = OpportunityFrame.model_validate(raw["opportunity_frame"])
    concept_cards = [ConceptCard.model_validate(item) for item in raw["concept_cards"]]
    prototype_brief = PrototypeBrief.model_validate(raw["prototype_brief"])

    assert {game.id for game in seed_games} == {
        "game_balatro",
        "game_into_the_breach",
        "game_baba_is_you",
    }
    assert {claim.confidence for claim in design_claims} >= {
        ConfidenceLevel.HIGH,
        ConfidenceLevel.LOW,
    }
    assert developer_profile.id == "profile_solo_systems"
    assert opportunity_frame.id == "frame_rule_tactics"
    assert concept_cards[0].opportunity_frame_id == opportunity_frame.id
    assert prototype_brief.concept_card_id == concept_cards[0].id
```

- [ ] **Step 2: Run fixture schema test and verify it fails**

Run:

```powershell
python -m pytest backend/tests/test_artifact_contracts.py::test_golden_fixture_core_payloads_match_artifact_schemas -v
```

Expected: `FAILED` with `FileNotFoundError` for `golden_flow.json`.

- [ ] **Step 3: Create the golden fixture**

Create `backend/app/fixtures/golden_flow.json` with this content:

```json
{
  "seed_games": [
    {
      "id": "game_balatro",
      "title": "Balatro",
      "source_refs": [
        {
          "title": "Balatro store page",
          "url": "https://store.steampowered.com/app/2379780/Balatro/",
          "notes": "Primary reference for the game candidate."
        }
      ],
      "short_description": "Poker-inspired roguelike deckbuilder built around familiar card semantics.",
      "selection_reason": "Strong sample for transforming familiar rules into systemic depth."
    },
    {
      "id": "game_into_the_breach",
      "title": "Into the Breach",
      "source_refs": [
        {
          "title": "Into the Breach store page",
          "url": "https://store.steampowered.com/app/590380/Into_the_Breach/",
          "notes": "Primary reference for the game candidate."
        }
      ],
      "short_description": "Compact tactical game using small boards, complete information, and readable enemy intent.",
      "selection_reason": "Strong sample for high tactical depth with constrained presentation scope."
    },
    {
      "id": "game_baba_is_you",
      "title": "Baba Is You",
      "source_refs": [
        {
          "title": "Baba Is You store page",
          "url": "https://store.steampowered.com/app/736260/Baba_Is_You/",
          "notes": "Primary reference for the game candidate."
        }
      ],
      "short_description": "Puzzle game where players manipulate explicit rules as objects.",
      "selection_reason": "Strong sample for rule manipulation as a central design pattern."
    }
  ],
  "design_claims": [
    {
      "id": "claim_balatro_familiar_rules",
      "subject": "Balatro",
      "relation": "uses",
      "object": "familiar card rules to reduce learning cost",
      "explanation": "Poker-like hands and card values give players an immediate rules vocabulary before modifiers add depth.",
      "evidence": [
        {
          "title": "Balatro design summary",
          "quote_or_summary": "The game starts from recognizable poker hand logic and layers score modifiers over it.",
          "notes": "Curated design interpretation for the fixture."
        }
      ],
      "confidence": "high",
      "quality_status": "reviewed"
    },
    {
      "id": "claim_breach_compact_tactics",
      "subject": "Into the Breach",
      "relation": "creates",
      "object": "high tactical depth through compact boards and visible enemy intent",
      "explanation": "Small board size and readable future actions let players reason about consequences without large production scope.",
      "evidence": [
        {
          "title": "Into the Breach design summary",
          "quote_or_summary": "Encounters emphasize small grids, visible threats, and consequence planning.",
          "notes": "Curated design interpretation for the fixture."
        }
      ],
      "confidence": "high",
      "quality_status": "reviewed"
    },
    {
      "id": "claim_baba_rule_manipulation",
      "subject": "Baba Is You",
      "relation": "demonstrates",
      "object": "rule manipulation as player-facing interaction",
      "explanation": "Rules become explicit objects that players can inspect and alter.",
      "evidence": [
        {
          "title": "Baba Is You design summary",
          "quote_or_summary": "Puzzle rules are represented as manipulable language-like objects.",
          "notes": "Curated design interpretation for the fixture."
        }
      ],
      "confidence": "high",
      "quality_status": "reviewed"
    },
    {
      "id": "claim_symbolic_ui_low_art_cost",
      "subject": "symbolic tactical UI",
      "relation": "may_reduce",
      "object": "animation and asset production burden",
      "explanation": "Abstract symbolic feedback can reduce art load, but this depends on clarity and feedback design.",
      "evidence": [
        {
          "title": "Curator hypothesis",
          "quote_or_summary": "Symbolic UI is expected to be cheaper than animation-heavy combat for a solo prototype.",
          "notes": "Weak evidence included to prove downstream confidence handling."
        }
      ],
      "confidence": "low",
      "quality_status": "weak_evidence"
    }
  ],
  "developer_profile": {
    "id": "profile_solo_systems",
    "team_size": "solo",
    "time_budget": "three month prototype",
    "programming_ability": "strong",
    "art_ability": "weak",
    "audio_ability": "basic",
    "content_production_ability": "limited",
    "liked_references": ["Balatro", "Into the Breach"],
    "disliked_references_or_mechanics": ["online multiplayer", "long scripted narrative"],
    "desired_player_experiences": ["short runs", "systemic decisions", "tactical prediction"],
    "constraints": [
      {
        "id": "constraint_no_online",
        "type": "hard",
        "statement": "Do not require online multiplayer."
      },
      {
        "id": "constraint_low_art",
        "type": "strong_preference",
        "statement": "Prefer concepts that can start with symbolic or low-volume art."
      }
    ]
  },
  "opportunity_frame": {
    "id": "frame_rule_tactics",
    "developer_profile_id": "profile_solo_systems",
    "opportunity_area": "Low-art, short-run tactical rule manipulation.",
    "source_game_ids": ["game_balatro", "game_into_the_breach", "game_baba_is_you"],
    "related_mechanics": ["rule modification", "compact tactical boards", "familiar rule vocabulary"],
    "related_player_experiences": ["tactical prediction", "chain satisfaction", "emergent problem solving"],
    "related_constraints": ["weak art ability", "three month prototype", "solo development"],
    "related_innovation_patterns": ["combine rule editing with short tactical runs"],
    "recommended_transformations": [
      "compress tactical space into a small board",
      "replace animation-heavy feedback with symbolic state changes",
      "combine editable rules with short encounter runs"
    ],
    "forbidden_directions": [
      "online multiplayer",
      "large open world",
      "long scripted narrative",
      "animation-heavy combat"
    ],
    "evidence_path": [
      "claim_balatro_familiar_rules",
      "claim_breach_compact_tactics",
      "claim_baba_rule_manipulation",
      "claim_symbolic_ui_low_art_cost"
    ],
    "fit_reason": "The area emphasizes systemic depth and readable rules over asset volume, matching a strong-programming solo developer with weak art capacity.",
    "risk_reason": "The largest risk is whether players can understand rule consequences quickly enough for short tactical runs."
  },
  "concept_cards": [
    {
      "id": "concept_ruleforge_tactics",
      "opportunity_frame_id": "frame_rule_tactics",
      "title": "Ruleforge Tactics",
      "one_sentence_concept": "A short-run tactics game where players win by editing small battlefield rules instead of directly commanding every unit.",
      "core_fantasy": "Outsmarting a compact battlefield by rewriting its laws.",
      "core_loop": "Inspect enemy intents, draft rule cards, apply one rule change, resolve the turn, and adapt the next encounter.",
      "main_player_decisions": [
        "which battlefield rule to alter",
        "when to accept a risky rule interaction",
        "which encounter reward supports the current rule plan"
      ],
      "main_mechanics": [
        "4x4 tactical board",
        "rule cards",
        "visible enemy intent",
        "short encounter chain"
      ],
      "reference_sources": ["Balatro", "Into the Breach", "Baba Is You"],
      "difference_from_references": "It uses tactical forecasting and rule manipulation, but turns them into short encounter runs rather than poker scoring, pure tactics, or puzzle levels.",
      "fit_reason": "The concept can begin with symbols, simple boards, and rules-first feedback before any polished asset work.",
      "production_risks": [
        "rule interactions need readable feedback",
        "symbolic presentation may still require careful UI polish"
      ],
      "design_risks": [
        "players may not predict rule consequences",
        "runs may feel arbitrary if rule feedback is unclear"
      ],
      "novelty_reason": "It combines rule editing with tactical run structure under low-art production constraints.",
      "suggested_prototype_scope": "A 4x4 board, three unit types, six rule cards, and five encounters."
    }
  ],
  "prototype_brief": {
    "id": "brief_ruleforge_tactics",
    "concept_card_id": "concept_ruleforge_tactics",
    "largest_risk_hypothesis": "Players can understand and enjoy changing battlefield rules within the first few minutes.",
    "minimum_prototype_scope": "A 4x4 board, three unit types, six rule cards, and five encounters.",
    "target_playtest_duration": "10 minutes",
    "success_signals": [
      "player can explain a rule consequence after one encounter",
      "player voluntarily restarts to try a different rule combination"
    ],
    "failure_signals": [
      "player says outcomes feel arbitrary",
      "player cannot predict what a rule change will affect"
    ],
    "do_not_build_yet": [
      "campaign progression",
      "polished art",
      "large content set",
      "online features"
    ]
  }
}
```

- [ ] **Step 4: Run fixture schema test and verify it passes**

Run:

```powershell
python -m pytest backend/tests/test_artifact_contracts.py::test_golden_fixture_core_payloads_match_artifact_schemas -v
```

Expected: `1 passed`.

- [ ] **Step 5: Run all schema tests**

Run:

```powershell
python -m pytest backend/tests/test_artifact_contracts.py -v
```

Expected: `9 passed`.

- [ ] **Step 6: Commit golden fixture**

```powershell
git add backend/app/fixtures/golden_flow.json backend/tests/test_artifact_contracts.py
git commit -m "Add golden backend fixture data"
```

---

### Task 5: Fixture Pipeline Success Path

**Files:**
- Create: `backend/app/services/fixture_pipeline.py`
- Create: `backend/tests/test_fixture_pipeline.py`

- [ ] **Step 1: Write failing tests for the successful fixture pipeline**

Create `backend/tests/test_fixture_pipeline.py` with this content:

```python
from pathlib import Path

from app.schemas.common import ConfidenceLevel, QualityStatus
from app.services.fixture_pipeline import (
    build_graph_relations_from_claims,
    run_fixture_pipeline,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "fixtures" / "golden_flow.json"
)


def test_build_graph_relations_preserves_claim_evidence_and_quality() -> None:
    result = run_fixture_pipeline(FIXTURE_PATH)
    relations = build_graph_relations_from_claims(result.design_claims)

    relation_by_claim = {relation.claim_id: relation for relation in relations}
    weak_relation = relation_by_claim["claim_symbolic_ui_low_art_cost"]

    assert weak_relation.confidence == ConfidenceLevel.LOW
    assert weak_relation.quality_status == QualityStatus.WEAK_EVIDENCE
    assert weak_relation.evidence[0].notes == "Weak evidence included to prove downstream confidence handling."


def test_golden_flow_runs_end_to_end() -> None:
    result = run_fixture_pipeline(FIXTURE_PATH)

    assert len(result.seed_games) == 3
    assert len(result.design_claims) == 4
    assert len(result.graph_relations) == 4
    assert result.developer_profile.id == "profile_solo_systems"
    assert result.opportunity_frame.id == "frame_rule_tactics"
    assert [concept.id for concept in result.concept_cards] == ["concept_ruleforge_tactics"]
    assert result.prototype_brief.id == "brief_ruleforge_tactics"
```

- [ ] **Step 2: Run pipeline tests and verify they fail**

Run:

```powershell
python -m pytest backend/tests/test_fixture_pipeline.py -v
```

Expected: `FAILED` with `ModuleNotFoundError: No module named 'app.services.fixture_pipeline'`.

- [ ] **Step 3: Implement the fixture pipeline success path**

Create `backend/app/services/fixture_pipeline.py` with this content:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from app.schemas.artifacts import (
    ConceptCard,
    DesignClaim,
    DeveloperProfile,
    GraphRelation,
    OpportunityFrame,
    PrototypeBrief,
    SeedGame,
)
from app.schemas.common import StrictBaseModel


class FixturePipelineResult(StrictBaseModel):
    seed_games: list[SeedGame]
    design_claims: list[DesignClaim]
    graph_relations: list[GraphRelation]
    developer_profile: DeveloperProfile
    opportunity_frame: OpportunityFrame
    concept_cards: list[ConceptCard]
    prototype_brief: PrototypeBrief


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_graph_relations_from_claims(claims: list[DesignClaim]) -> list[GraphRelation]:
    return [
        GraphRelation(
            id=f"rel_{claim.id}",
            source_node=claim.subject,
            relation=claim.relation,
            target_node=claim.object,
            claim_id=claim.id,
            evidence=claim.evidence,
            confidence=claim.confidence,
            quality_status=claim.quality_status,
        )
        for claim in claims
    ]


def run_fixture_pipeline(path: Path) -> FixturePipelineResult:
    return run_fixture_pipeline_from_dict(load_fixture(path))


def run_fixture_pipeline_from_dict(raw: dict[str, Any]) -> FixturePipelineResult:
    seed_games = TypeAdapter(list[SeedGame]).validate_python(raw["seed_games"])
    design_claims = TypeAdapter(list[DesignClaim]).validate_python(raw["design_claims"])
    graph_relations = build_graph_relations_from_claims(design_claims)
    developer_profile = DeveloperProfile.model_validate(raw["developer_profile"])
    opportunity_frame = OpportunityFrame.model_validate(raw["opportunity_frame"])
    concept_cards = TypeAdapter(list[ConceptCard]).validate_python(raw["concept_cards"])
    prototype_brief = PrototypeBrief.model_validate(raw["prototype_brief"])

    return FixturePipelineResult(
        seed_games=seed_games,
        design_claims=design_claims,
        graph_relations=graph_relations,
        developer_profile=developer_profile,
        opportunity_frame=opportunity_frame,
        concept_cards=concept_cards,
        prototype_brief=prototype_brief,
    )
```

- [ ] **Step 4: Run pipeline tests and verify they pass**

Run:

```powershell
python -m pytest backend/tests/test_fixture_pipeline.py -v
```

Expected: `2 passed`.

- [ ] **Step 5: Run full backend tests**

Run:

```powershell
python -m pytest backend/tests -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit pipeline success path**

```powershell
git add backend/app/services/fixture_pipeline.py backend/tests/test_fixture_pipeline.py
git commit -m "Add deterministic fixture pipeline"
```

---

### Task 6: Cross-Artifact Contract Validation

**Files:**
- Modify: `backend/app/services/fixture_pipeline.py`
- Modify: `backend/tests/test_fixture_pipeline.py`

- [ ] **Step 1: Add failing tests for cross-artifact rule violations**

Replace `backend/tests/test_fixture_pipeline.py` with this content:

```python
from copy import deepcopy
from pathlib import Path

import pytest

from app.schemas.common import ConfidenceLevel, QualityStatus
from app.services.fixture_pipeline import (
    ContractViolation,
    build_graph_relations_from_claims,
    load_fixture,
    run_fixture_pipeline,
    run_fixture_pipeline_from_dict,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "fixtures" / "golden_flow.json"
)


def golden_raw() -> dict:
    return deepcopy(load_fixture(FIXTURE_PATH))


def test_build_graph_relations_preserves_claim_evidence_and_quality() -> None:
    result = run_fixture_pipeline(FIXTURE_PATH)
    relations = build_graph_relations_from_claims(result.design_claims)

    relation_by_claim = {relation.claim_id: relation for relation in relations}
    weak_relation = relation_by_claim["claim_symbolic_ui_low_art_cost"]

    assert weak_relation.confidence == ConfidenceLevel.LOW
    assert weak_relation.quality_status == QualityStatus.WEAK_EVIDENCE
    assert weak_relation.evidence[0].notes == "Weak evidence included to prove downstream confidence handling."


def test_golden_flow_runs_end_to_end() -> None:
    result = run_fixture_pipeline(FIXTURE_PATH)

    assert len(result.seed_games) == 3
    assert len(result.design_claims) == 4
    assert len(result.graph_relations) == 4
    assert result.developer_profile.id == "profile_solo_systems"
    assert result.opportunity_frame.id == "frame_rule_tactics"
    assert [concept.id for concept in result.concept_cards] == ["concept_ruleforge_tactics"]
    assert result.prototype_brief.id == "brief_ruleforge_tactics"


def test_opportunity_frame_must_reference_existing_evidence() -> None:
    raw = golden_raw()
    raw["opportunity_frame"]["evidence_path"] = ["claim_missing"]

    with pytest.raises(ContractViolation, match="OpportunityFrame must include a valid evidence path"):
        run_fixture_pipeline_from_dict(raw)


def test_concept_card_must_reference_existing_opportunity_frame() -> None:
    raw = golden_raw()
    raw["concept_cards"][0]["opportunity_frame_id"] = "frame_missing"

    with pytest.raises(ContractViolation, match="ConceptCard must reference an existing opportunity frame"):
        run_fixture_pipeline_from_dict(raw)


def test_concept_card_must_not_include_forbidden_directions() -> None:
    raw = golden_raw()
    raw["concept_cards"][0]["one_sentence_concept"] = (
        "A short-run tactics game with online multiplayer rule battles."
    )

    with pytest.raises(ContractViolation, match="ConceptCard must not include forbidden directions"):
        run_fixture_pipeline_from_dict(raw)


def test_prototype_brief_must_reference_existing_concept_card() -> None:
    raw = golden_raw()
    raw["prototype_brief"]["concept_card_id"] = "concept_missing"

    with pytest.raises(ContractViolation, match="PrototypeBrief must reference an existing concept card"):
        run_fixture_pipeline_from_dict(raw)


def test_prototype_brief_must_define_observable_signals() -> None:
    raw = golden_raw()
    raw["prototype_brief"]["success_signals"] = ["   "]
    raw["prototype_brief"]["failure_signals"] = ["   "]

    with pytest.raises(
        ContractViolation,
        match="PrototypeBrief must define observable success and failure signals",
    ):
        run_fixture_pipeline_from_dict(raw)
```

- [ ] **Step 2: Run contract tests and verify they fail**

Run:

```powershell
python -m pytest backend/tests/test_fixture_pipeline.py -v
```

Expected: `FAILED` because `ContractViolation` and cross-artifact validations are not implemented.

- [ ] **Step 3: Implement cross-artifact contract validation**

Replace `backend/app/services/fixture_pipeline.py` with this content:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from app.schemas.artifacts import (
    ConceptCard,
    DesignClaim,
    DeveloperProfile,
    GraphRelation,
    OpportunityFrame,
    PrototypeBrief,
    SeedGame,
)
from app.schemas.common import StrictBaseModel


class ContractViolation(ValueError):
    pass


class FixturePipelineResult(StrictBaseModel):
    seed_games: list[SeedGame]
    design_claims: list[DesignClaim]
    graph_relations: list[GraphRelation]
    developer_profile: DeveloperProfile
    opportunity_frame: OpportunityFrame
    concept_cards: list[ConceptCard]
    prototype_brief: PrototypeBrief


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_graph_relations_from_claims(claims: list[DesignClaim]) -> list[GraphRelation]:
    return [
        GraphRelation(
            id=f"rel_{claim.id}",
            source_node=claim.subject,
            relation=claim.relation,
            target_node=claim.object,
            claim_id=claim.id,
            evidence=claim.evidence,
            confidence=claim.confidence,
            quality_status=claim.quality_status,
        )
        for claim in claims
    ]


def run_fixture_pipeline(path: Path) -> FixturePipelineResult:
    return run_fixture_pipeline_from_dict(load_fixture(path))


def run_fixture_pipeline_from_dict(raw: dict[str, Any]) -> FixturePipelineResult:
    seed_games = TypeAdapter(list[SeedGame]).validate_python(raw["seed_games"])
    design_claims = TypeAdapter(list[DesignClaim]).validate_python(raw["design_claims"])
    graph_relations = build_graph_relations_from_claims(design_claims)
    developer_profile = DeveloperProfile.model_validate(raw["developer_profile"])
    opportunity_frame = OpportunityFrame.model_validate(raw["opportunity_frame"])
    concept_cards = TypeAdapter(list[ConceptCard]).validate_python(raw["concept_cards"])
    prototype_brief = PrototypeBrief.model_validate(raw["prototype_brief"])

    validate_graph_relations(graph_relations, design_claims)
    validate_opportunity_frame(opportunity_frame, developer_profile, seed_games, design_claims, graph_relations)
    validate_concept_cards(concept_cards, opportunity_frame)
    validate_prototype_brief(prototype_brief, concept_cards)

    return FixturePipelineResult(
        seed_games=seed_games,
        design_claims=design_claims,
        graph_relations=graph_relations,
        developer_profile=developer_profile,
        opportunity_frame=opportunity_frame,
        concept_cards=concept_cards,
        prototype_brief=prototype_brief,
    )


def validate_graph_relations(
    graph_relations: list[GraphRelation],
    design_claims: list[DesignClaim],
) -> None:
    claim_ids = {claim.id for claim in design_claims}
    for relation in graph_relations:
        if relation.claim_id not in claim_ids:
            raise ContractViolation("GraphRelation must reference an existing design claim")


def validate_opportunity_frame(
    opportunity_frame: OpportunityFrame,
    developer_profile: DeveloperProfile,
    seed_games: list[SeedGame],
    design_claims: list[DesignClaim],
    graph_relations: list[GraphRelation],
) -> None:
    if opportunity_frame.developer_profile_id != developer_profile.id:
        raise ContractViolation("OpportunityFrame must reference an existing developer profile")

    seed_game_ids = {game.id for game in seed_games}
    if any(game_id not in seed_game_ids for game_id in opportunity_frame.source_game_ids):
        raise ContractViolation("OpportunityFrame must reference existing source games")

    evidence_ids = {claim.id for claim in design_claims} | {relation.id for relation in graph_relations}
    if any(evidence_id not in evidence_ids for evidence_id in opportunity_frame.evidence_path):
        raise ContractViolation("OpportunityFrame must include a valid evidence path")


def validate_concept_cards(
    concept_cards: list[ConceptCard],
    opportunity_frame: OpportunityFrame,
) -> None:
    for concept in concept_cards:
        if concept.opportunity_frame_id != opportunity_frame.id:
            raise ContractViolation("ConceptCard must reference an existing opportunity frame")

        concept_text = searchable_concept_text(concept)
        forbidden_matches = [
            direction
            for direction in opportunity_frame.forbidden_directions
            if direction.lower() in concept_text
        ]
        if forbidden_matches:
            raise ContractViolation("ConceptCard must not include forbidden directions")

        success_claims = [
            "guaranteed fun",
            "commercial success",
            "will be successful",
            "一定好玩",
            "一定成功",
        ]
        if any(claim in concept_text for claim in success_claims):
            raise ContractViolation("ConceptCard must not promise fun or commercial success")


def validate_prototype_brief(
    prototype_brief: PrototypeBrief,
    concept_cards: list[ConceptCard],
) -> None:
    concept_ids = {concept.id for concept in concept_cards}
    if prototype_brief.concept_card_id not in concept_ids:
        raise ContractViolation("PrototypeBrief must reference an existing concept card")

    success_signals = [signal.strip() for signal in prototype_brief.success_signals]
    failure_signals = [signal.strip() for signal in prototype_brief.failure_signals]
    if not any(success_signals) or not any(failure_signals):
        raise ContractViolation("PrototypeBrief must define observable success and failure signals")

    vague_risk_phrases = ["whether it is fun", "是否好玩", "validate fun"]
    risk_text = prototype_brief.largest_risk_hypothesis.lower()
    if any(phrase in risk_text for phrase in vague_risk_phrases):
        raise ContractViolation("PrototypeBrief must define a specific largest risk hypothesis")


def searchable_concept_text(concept: ConceptCard) -> str:
    parts: list[str] = [
        concept.title,
        concept.one_sentence_concept,
        concept.core_fantasy,
        concept.core_loop,
        concept.difference_from_references,
        concept.fit_reason,
        concept.novelty_reason,
        concept.suggested_prototype_scope,
    ]
    parts.extend(concept.main_player_decisions)
    parts.extend(concept.main_mechanics)
    parts.extend(concept.reference_sources)
    parts.extend(concept.production_risks)
    parts.extend(concept.design_risks)
    return " ".join(parts).lower()
```

- [ ] **Step 4: Run contract tests and verify they pass**

Run:

```powershell
python -m pytest backend/tests/test_fixture_pipeline.py -v
```

Expected: `7 passed`.

- [ ] **Step 5: Run full backend tests**

Run:

```powershell
python -m pytest backend/tests -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit contract validation**

```powershell
git add backend/app/services/fixture_pipeline.py backend/tests/test_fixture_pipeline.py
git commit -m "Validate backend fixture contract rules"
```

---

### Task 7: Final Verification

**Files:**
- Verify: all files under `backend/`

- [ ] **Step 1: Run the full backend test suite quietly**

Run:

```powershell
python -m pytest backend/tests -q
```

Expected: all tests pass, with output similar to:

```text
................
```

- [ ] **Step 2: Inspect backend file list**

Run:

```powershell
rg --files backend
```

Expected output includes:

```text
backend/pyproject.toml
backend/app/__init__.py
backend/app/schemas/__init__.py
backend/app/schemas/common.py
backend/app/schemas/artifacts.py
backend/app/services/__init__.py
backend/app/services/fixture_pipeline.py
backend/app/fixtures/golden_flow.json
backend/tests/test_project_structure.py
backend/tests/test_artifact_contracts.py
backend/tests/test_fixture_pipeline.py
```

- [ ] **Step 3: Confirm worktree state**

Run:

```powershell
git status --short --branch
```

Expected: current branch shown with no unstaged or untracked files after the task commits.

---

## Self-Review Results

**Spec coverage:** The plan covers the backend directory, Pydantic v2 schemas, `golden_flow.json`, deterministic fixture pipeline, pytest validation, evidence and confidence propagation, opportunity-frame gating, forbidden-direction blocking, and prototype-brief signal checks.

**Scope check:** The plan does not add FastAPI, Neo4j, Docker Compose, real LLM calls, frontend code, user accounts, task history, or concept evaluation.

**Type consistency:** Model names and field names match across tests, fixture JSON, and pipeline code: `SeedGame`, `DesignClaim`, `GraphRelation`, `DeveloperProfile`, `OpportunityFrame`, `ConceptCard`, and `PrototypeBrief`.

