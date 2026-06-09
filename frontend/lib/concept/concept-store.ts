// 浏览器侧「最近一次生成的概念」单槽存储（latest-only）。仿 lib/opportunity/frame-history.ts
// 的 useSyncExternalStore 写法：用 raw 字符串缓存解析快照，数据未变时返回稳定引用，
// 避免 useSyncExternalStore 无限重渲染。重新生成即覆盖。
import type { ConceptCard, OpportunityFrame } from "@/lib/types";

export const LATEST_CONCEPTS_KEY = "gamegraph.latest-concepts";

export interface ConceptSet {
  frame: OpportunityFrame;
  cards: ConceptCard[];
}

function parse(raw: string | null): ConceptSet | null {
  if (!raw) return null;
  try {
    const value = JSON.parse(raw);
    if (value && typeof value === "object" && value.frame && Array.isArray(value.cards)) {
      return value as ConceptSet;
    }
    return null;
  } catch {
    return null;
  }
}

let snapshotRaw: string | null = null;
let snapshot: ConceptSet | null = null;

const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((listener) => listener());
}

export function loadLatestConcepts(): ConceptSet | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(LATEST_CONCEPTS_KEY);
  if (raw !== snapshotRaw) {
    snapshotRaw = raw;
    snapshot = parse(raw);
  }
  return snapshot;
}

export function subscribeConcepts(onChange: () => void): () => void {
  listeners.add(onChange);
  let removeStorage = () => {};
  if (typeof window !== "undefined") {
    const handler = (event: StorageEvent) => {
      if (event.key === null || event.key === LATEST_CONCEPTS_KEY) onChange();
    };
    window.addEventListener("storage", handler);
    removeStorage = () => window.removeEventListener("storage", handler);
  }
  return () => {
    listeners.delete(onChange);
    removeStorage();
  };
}

export function saveConcepts(frame: OpportunityFrame, cards: ConceptCard[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(LATEST_CONCEPTS_KEY, JSON.stringify({ frame, cards }));
  emit();
}

export function clearConcepts(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(LATEST_CONCEPTS_KEY);
  emit();
}
