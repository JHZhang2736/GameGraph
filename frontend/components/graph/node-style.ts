// 节点按类型上色,沿用迁移前的色板。
const NODE_COLORS: Record<string, string> = {
  Game: "#4f46e5",
  Mechanic: "#818cf8",
  PlayerAction: "#818cf8",
  PlayerDecision: "#818cf8",
  Experience: "#14b8a6",
  Concept: "#f87171",
  ReferenceTag: "#f59e0b",
};

const DEFAULT_NODE_COLOR = "#94a3b8";

export function nodeColor(nodeType: string): string {
  return NODE_COLORS[nodeType] ?? DEFAULT_NODE_COLOR;
}

// 节点半径按连接数(degree)增长并 clamp;焦点节点连接最多故自然最大。
export function nodeSize(degree: number): number {
  const raw = 6 + degree * 1.2;
  return Math.min(Math.max(raw, 6), 20);
}
