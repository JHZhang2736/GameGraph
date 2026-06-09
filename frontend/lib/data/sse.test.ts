import { describe, it, expect } from "vitest";
import { readSseResult, SseStreamError } from "@/lib/data/sse";

function sseResponse(text: string, status = 200): Response {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text));
      controller.close();
    },
  });
  return { ok: status >= 200 && status < 300, status, body } as unknown as Response;
}

describe("readSseResult", () => {
  it("ignores heartbeats and resolves the result event", async () => {
    const text =
      "event: heartbeat\ndata: {}\n\n" +
      "event: heartbeat\ndata: {}\n\n" +
      'event: result\ndata: {"value":"done"}\n\n';
    const out = await readSseResult<{ value: string }>(sseResponse(text));
    expect(out.value).toBe("done");
  });

  it("throws SseStreamError with detail and code on error event", async () => {
    const text = 'event: error\ndata: {"detail":"boom","code":502}\n\n';
    await expect(readSseResult(sseResponse(text))).rejects.toMatchObject({
      message: "boom",
      code: 502,
    });
    await expect(readSseResult(sseResponse(text))).rejects.toBeInstanceOf(SseStreamError);
  });

  it("throws when the stream ends without a result event", async () => {
    const text = "event: heartbeat\ndata: {}\n\n";
    await expect(readSseResult(sseResponse(text))).rejects.toThrow();
  });
});
