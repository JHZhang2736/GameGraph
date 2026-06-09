// 浏览器侧的机会框架历史。仿 lib/profile/storage.ts 的 useSyncExternalStore 写法：
// 用 raw 字符串作 key 缓存解析快照，使 loadFrames() 在数据未变时返回稳定引用，
// 避免 useSyncExternalStore 无限重渲染。写操作额外通知本地订阅者，以便同标签页
// 内的 upsert/remove 也能即时触发 React 重渲染（storage 事件只跨标签页触发）。
import type { OpportunityFrame } from "@/lib/types";

export const FRAMES_KEY = "gamegraph.opportunity-frames";
export const LAST_FRAME_ID_KEY = "gamegraph.last-frame-id";

function parseFrames(raw: string | null): OpportunityFrame[] {
  if (!raw) return [];
  try {
    const value = JSON.parse(raw);
    return Array.isArray(value) ? (value as OpportunityFrame[]) : [];
  } catch {
    return [];
  }
}

let snapshotRaw: string | null = null;
let snapshotFrames: OpportunityFrame[] = [];

const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((listener) => listener());
}

// 最新在前。无 window（SSR）或解析失败 → []。
export function loadFrames(): OpportunityFrame[] {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(FRAMES_KEY);
  if (raw !== snapshotRaw) {
    snapshotRaw = raw;
    snapshotFrames = parseFrames(raw);
  }
  return snapshotFrames;
}

export function subscribeFrames(onChange: () => void): () => void {
  listeners.add(onChange);
  let removeStorage = () => {};
  if (typeof window !== "undefined") {
    const handler = (event: StorageEvent) => {
      if (event.key === null || event.key === FRAMES_KEY) onChange();
    };
    window.addEventListener("storage", handler);
    removeStorage = () => window.removeEventListener("storage", handler);
  }
  return () => {
    listeners.delete(onChange);
    removeStorage();
  };
}

function writeFrames(frames: OpportunityFrame[]): void {
  window.localStorage.setItem(FRAMES_KEY, JSON.stringify(frames));
  emit();
}

// 按 frame.id 去重，并把被写入的框架置顶（最新在前）。
export function upsertFrame(frame: OpportunityFrame): void {
  if (typeof window === "undefined") return;
  const rest = loadFrames().filter((f) => f.id !== frame.id);
  writeFrames([frame, ...rest]);
}

export function removeFrame(id: string): void {
  if (typeof window === "undefined") return;
  writeFrames(loadFrames().filter((f) => f.id !== id));
}

export function rememberLastFrameId(id: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(LAST_FRAME_ID_KEY, id);
}

// 读取「刚生成」标记（不清除），供渲染期 lazy 初始化安全调用。
export function peekLastFrameId(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(LAST_FRAME_ID_KEY);
}

// 清除「刚生成」标记（在 effect 里调用，幂等）。
export function clearLastFrameId(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(LAST_FRAME_ID_KEY);
}
