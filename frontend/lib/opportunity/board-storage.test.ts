import { afterEach, describe, it, expect } from "vitest";
import { loadBoard, saveBoard, clearBoard } from "@/lib/opportunity/board-storage";
import type { OpportunityArea } from "@/lib/types";

const AREA: OpportunityArea = {
  id: "opp|a|sub|Perspective|第一人称",
  anchor_game_id: "a",
  anchor_summary: "s",
  transformation: { type: "substitute", dimension: "Perspective", from_value: "第三人称", to_value: "第一人称" },
  existing_combination_count: 0,
  evidence: { anchor_game_id: "a", target_value_game_ids: ["g0"], combination_game_ids: [] },
  risk_posture: "balanced",
  fit_reason: "f",
  risk_reason: "r",
};

afterEach(() => localStorage.clear());

describe("board-storage", () => {
  it("returns an empty board when nothing is stored", () => {
    expect(loadBoard("p1")).toEqual({ areas: [], seen_ids: [] });
  });

  it("saves and loads a board keyed by profile id", () => {
    saveBoard("p1", { areas: [AREA], seen_ids: ["opp|a|sub|Perspective|第一人称"] });
    expect(loadBoard("p1")).toEqual({ areas: [AREA], seen_ids: ["opp|a|sub|Perspective|第一人称"] });
    expect(loadBoard("p2")).toEqual({ areas: [], seen_ids: [] });
  });

  it("clears a profile's board", () => {
    saveBoard("p1", { areas: [AREA], seen_ids: ["x"] });
    clearBoard("p1");
    expect(loadBoard("p1")).toEqual({ areas: [], seen_ids: [] });
  });

  it("returns an empty board on corrupt json", () => {
    localStorage.setItem("gamegraph.opportunity-board.p1", "{not json");
    expect(loadBoard("p1")).toEqual({ areas: [], seen_ids: [] });
  });
});
