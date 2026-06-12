// Chinese display labels for the structured-preview dropdowns, mapped to the
// canonical (English) values the parser/LLM and downstream contract use. The UI
// shows Chinese; the stored value stays canonical so nothing downstream changes.

export interface FieldOption {
  value: string;
  label: string;
}

export type ScalarFieldKey =
  | "team_size"
  | "time_budget"
  | "programming_ability"
  | "art_ability"
  | "audio_ability"
  | "content_production_ability";

const ABILITY_OPTIONS: FieldOption[] = [
  { value: "strong", label: "强" },
  { value: "basic", label: "一般" },
  { value: "weak", label: "弱" },
];

export const SCALAR_FIELD_OPTIONS: Record<ScalarFieldKey, FieldOption[]> = {
  team_size: [
    { value: "solo", label: "独立开发者（单人）" },
    { value: "small team", label: "小团队" },
  ],
  time_budget: [
    { value: "three month prototype", label: "三个月原型" },
    { value: "six week prototype", label: "六周原型" },
    { value: "part-time prototype", label: "业余 / 周末原型" },
  ],
  programming_ability: ABILITY_OPTIONS,
  art_ability: ABILITY_OPTIONS,
  audio_ability: ABILITY_OPTIONS,
  content_production_ability: [
    { value: "full", label: "充足" },
    { value: "limited", label: "有限" },
  ],
};

// 可靶向的玩家体验 = 后端 synergy_rules.json 里所有 distinct experience。
// desired_player_experiences 的取值须与这些字符串一致，匹配上才驱动机会匹配的「画像靶向」
// （命中则该体验的机会优先；选 0 个则退化为全量机会空间）。
// 新增/修改协同规则的 experience 时，请同步此列表。
export const DESIRED_EXPERIENCE_OPTIONS: string[] = [
  "欢乐混乱",
  "战斗精通",
  "构筑乐趣",
  "涌现玩法",
  "运筹帷幄",
  "滚雪球快感",
  "协作默契",
  "收集养成",
  "氛围营造",
  "经营成就",
  "竞技紧张",
  "情感叙事",
  "探索发现",
  "个性化表达",
];

// Returns the Chinese label for a canonical value, or the raw value for custom
// inputs that aren't in the preset list. Empty/null yields "".
export function scalarLabel(field: ScalarFieldKey, value: string | null): string {
  if (!value) return "";
  return SCALAR_FIELD_OPTIONS[field].find((o) => o.value === value)?.label ?? value;
}
