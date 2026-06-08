// Pure draft operations for the editable workbench. These mirror the backend:
// recompute = the parser's blocking-field completeness rule, applied live as the
// user edits; promote = backend promote_draft_to_profile.
import { BLOCKING_FIELDS, missingProfileField } from "@/lib/profile/parser";
import type { DeveloperProfile, DeveloperProfileDraft } from "@/lib/types";

function isEmpty(value: string | null | string[] | unknown[]): boolean {
  if (value === null || value === "") return true;
  return Array.isArray(value) && value.length === 0;
}

// Recomputes missing_fields and is_complete from the current field values so a
// manual edit immediately reflects in the badge, missing panel, and confirm gate.
export function recomputeDraftCompleteness(
  draft: DeveloperProfileDraft,
): DeveloperProfileDraft {
  const values: Record<(typeof BLOCKING_FIELDS)[number], string | null | unknown[]> = {
    team_size: draft.team_size,
    time_budget: draft.time_budget,
    programming_ability: draft.programming_ability,
    art_ability: draft.art_ability,
    content_production_ability: draft.content_production_ability,
    liked_references: draft.liked_references,
    desired_player_experiences: draft.desired_player_experiences,
    constraints: draft.constraints,
  };

  const missingFields = BLOCKING_FIELDS.flatMap((field) =>
    isEmpty(values[field]) ? [missingProfileField(field)] : [],
  );

  return {
    ...draft,
    missing_fields: missingFields,
    is_complete: missingFields.length === 0,
  };
}

function required(value: string | null, field: string): string {
  if (value === null || value === "") {
    throw new Error(`DeveloperProfileDraft missing required field: ${field}`);
  }
  return value;
}

// Promotes a complete, confirmed draft into the authoritative DeveloperProfile,
// dropping the draft-only audit fields. Throws if the draft is not complete.
export function promoteDraftToProfile(draft: DeveloperProfileDraft): DeveloperProfile {
  if (!draft.is_complete) {
    throw new Error("DeveloperProfileDraft is incomplete");
  }

  return {
    id: draft.id,
    team_size: required(draft.team_size, "team_size"),
    time_budget: required(draft.time_budget, "time_budget"),
    programming_ability: required(draft.programming_ability, "programming_ability"),
    art_ability: required(draft.art_ability, "art_ability"),
    audio_ability: required(draft.audio_ability, "audio_ability"),
    content_production_ability: required(
      draft.content_production_ability,
      "content_production_ability",
    ),
    liked_references: draft.liked_references,
    disliked_references_or_mechanics: draft.disliked_references_or_mechanics,
    desired_player_experiences: draft.desired_player_experiences,
    constraints: draft.constraints,
  };
}
