// 关系类型英→中映射(仅前端展示用,后端不变)。缺失键回退显示原始英文,不丢信息。
const RELATION_LABELS: Record<string, string> = {
  // 结构边类型(与 backend import_service.PROFILE_LIST_EDGES 对齐)
  HAS_MECHANIC: "具备机制",
  TAKES_ACTION: "玩家行为",
  MAKES_DECISION: "玩家决策",
  DELIVERS_EXPERIENCE: "带来体验",
  CONSTRAINED_BY: "受约束于",
  USES_INNOVATION: "采用创新",
  REUSABLE_PATTERN: "可复用范式",
  NON_REPLICABLE_RISK: "不可复制风险",
  HAS_REPLAYABILITY_SOURCE: "重玩性来源",
  HAS_GENRE: "类型",
  HAS_ART_STYLE: "美术风格",
  HAS_AUDIO_STYLE: "音频风格",
  HAS_PERSPECTIVE: "视角",
  HAS_THEME: "主题",
  HAS_NARRATIVE_STYLE: "叙事风格",
  HAS_GAME_FEEL: "游戏手感",
  HAS_TEAM_MODEL: "团队模式",
  CLAIM: "论断",
  TAGGED: "标签",
  // claim 的 relation 值
  reinforces: "强化",
  enables: "使能",
  tensions_with: "张力",
  requires: "需要",
  contrasts_with: "对比",
};

export function relationLabel(relation: string): string {
  return RELATION_LABELS[relation] ?? relation;
}
