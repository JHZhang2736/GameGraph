// Browser-local persistence for the confirmed DeveloperProfile. Once the user
// confirms a profile we keep it in localStorage so re-entering the workbench (or
// any downstream step) restores the same profile instead of starting blank.
import type { DeveloperProfile } from "@/lib/types";

export const STORED_PROFILE_KEY = "gamegraph.developer-profile";

function parseProfile(raw: string | null): DeveloperProfile | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as DeveloperProfile;
  } catch {
    return null;
  }
}

// Cache the parsed snapshot keyed by the raw string so loadStoredProfile returns
// a stable reference while the stored value is unchanged. useSyncExternalStore
// requires this — re-parsing on every call would hand it a new object each time
// and trigger an infinite render loop.
let snapshotRaw: string | null = null;
let snapshotProfile: DeveloperProfile | null = null;

// Returns the saved profile, or null when nothing is stored, the value is
// corrupt, or there is no localStorage (e.g. server-side rendering).
export function loadStoredProfile(): DeveloperProfile | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORED_PROFILE_KEY);
  if (raw !== snapshotRaw) {
    snapshotRaw = raw;
    snapshotProfile = parseProfile(raw);
  }
  return snapshotProfile;
}

// Subscribes to cross-tab changes so a profile confirmed in another tab restores
// here too. Returns the unsubscribe handler useSyncExternalStore expects.
export function subscribeStoredProfile(onChange: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  const handler = (event: StorageEvent) => {
    if (event.key === null || event.key === STORED_PROFILE_KEY) onChange();
  };
  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
}

export function saveStoredProfile(profile: DeveloperProfile): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORED_PROFILE_KEY, JSON.stringify(profile));
}

export function clearStoredProfile(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORED_PROFILE_KEY);
}
