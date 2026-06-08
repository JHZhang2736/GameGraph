import { z } from "zod";

const nonEmpty = z.string().trim().min(1);
const nonEmptyList = z.array(nonEmpty).min(1);

const evidenceRef = z
  .object({
    title: nonEmpty,
    url: nonEmpty.optional(),
    quote_or_summary: nonEmpty.optional(),
    notes: nonEmpty,
  })
  .strict()
  .refine((e) => Boolean(e.url) || Boolean(e.quote_or_summary), {
    message: "EvidenceRef requires url or quote_or_summary",
  });

const evidenceList = z.array(evidenceRef).min(1);
const confidence = z.enum(["low", "medium", "high"]);
const quality = z.enum(["draft", "reviewed", "weak_evidence", "conflicting"]);

const referenceValueTag = z
  .object({
    tag: nonEmpty,
    confidence,
    quality_status: quality,
    evidence: z.array(evidenceRef),
  })
  .strict();

const seedGame = z
  .object({
    id: nonEmpty,
    title: nonEmpty,
    source_refs: evidenceList,
    short_description: nonEmpty,
    selection_reason: nonEmpty,
  })
  .strict();

const profile = z
  .object({
    game_id: nonEmpty,
    one_sentence_summary: nonEmpty,
    core_hook: nonEmpty,
    core_loop: nonEmpty,
    progression_model: nonEmpty,
    failure_model: nonEmpty,
    content_structure: nonEmpty,
    main_player_actions: nonEmptyList,
    main_player_decisions: nonEmptyList,
    main_player_experiences: nonEmptyList,
    main_mechanics: nonEmptyList,
    replayability_sources: nonEmptyList,
    production_constraints: nonEmptyList,
    innovation_patterns: nonEmptyList,
    reusable_reference_patterns: nonEmptyList,
    non_replicable_risks: nonEmptyList,
    genre: nonEmptyList,
    art_style: nonEmptyList,
    audio_style: nonEmptyList,
    perspective: nonEmptyList,
    theme: nonEmptyList,
    narrative_style: nonEmptyList,
    game_feel: nonEmptyList,
    team_model: nonEmptyList,
    reference_value_tags: z.array(referenceValueTag).min(1),
    evidence: evidenceList,
    confidence,
    quality_status: quality,
  })
  .strict();

const claim = z
  .object({
    id: nonEmpty,
    subject: nonEmpty,
    relation: nonEmpty,
    object: nonEmpty,
    explanation: nonEmpty,
    evidence: evidenceList,
    confidence,
    quality_status: quality,
  })
  .strict();

export const importDocumentSchema = z
  .object({
    candidate: seedGame,
    profile,
    claims: z.array(claim),
  })
  .strict()
  .refine((doc) => doc.profile.game_id === doc.candidate.id, {
    message: "profile.game_id must match candidate.id",
    path: ["profile", "game_id"],
  });

export type ImportDocument = z.infer<typeof importDocumentSchema>;

export interface FieldError {
  path: string;
  message: string;
}

export type ParseResult =
  | { ok: true; document: ImportDocument }
  | { ok: false; errors: FieldError[] };

export function parseImportDocument(raw: unknown): ParseResult {
  const result = importDocumentSchema.safeParse(raw);
  if (result.success) {
    return { ok: true, document: result.data };
  }
  return {
    ok: false,
    errors: result.error.issues.map((issue) => ({
      path: issue.path.join("."),
      message: issue.message,
    })),
  };
}
