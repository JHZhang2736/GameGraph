// 按开发者画像分键的「机会发现看板」浏览器持久化:累积已保留的机会(areas)与
// 已见候选 id(seen_ids,用于跨批去重)。纯 localStorage,刷新/重进可恢复。
import type { OpportunityArea } from "@/lib/types";

export interface OpportunityBoard {
  areas: OpportunityArea[];
  seen_ids: string[];
}

const EMPTY_BOARD: OpportunityBoard = { areas: [], seen_ids: [] };

function key(profileId: string): string {
  return `gamegraph.opportunity-board.${profileId}`;
}

export function loadBoard(profileId: string): OpportunityBoard {
  if (typeof window === "undefined") return EMPTY_BOARD;
  const raw = window.localStorage.getItem(key(profileId));
  if (!raw) return EMPTY_BOARD;
  try {
    const parsed = JSON.parse(raw) as Partial<OpportunityBoard>;
    return {
      areas: Array.isArray(parsed.areas) ? parsed.areas : [],
      seen_ids: Array.isArray(parsed.seen_ids) ? parsed.seen_ids : [],
    };
  } catch {
    return EMPTY_BOARD;
  }
}

export function saveBoard(profileId: string, board: OpportunityBoard): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key(profileId), JSON.stringify(board));
}

export function clearBoard(profileId: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(key(profileId));
}
