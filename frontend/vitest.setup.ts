import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// React Flow measures its container with ResizeObserver; jsdom has none.
globalThis.ResizeObserver = globalThis.ResizeObserver ?? (ResizeObserverStub as unknown as typeof ResizeObserver);

// jsdom in this setup ships a localStorage object without working methods, so
// give it a real in-memory implementation for tests that persist state.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length() {
    return this.store.size;
  }
  clear() {
    this.store.clear();
  }
  getItem(key: string) {
    return this.store.has(key) ? (this.store.get(key) as string) : null;
  }
  key(index: number) {
    return Array.from(this.store.keys())[index] ?? null;
  }
  removeItem(key: string) {
    this.store.delete(key);
  }
  setItem(key: string, value: string) {
    this.store.set(key, String(value));
  }
}

vi.stubGlobal("localStorage", new MemoryStorage());

// Tests must not hit the network. Suites that exercise fetch override this
// per-test (vi.stubGlobal / spyOn); everything else falls back to local logic.
vi.stubGlobal(
  "fetch",
  vi.fn(() => Promise.reject(new Error("network disabled in tests"))),
);
