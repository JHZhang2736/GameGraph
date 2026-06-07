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
