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
// The implementation also mirrors the browser Storage key-enumeration contract:
// Object.keys(localStorage) returns the stored keys, not internal properties.
function makeMemoryStorage(): Storage {
  // Keep backing data in a closure so it never appears as an own enumerable
  // property, leaving Object.keys(storage) to return only actual storage keys.
  const _store = new Map<string, string>();
  const storage: Storage = {
    get length() {
      return _store.size;
    },
    clear() {
      for (const key of Array.from(_store.keys())) {
        // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
        delete (storage as Record<string, unknown>)[key];
      }
      _store.clear();
    },
    getItem(key: string) {
      return _store.has(key) ? (_store.get(key) as string) : null;
    },
    key(index: number) {
      return Array.from(_store.keys())[index] ?? null;
    },
    removeItem(key: string) {
      _store.delete(key);
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete (storage as Record<string, unknown>)[key];
    },
    setItem(key: string, value: string) {
      _store.set(key, String(value));
      // Expose as own enumerable property so Object.keys(localStorage) works,
      // matching the browser Storage enumeration contract.
      (storage as Record<string, unknown>)[key] = String(value);
    },
  };
  return storage;
}

vi.stubGlobal("localStorage", makeMemoryStorage());

// Tests must not hit the network. Suites that exercise fetch override this
// per-test (vi.stubGlobal / spyOn); everything else falls back to local logic.
vi.stubGlobal(
  "fetch",
  vi.fn(() => Promise.reject(new Error("network disabled in tests"))),
);
