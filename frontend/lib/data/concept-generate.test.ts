import { afterEach, describe, it, expect, vi } from "vitest";
import { generateConcepts, ConceptGenerationError } from "@/lib/data";
import type { ConceptCard, OpportunityFrame } from "@/lib/types";

const FRAME: OpportunityFrame = {
  id: "frame|opp|a|sub|Perspective|第一人称",
  developer_profile_id: "p",
  opportunity_area: "第一人称生存割草",
  source_game_ids: ["a", "b"],
  related_mechanics: ["护符定制"],
  related_player_experiences: ["紧张"],
  related_constraints: ["低美术成本"],
  related_innovation_patterns: ["数值滚雪球"],
  recommended_transformations: ["主变形"],
  forbidden_directions: ["禁止"],
  evidence_path: ["rel"],
  fit_reason: "f",
  risk_reason: "r",
};

const CARD: ConceptCard = {
  id: "concept|frame|opp|a|sub|Perspective|第一人称|1",
  opportunity_frame_id: FRAME.id,
  title: "概念1",
  one_sentence_concept: "一句话",
  core_fantasy: "幻想",
  core_loop: "循环",
  main_player_decisions: ["决策"],
  main_mechanics: ["机制"],
  reference_sources: ["a"],
  difference_from_references: "差异",
  fit_reason: "适配",
  production_risks: ["制作风险"],
  design_risks: ["设计风险"],
  novelty_reason: "新颖",
  suggested_prototype_scope: "原型范围",
};

afterEach(() => vi.restoreAllMocks());

describe("generateConcepts", () => {
  it("POSTs { frame } to /api/concept/generate and returns the cards", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => [CARD] });
    vi.stubGlobal("fetch", fetchMock);

    const result = await generateConcepts(FRAME);

    expect(result).toHaveLength(1);
    expect(result[0].id).toBe(CARD.id);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/concept/generate");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ frame: FRAME });
  });

  it("throws ConceptGenerationError carrying the status on 503", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({}) }),
    );
    await expect(generateConcepts(FRAME)).rejects.toMatchObject({
      name: "ConceptGenerationError",
      status: 503,
    });
  });

  it("throws ConceptGenerationError carrying the status on 502", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 502, json: async () => ({}) }),
    );
    await expect(generateConcepts(FRAME)).rejects.toBeInstanceOf(ConceptGenerationError);
    await expect(generateConcepts(FRAME)).rejects.toMatchObject({
      name: "ConceptGenerationError",
      status: 502,
    });
  });
});
