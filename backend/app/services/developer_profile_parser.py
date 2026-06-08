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
