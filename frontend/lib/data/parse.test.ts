import { afterEach, describe, expect, it, vi } from "vitest";
import { parseDeveloperProfileInput } from "@/lib/data";
import type { ProfileParseResult } from "@/lib/types";

const backendResult: ProfileParseResult = {
  draft: {
    id: "profile_draft_current",
    team_size: "solo",
    time_budget: "three month prototype",
    programming_ability: "strong",
    art_ability: "weak",
    audio_ability: "basic",
    content_production_ability: "limited",
    liked_references: ["Hades"],
    disliked_references_or_mechanics: [],
    desired_player_experiences: ["short runs"],
    constraints: [],
    missing_fields: [],
    field_sources: [],
    raw_text: "我一个人做游戏",
    is_complete: true,
  },
  warnings: [],
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

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

describe("parseDeveloperProfileInput", () => {
  it("returns the backend result when the request succeeds", async () => {
    vi.stubGlobal(
      "fetch",
      sseFetch(`event: result\ndata: ${JSON.stringify(backendResult)}\n\n`),
    );

    const result = await parseDeveloperProfileInput({ raw_text: "我一个人做游戏" });
    expect(result.draft.team_size).toBe("solo");
    expect(result.warnings).toEqual([]);
  });

  it("falls back to the local parser when the request fails", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));

    const result = await parseDeveloperProfileInput({
      raw_text:
        "我是 solo 开发者，程序能力强，美术能力弱，三个月原型。" +
        "我喜欢 Balatro，想要短局，不要做在线多人，也不想做大量内容。",
    });

    expect(result.draft.team_size).toBe("solo");
    expect(result.warnings[0]).toBe("后端不可用，已使用本地规则解析。");
  });

  it("falls back to the local parser on a non-2xx response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response("error", { status: 500 }))),
    );

    const result = await parseDeveloperProfileInput({
      raw_text:
        "我是 solo 开发者，程序能力强，美术能力弱，三个月原型。" +
        "我喜欢 Balatro，想要短局，不要做在线多人，也不想做大量内容。",
    });

    expect(result.draft.team_size).toBe("solo");
    expect(result.warnings[0]).toBe("后端不可用，已使用本地规则解析。");
  });
});
