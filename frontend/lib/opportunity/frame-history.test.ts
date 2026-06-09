import { afterEach, describe, it, expect } from "vitest";
import {
  FRAMES_KEY,
  clearLastFrameId,
  loadFrames,
  peekLastFrameId,
  removeFrame,
  rememberLastFrameId,
  upsertFrame,
} from "@/lib/opportunity/frame-history";
import type { OpportunityFrame } from "@/lib/types";

function frame(id: string, area = "区域"): OpportunityFrame {
  return {
    id,
    developer_profile_id: "p",
    opportunity_area: area,
    source_game_ids: [],
    related_mechanics: [],
    related_player_experiences: [],
    related_constraints: [],
    related_innovation_patterns: [],
    recommended_transformations: ["主变形"],
    forbidden_directions: ["禁止"],
    evidence_path: [],
    fit_reason: "f",
    risk_reason: "r",
  };
}

afterEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe("frame-history", () => {
  it("starts empty", () => {
    expect(loadFrames()).toEqual([]);
  });

  it("upserts new frames newest-first", () => {
    upsertFrame(frame("frame|a"));
    upsertFrame(frame("frame|b"));
    expect(loadFrames().map((f) => f.id)).toEqual(["frame|b", "frame|a"]);
  });

  it("dedupes by id and moves the touched frame to the front", () => {
    upsertFrame(frame("frame|a", "旧"));
    upsertFrame(frame("frame|b"));
    upsertFrame(frame("frame|a", "新"));
    const frames = loadFrames();
    expect(frames.map((f) => f.id)).toEqual(["frame|a", "frame|b"]);
    expect(frames[0].opportunity_area).toBe("新");
  });

  it("removes a frame by id", () => {
    upsertFrame(frame("frame|a"));
    upsertFrame(frame("frame|b"));
    removeFrame("frame|a");
    expect(loadFrames().map((f) => f.id)).toEqual(["frame|b"]);
  });

  it("peekLastFrameId reads without clearing; clearLastFrameId removes it", () => {
    rememberLastFrameId("frame|a");
    expect(peekLastFrameId()).toBe("frame|a");
    expect(peekLastFrameId()).toBe("frame|a");
    clearLastFrameId();
    expect(peekLastFrameId()).toBeNull();
  });

  it("ignores corrupt storage", () => {
    localStorage.setItem(FRAMES_KEY, "{not json");
    expect(loadFrames()).toEqual([]);
  });
});
