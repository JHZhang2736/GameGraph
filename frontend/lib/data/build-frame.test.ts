import { afterEach, describe, it, expect, vi } from "vitest";
import { buildOpportunityFrame } from "@/lib/data";
import type { DeveloperProfile, OpportunityArea, OpportunityFrame } from "@/lib/types";

const PROFILE: DeveloperProfile = {
  id: "p",
  team_size: "solo",
  time_budget: "三个月",
  programming_ability: "强",
  art_ability: "弱",
  audio_ability: "弱",
  content_production_ability: "有限",
  liked_references: [],
  disliked_references_or_mechanics: [],
  desired_player_experiences: [],
  constraints: [],
};

const AREA: OpportunityArea = {
  id: "opp|a|sub|Perspective|第一人称",
  anchor_game_id: "a",
  anchor_summary: "s",
  transformation: {
    type: "substitute",
    dimension: "Perspective",
    from_value: "第三人称",
    to_value: "第一人称",
  },
  existing_combination_count: 0,
  evidence: { anchor_game_id: "a", target_value_game_ids: ["b"], combination_game_ids: [] },
  risk_posture: "balanced",
  fit_reason: "f",
  risk_reason: "r",
};

const FRAME: OpportunityFrame = {
  id: "frame|opp|a|sub|Perspective|第一人称",
  developer_profile_id: "p",
  opportunity_area: "区域",
  source_game_ids: ["a"],
  related_mechanics: [],
  related_player_experiences: [],
  related_constraints: [],
  related_innovation_patterns: [],
  recommended_transformations: ["主变形"],
  forbidden_directions: ["禁止"],
  evidence_path: ["rel"],
  fit_reason: "f",
  risk_reason: "r",
  warnings: ["注意"],
};

function sseFetch(frames: string, status = 200) {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(frames));
      controller.close();
    },
  });
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    body,
  } as unknown as Response);
}

afterEach(() => vi.restoreAllMocks());

describe("buildOpportunityFrame", () => {
  it("POSTs profile+area to /api/opportunity/frame and returns the frame", async () => {
    const fetchMock = sseFetch(`event: result\ndata: ${JSON.stringify(FRAME)}\n\n`);
    vi.stubGlobal("fetch", fetchMock);

    const result = await buildOpportunityFrame(PROFILE, AREA);

    expect(result.id).toBe(FRAME.id);
    expect(result.warnings).toEqual(["注意"]);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/opportunity/frame");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ profile: PROFILE, area: AREA });
  });

  it("throws on a non-2xx response", async () => {
    vi.stubGlobal("fetch", sseFetch("", 500));
    await expect(buildOpportunityFrame(PROFILE, AREA)).rejects.toThrow(/500/);
  });
});
