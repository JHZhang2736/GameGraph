export interface SsePayload {
  detail: string;
  code?: number;
}

export class SseStreamError extends Error {
  readonly code?: number;
  constructor(detail: string, code?: number) {
    super(detail);
    this.name = "SseStreamError";
    this.code = code;
  }
}

function parseBlock(block: string): { event: string; data: string } | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

// 读取后端 SSE 流：忽略 heartbeat，收到 result resolve，收到 error 抛 SseStreamError。
export async function readSseResult<T>(response: Response): Promise<T> {
  const body = response.body;
  if (!body) throw new Error("SSE response has no body");
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (value) buffer += decoder.decode(value, { stream: true });
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const rawBlock = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const parsed = parseBlock(rawBlock);
        if (!parsed || parsed.event === "heartbeat") continue;
        if (parsed.event === "result") return JSON.parse(parsed.data) as T;
        if (parsed.event === "error") {
          const payload = JSON.parse(parsed.data) as SsePayload;
          throw new SseStreamError(payload.detail, payload.code);
        }
      }
      if (done) break;
    }
  } finally {
    reader.releaseLock();
  }
  throw new Error("SSE stream ended without a result event");
}
