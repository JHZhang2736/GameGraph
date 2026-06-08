// 关系类型英→中映射(仅前端展示用,后端不变)。缺失键回退显示原始英文,不丢信息。
const RELATION_LABELS: Record<string, string> = {
  // 结构边类型
  HAS_MECHANIC: "具备机制",
  DELIVERS_EXPERIENCE: "带来体验",
  CLAIM: "论断",
  TAGGED: "标签",
  HAS_GENRE: "类型",
  HAS_ART_STYLE: "美术风格",
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
