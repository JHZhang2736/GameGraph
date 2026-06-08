// Pure draft operations for the editable workbench. These mirror the backend:
// recompute = the parser's blocking-field completeness rule, applied live as the
// user edits; promote = backend promote_draft_to_profile.
import { BLOCKING_FIELDS, missingProfileField } from "@/lib/profile/parser";
import type { DeveloperProfile, DeveloperProfileDraft } from "@/lib/types";

// Recomputes missing_fields and is_complete from the current field values so a
// manual edit immediately reflects in the badge and confirm gate.
export function recomputeDraftCompleteness(
  draft: DeveloperProfileDraft,
): DeveloperProfileDraft {
  const values: Record<(typeof BLOCKING_FIELDS)[number], string | null> = {
    team_size: draft.team_size,
    time_budget: draft.time_budget,
    programming_ability: draft.programming_ability,
    art_ability: draft.art_ability,
    content_production_ability: draft.content_production_ability,
  };

  const missingFields = BLOCKING_FIELDS.flatMap((field) =>
    values[field] ? [] : [missingProfileField(field)],
  );

  return {
    ...draft,
    missing_fields: missingFields,
    is_complete: missingFields.length === 0,
  };
}

// A blank, editable draft so the workbench is usable from a fresh load: the user
// can fill the profile by selecting on the right without typing any free text.
export function createEmptyDraft(): DeveloperProfileDraft {
  return recomputeDraftCompleteness({
    id: "profile_draft_current",
    team_size: null,
    time_budget: null,
    programming_ability: null,
    art_ability: null,
    audio_ability: "basic",
    content_production_ability: null,
    liked_references: [],
    disliked_references_or_mechanics: [],
    desired_player_experiences: [],
    constraints: [],
    missing_fields: [],
    field_sources: [],
    raw_text: "",
    is_complete: false,
  });
}

// Seeds an editable draft from an already-confirmed DeveloperProfile so a
// restored profile (e.g. loaded from browser storage) can be re-edited in the
// workbench. The audit-only fields (sources, raw_text) start empty; this is the
// inverse of promoteDraftToProfile.
export function createDraftFromProfile(profile: DeveloperProfile): DeveloperProfileDraft {
  return recomputeDraftCompleteness({
    id: profile.id,
    team_size: profile.team_size,
    time_budget: profile.time_budget,
    programming_ability: profile.programming_ability,
    art_ability: profile.art_ability,
    audio_ability: profile.audio_ability,
    content_production_ability: profile.content_production_ability,
    liked_references: profile.liked_references,
    disliked_references_or_mechanics: profile.disliked_references_or_mechanics,
    desired_player_experiences: profile.desired_player_experiences,
    constraints: profile.constraints,
    missing_fields: [],
    field_sources: [],
    raw_text: "",
    is_complete: false,
  });
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
    // Audio is optional/non-blocking; default it so a complete draft never fails
    // promotion just because the user left audio unset.
    audio_ability: draft.audio_ability ?? "basic",
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
