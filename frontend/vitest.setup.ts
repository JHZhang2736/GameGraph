import "@testing-library/jest-dom/vitest";

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// React Flow measures its container with ResizeObserver; jsdom has none.
globalThis.ResizeObserver = globalThis.ResizeObserver ?? (ResizeObserverStub as unknown as typeof ResizeObserver);

import { vi } from "vitest";

// Tests must not hit the network. Suites that exercise fetch override this
// per-test (vi.stubGlobal / spyOn); everything else falls back to local logic.
vi.stubGlobal(
  "fetch",
  vi.fn(() => Promise.reject(new Error("network disabled in tests"))),
);
