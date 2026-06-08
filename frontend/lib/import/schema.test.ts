import { describe, it, expect } from "vitest";
import { parseImportDocument } from "@/lib/import/schema";

const evidence = { title: "GDC", notes: "n", url: "http://x" };

function validDoc() {
  return {
    candidate: {
      id: "game_hk",
      title: "Hollow Knight",
      source_refs: [evidence],
      short_description: "metroidvania",
      selection_reason: "reference",
    },
    profile: {
      game_id: "game_hk",
      one_sentence_summary: "s",
      core_hook: "h",
      core_loop: "l",
      progression_model: "p",
      failure_model: "f",
      content_structure: "c",
      main_player_actions: ["jump"],
      main_player_decisions: ["route"],
      main_player_experiences: ["tension"],
      main_mechanics: ["platforming"],
      replayability_sources: ["secrets"],
      production_constraints: ["small team"],
      innovation_patterns: ["x"],
      reusable_reference_patterns: ["y"],
      non_replicable_risks: ["z"],
      genre: ["metroidvania"],
      art_style: ["hand-drawn"],
      audio_style: ["orchestral"],
      perspective: ["2d"],
      theme: ["dark"],
      narrative_style: ["environmental"],
      game_feel: ["tight"],
      team_model: ["small"],
      reference_value_tags: [
        { tag: "atmosphere", confidence: "high", quality_status: "reviewed", evidence: [evidence] },
      ],
      evidence: [evidence],
      confidence: "high",
      quality_status: "reviewed",
    },
    claims: [
      {
        id: "claim_1",
        subject: "Hollow Knight",
        relation: "reinforces",
        object: "exploration flow",
        explanation: "e",
        evidence: [evidence],
        confidence: "high",
        quality_status: "reviewed",
      },
    ],
  };
}

describe("parseImportDocument", () => {
  it("accepts a valid document", () => {
    const result = parseImportDocument(validDoc());
    expect(result.ok).toBe(true);
  });

  it("rejects empty main_mechanics with a field path", () => {
    const doc = validDoc();
    doc.profile.main_mechanics = [];
    const result = parseImportDocument(doc);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.some((e) => e.path.includes("main_mechanics"))).toBe(true);
    }
  });

  it("rejects evidence with neither url nor quote_or_summary", () => {
    const doc = validDoc();
    doc.profile.evidence = [{ title: "t", notes: "n" } as never];
    const result = parseImportDocument(doc);
    expect(result.ok).toBe(false);
  });

  it("rejects when profile.game_id does not match candidate.id", () => {
    const doc = validDoc();
    doc.profile.game_id = "game_other";
    const result = parseImportDocument(doc);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.some((e) => e.message.includes("game_id"))).toBe(true);
    }
  });
});
