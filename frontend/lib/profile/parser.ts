// Local deterministic developer-profile parser (6.4).
//
// This mirrors the authoritative backend parser in
// backend/app/services/developer_profile_parser.py. Keep both in sync: the
// page only talks to lib/data, so swapping this for a real `fetch` later must
// not change the ProfileParseResult shape or behavior.
import type {
  ConfidenceLevel,
  ConstraintType,
  DeveloperConstraint,
  MissingProfileField,
  ProfileFieldSource,
  ProfileFieldSourceKind,
  ProfileParseInput,
  ProfileParseResult,
} from "@/lib/types";

const BLOCKING_FIELDS = [
  "team_size",
  "time_budget",
  "programming_ability",
  "art_ability",
  "content_production_ability",
  "liked_references",
  "desired_player_experiences",
  "constraints",
] as const;

function containsAny(value: string, needles: string[]): boolean {
  const normalized = value.toLowerCase();
  return needles.some((needle) => normalized.includes(needle.toLowerCase()));
}

function source(
  field: string,
  sourceText: string,
  confidence: ConfidenceLevel = "high",
  sourceKind: ProfileFieldSourceKind = "raw_text",
): ProfileFieldSource {
  return {
    field,
    source_text: sourceText,
    source_kind: sourceKind,
    confidence,
  };
}

function unique(values: string[]): string[] {
  const seen = new Set<string>();
  const output: string[] = [];
  for (const value of values) {
    const normalized = value.toLowerCase();
    if (!seen.has(normalized)) {
      output.push(value);
      seen.add(normalized);
    }
  }
  return output;
}

function constraint(
  id: string,
  type: ConstraintType,
  statement: string,
): DeveloperConstraint {
  return { id, type, statement };
}

function missing(field: string): MissingProfileField {
  return {
    field,
    reason: `Could not infer ${field} from developer profile input.`,
    blocking: true,
  };
}

function ability(
  rawText: string,
  field: string,
  strongTerms: string[],
  weakTerms: string[],
  basicTerms: string[],
): [string | null, ProfileFieldSource | null] {
  if (containsAny(rawText, strongTerms)) return ["strong", source(field, rawText)];
  if (containsAny(rawText, weakTerms)) return ["weak", source(field, rawText)];
  if (containsAny(rawText, basicTerms)) return ["basic", source(field, rawText)];
  return [null, null];
}

export function parseDeveloperProfileInput(
  input: ProfileParseInput,
): ProfileParseResult {
  const rawText = input.raw_text;
  const fieldSources: ProfileFieldSource[] = [];
  const warnings: string[] = [];

  // Team size.
  let teamSize: string | null = null;
  if (containsAny(rawText, ["solo", "一个人", "单人", "独立开发者"])) {
    teamSize = "solo";
    fieldSources.push(source("team_size", rawText));
  } else if (containsAny(rawText, ["两个人", "2人", "小团队"])) {
    teamSize = "small team";
    fieldSources.push(source("team_size", rawText));
  }

  // Time budget. Explicit project scale wins over inferred text.
  let timeBudget: string | null = null;
  const explicitScale = input.expected_project_scale?.trim();
  if (explicitScale) {
    timeBudget = explicitScale;
    fieldSources.push(source("time_budget", explicitScale, "high", "explicit_field"));
  } else if (containsAny(rawText, ["三个月", "3个月", "three month"])) {
    timeBudget = "three month prototype";
    fieldSources.push(source("time_budget", rawText));
  } else if (containsAny(rawText, ["周末", "业余", "part-time"])) {
    timeBudget = "part-time prototype";
    fieldSources.push(source("time_budget", rawText, "medium"));
    warnings.push("Interpreted time budget as part-time prototype.");
  } else if (containsAny(rawText, ["尽快", "短期"])) {
    warnings.push("Time budget is vague and needs clarification.");
  }

  // Capability fields.
  const [programmingAbility, programmingSource] = ability(
    rawText,
    "programming_ability",
    ["程序能力强", "程序强", "擅长编程", "会写系统", "strong programming"],
    ["程序能力弱", "程序弱", "weak programming"],
    ["程序基础", "basic programming"],
  );
  if (programmingSource) fieldSources.push(programmingSource);

  const [artAbility, artSource] = ability(
    rawText,
    "art_ability",
    ["美术能力强", "美术强", "strong art"],
    ["美术能力弱", "美术弱", "不会画", "低美术", "weak art"],
    ["美术基础", "basic art"],
  );
  if (artSource) fieldSources.push(artSource);

  let [audioAbility, audioSource] = ability(
    rawText,
    "audio_ability",
    ["音频能力强", "音频强", "strong audio"],
    ["音频能力弱", "音频弱", "weak audio"],
    ["音频基础", "音频一般", "基础音效", "basic audio"],
  );
  if (audioSource) {
    fieldSources.push(audioSource);
  } else {
    audioAbility = "basic";
    fieldSources.push(source("audio_ability", "defaulted to basic", "low"));
  }

  const contentProductionAbility = containsAny(rawText, [
    "不想做大量内容",
    "内容产能有限",
    "limited content",
  ])
    ? "limited"
    : null;
  if (contentProductionAbility) {
    fieldSources.push(source("content_production_ability", rawText));
  }

  // References. Explicit fields win over inferred mentions.
  let likedReferences: string[];
  if (input.liked_references?.length) {
    likedReferences = unique(input.liked_references);
    fieldSources.push(
      source("liked_references", likedReferences.join(", "), "high", "explicit_field"),
    );
  } else {
    likedReferences = unique(
      ["Balatro", "Into the Breach", "Baba Is You"].filter((reference) =>
        containsAny(rawText, [reference]),
      ),
    );
    if (likedReferences.length) {
      fieldSources.push(source("liked_references", rawText));
    }
  }

  let dislikedReferences: string[];
  if (input.disliked_references_or_mechanics?.length) {
    dislikedReferences = unique(input.disliked_references_or_mechanics);
    fieldSources.push(
      source(
        "disliked_references_or_mechanics",
        dislikedReferences.join(", "),
        "high",
        "explicit_field",
      ),
    );
  } else {
    dislikedReferences = unique(
      (
        [
          ["online multiplayer", ["在线多人", "online multiplayer"]],
          ["long scripted narrative", ["长篇叙事", "long scripted narrative"]],
        ] as const
      )
        .filter(([, terms]) => containsAny(rawText, [...terms]))
        .map(([label]) => label),
    );
    if (dislikedReferences.length) {
      fieldSources.push(source("disliked_references_or_mechanics", rawText));
    }
  }

  // Desired player experiences.
  const desiredExperiences = unique(
    (
      [
        ["short runs", ["短局", "short runs"]],
        ["systemic decisions", ["系统性决策", "systemic decisions"]],
        ["tactical prediction", ["战术预测", "tactical prediction"]],
        ["replayability", ["高重玩", "replayability"]],
      ] as const
    )
      .filter(([, terms]) => containsAny(rawText, [...terms]))
      .map(([label]) => label),
  );
  if (desiredExperiences.length) {
    fieldSources.push(source("desired_player_experiences", rawText));
  }

  // Constraints, graded by wording.
  const constraints: DeveloperConstraint[] = [];
  if (
    containsAny(rawText, [
      "不要做在线多人",
      "不能做在线多人",
      "do not require online multiplayer",
    ])
  ) {
    constraints.push(
      constraint("constraint_no_online", "hard", "Do not require online multiplayer."),
    );
  }
  if (containsAny(rawText, ["不想做长篇叙事", "尽量不要长篇叙事"])) {
    constraints.push(
      constraint(
        "constraint_avoid_long_narrative",
        "strong_preference",
        "Avoid long scripted narrative.",
      ),
    );
  }
  if (containsAny(rawText, ["不想做大量内容", "内容产能有限"])) {
    constraints.push(
      constraint(
        "constraint_limited_content",
        "strong_preference",
        "Prefer concepts with limited content production.",
      ),
    );
  }
  if (constraints.length) {
    fieldSources.push(source("constraints", rawText));
  }

  // Blocking missing fields drive completeness.
  const values: Record<(typeof BLOCKING_FIELDS)[number], string | string[] | null> = {
    team_size: teamSize,
    time_budget: timeBudget,
    programming_ability: programmingAbility,
    art_ability: artAbility,
    content_production_ability: contentProductionAbility,
    liked_references: likedReferences,
    desired_player_experiences: desiredExperiences,
    constraints: constraints.map((item) => item.id),
  };
  const missingFields = BLOCKING_FIELDS.flatMap((field) => {
    const value = values[field];
    const isEmpty =
      value === null || (Array.isArray(value) && value.length === 0);
    return isEmpty ? [missing(field)] : [];
  });

  return {
    draft: {
      id: "profile_draft_current",
      team_size: teamSize,
      time_budget: timeBudget,
      programming_ability: programmingAbility,
      art_ability: artAbility,
      audio_ability: audioAbility,
      content_production_ability: contentProductionAbility,
      liked_references: likedReferences,
      disliked_references_or_mechanics: dislikedReferences,
      desired_player_experiences: desiredExperiences,
      constraints,
      missing_fields: missingFields,
      field_sources: fieldSources,
      raw_text: rawText,
      is_complete: missingFields.length === 0,
    },
    warnings,
  };
}
