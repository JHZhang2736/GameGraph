import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ImportPreview } from "@/components/import/import-preview";
import type { ImportDocument } from "@/lib/import/schema";

const doc = {
  candidate: { id: "game_hk", title: "Hollow Knight", short_description: "mv", selection_reason: "ref" },
  profile: {
    game_id: "game_hk", one_sentence_summary: "s", core_hook: "h", core_loop: "l",
    progression_model: "p", failure_model: "f", content_structure: "c",
    main_player_actions: ["jump"], main_player_decisions: ["route"], main_player_experiences: ["tension"],
    main_mechanics: ["platforming"], replayability_sources: ["x"], production_constraints: ["y"],
    innovation_patterns: ["i"], reusable_reference_patterns: ["r"], non_replicable_risks: ["k"],
    genre: ["mv"], art_style: ["a"], audio_style: ["o"], perspective: ["2d"], theme: ["dark"],
    narrative_style: ["env"], game_feel: ["tight"], team_model: ["small"],
    reference_value_tags: ["atmosphere"],
  },
  claims: [
    { id: "c1", subject: "Hollow Knight", relation: "reinforces", object: "flow", explanation: "e" },
  ],
} as unknown as ImportDocument;

describe("ImportPreview", () => {
  it("renders title, mechanics, reference tags and a claim", () => {
    render(<ImportPreview document={doc} onBack={vi.fn()} onConfirm={vi.fn()} pending={false} />);
    expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
    expect(screen.getByText("platforming")).toBeInTheDocument();
    expect(screen.getByText("atmosphere")).toBeInTheDocument();
    expect(screen.getByText(/reinforces/)).toBeInTheDocument();
  });
});
