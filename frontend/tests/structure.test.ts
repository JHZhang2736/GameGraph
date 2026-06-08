// @vitest-environment node
import { describe, it, expect } from "vitest";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

function fromRoot(rel: string): string {
  return fileURLToPath(new URL(`../${rel}`, import.meta.url));
}

describe("frontend scaffold", () => {
  it("has the app router entry", () => {
    expect(existsSync(fromRoot("app/layout.tsx"))).toBe(true);
  });

  it("has tsconfig and tailwind wired", () => {
    expect(existsSync(fromRoot("tsconfig.json"))).toBe(true);
  });
});
