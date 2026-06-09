// 节点类型注册表:颜色 + 中文名,与后端节点 label 对齐
// (见 backend import_service.PROFILE_LIST_EDGES,外加 Game / Concept / ReferenceTag)。
// 图例(GraphLegend)、节点上色都以此为唯一来源。
export interface NodeTypeMeta {
  type: string;
  color: string;
  label: string;
}

export const NODE_TYPES: NodeTypeMeta[] = [
  { type: "Game", color: "#4f46e5", label: "游戏" },
  { type: "Mechanic", color: "#818cf8", label: "机制" },
  { type: "PlayerAction", color: "#6366f1", label: "玩家行为" },
  { type: "PlayerDecision", color: "#a78bfa", label: "玩家决策" },
  { type: "Experience", color: "#14b8a6", label: "体验" },
  { type: "ProductionConstraint", color: "#f97316", label: "生产约束" },
  { type: "InnovationPattern", color: "#ec4899", label: "创新模式" },
  { type: "ReferencePattern", color: "#0ea5e9", label: "可复用范式" },
  { type: "Risk", color: "#dc2626", label: "不可复制风险" },
  { type: "ReplayabilitySource", color: "#22c55e", label: "重玩性来源" },
  { type: "Genre", color: "#8b5cf6", label: "类型" },
  { type: "ArtStyle", color: "#f59e0b", label: "美术风格" },
  { type: "AudioStyle", color: "#eab308", label: "音频风格" },
  { type: "Perspective", color: "#06b6d4", label: "视角" },
  { type: "Theme", color: "#d946ef", label: "主题" },
  { type: "NarrativeStyle", color: "#84cc16", label: "叙事风格" },
  { type: "GameFeel", color: "#fb7185", label: "游戏手感" },
  { type: "TeamModel", color: "#64748b", label: "团队模式" },
  { type: "Concept", color: "#f87171", label: "概念" },
  { type: "ReferenceTag", color: "#fbbf24", label: "参考标签" },
];

const COLOR_BY_TYPE = new Map(NODE_TYPES.map((t) => [t.type, t.color]));
const LABEL_BY_TYPE = new Map(NODE_TYPES.map((t) => [t.type, t.label]));

export const DEFAULT_NODE_COLOR = "#94a3b8";

export function nodeColor(nodeType: string): string {
  return COLOR_BY_TYPE.get(nodeType) ?? DEFAULT_NODE_COLOR;
}

// 未知类型回退显示原始英文,不丢信息。
export function nodeTypeLabel(nodeType: string): string {
  return LABEL_BY_TYPE.get(nodeType) ?? nodeType;
}

// 节点半径按连接数(degree)增长并 clamp;焦点节点连接最多故自然最大。
export function nodeSize(degree: number): number {
  const raw = 6 + degree * 0.1;
  return Math.min(Math.max(raw, 6), 20);
}
