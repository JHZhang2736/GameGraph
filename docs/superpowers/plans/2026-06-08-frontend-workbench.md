# Frontend Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first frontend slice: a Next.js App Router workbench that renders all seven GameGraph artifact views (plus an overview) read-only from local deterministic mock data, with a swappable data-access layer and TanStack Query.

**Architecture:** A `frontend/` Next.js (App Router, TypeScript) app. TypeScript types mirror the backend Pydantic artifacts. A typed fixture (`golden-flow`) feeds an async data-access layer (`lib/data`) consumed only through TanStack Query hooks (`lib/queries`), so swapping fixtures for a real API later changes no page code. A sidebar + master-detail shell (`components/shell`) hosts eight routes. Reusable artifact components (`components/artifacts`) keep evidence/confidence/quality rendering consistent and downgrade low-confidence material. React Flow renders the knowledge graph.

**Tech Stack:** Next.js (App Router) · React · TypeScript · Tailwind CSS · shadcn/ui · Radix · lucide-react · TanStack Query · @xyflow/react (React Flow) · Vitest + React Testing Library.

---

## File Structure

- `frontend/` — Next.js project root (created by create-next-app).
- `frontend/app/layout.tsx` — root layout; mounts `Providers`.
- `frontend/app/providers.tsx` — client component; wraps `QueryClientProvider`.
- `frontend/app/page.tsx` — redirects `/` → `/overview`.
- `frontend/app/(workbench)/layout.tsx` — workbench shell (sidebar + topbar).
- `frontend/app/(workbench)/overview/page.tsx` — overview view.
- `frontend/app/(workbench)/games/page.tsx` — seed game list.
- `frontend/app/(workbench)/games/[id]/page.tsx` — game design profile + claims.
- `frontend/app/(workbench)/graph/page.tsx` — knowledge graph (React Flow).
- `frontend/app/(workbench)/profile/page.tsx` — developer profile.
- `frontend/app/(workbench)/opportunities/page.tsx` — opportunity frame.
- `frontend/app/(workbench)/concepts/page.tsx` — concept cards + evaluation.
- `frontend/app/(workbench)/prototype/page.tsx` — prototype brief.
- `frontend/lib/types/index.ts` — artifact + shared TS types.
- `frontend/lib/fixtures/golden-flow.ts` — typed mock mirroring `golden_flow.json` + frontend-only artifacts.
- `frontend/lib/data/index.ts` — async data-access functions (read fixtures now, `fetch` later).
- `frontend/lib/queries/index.ts` — TanStack Query hooks.
- `frontend/lib/nav.ts` — sidebar navigation config.
- `frontend/components/shell/*` — `app-sidebar.tsx`, `top-bar.tsx`, `task-progress.tsx`.
- `frontend/components/artifacts/*` — `confidence-badge.tsx`, `quality-badge.tsx`, `evidence-list.tsx`, `claim-row.tsx`, `constraint-tag.tsx`, `artifact-card.tsx`.
- `frontend/components/graph/graph-canvas.tsx` — React Flow wrapper.
- `frontend/components/ui/*` — shadcn primitives (generated).
- `frontend/lib/utils.ts` — shadcn `cn` helper (generated).
- Tests co-located as `*.test.tsx` / `*.test.ts` next to the unit under test.

Run scaffold/install commands from repo root `D:\Files\GameGraph`. Run app/test commands from `frontend/` unless a command shows an explicit `--prefix`.

---

### Task 1: Scaffold Next.js App, Tailwind, And Vitest

**Files:**
- Create: `frontend/` (entire Next.js scaffold)
- Create: `frontend/vitest.config.ts`
- Create: `frontend/vitest.setup.ts`
- Create: `frontend/tests/structure.test.ts`
- Modify: `frontend/package.json` (add test script)

- [ ] **Step 1: Create the Next.js app**

Run from repo root:

```powershell
npx --yes create-next-app@latest frontend --typescript --tailwind --app --eslint --no-src-dir --import-alias "@/*" --use-npm --turbopack
```

Expected: a `frontend/` directory is created with `app/`, `package.json`, `tailwind`/`postcss` config, and `tsconfig.json`. If prompted about any option not covered by flags, accept defaults.

- [ ] **Step 2: Install runtime and test dependencies**

Run from repo root:

```powershell
npm --prefix frontend install @tanstack/react-query @xyflow/react lucide-react
npm --prefix frontend install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/dom @testing-library/jest-dom @testing-library/user-event
```

Expected: pip-style success; `package.json` lists these under `dependencies` / `devDependencies`.

- [ ] **Step 3: Add the test script**

In `frontend/package.json`, add a `"test"` script inside the existing `"scripts"` object:

```json
    "test": "vitest run",
    "test:watch": "vitest"
```

- [ ] **Step 4: Create Vitest config**

Create `frontend/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    css: false,
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./", import.meta.url)),
    },
  },
});
```

- [ ] **Step 5: Create Vitest setup file**

Create `frontend/vitest.setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 6: Write the structure test**

Create `frontend/tests/structure.test.ts`:

```ts
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
```

- [ ] **Step 7: Run the structure test**

Run from `frontend/`:

```powershell
npm test
```

Expected: `2 passed`.

- [ ] **Step 8: Commit**

```powershell
git add frontend
git commit -m "Scaffold Next.js frontend with Tailwind and Vitest"
```

---

### Task 2: Initialize shadcn/ui And Base Primitives

**Files:**
- Create: `frontend/components.json`
- Create: `frontend/components/ui/*` (generated primitives)
- Create/Modify: `frontend/lib/utils.ts` (generated `cn`)
- Modify: `frontend/app/globals.css` (shadcn theme tokens)

- [ ] **Step 1: Initialize shadcn**

Run from `frontend/`:

```powershell
npx --yes shadcn@latest init -d -b neutral
```

Expected: creates `components.json`, writes theme tokens into `app/globals.css`, and creates `lib/utils.ts` with a `cn` helper. `-d` accepts defaults; `-b neutral` selects the neutral base color.

- [ ] **Step 2: Add the primitives the views need**

Run from `frontend/`:

```powershell
npx --yes shadcn@latest add button card badge table separator skeleton scroll-area tabs tooltip
```

Expected: files appear under `frontend/components/ui/` (e.g. `button.tsx`, `card.tsx`, `badge.tsx`, `table.tsx`, `separator.tsx`, `skeleton.tsx`, `scroll-area.tsx`, `tabs.tsx`, `tooltip.tsx`).

- [ ] **Step 3: Verify the build still type-checks**

Run from `frontend/`:

```powershell
npx tsc --noEmit
```

Expected: no type errors.

- [ ] **Step 4: Commit**

```powershell
git add frontend/components.json frontend/components/ui frontend/lib/utils.ts frontend/app/globals.css
git commit -m "Add shadcn/ui base primitives"
```

---

### Task 3: Artifact And Shared Types

**Files:**
- Create: `frontend/lib/types/index.ts`
- Create: `frontend/lib/types/types.test.ts`

- [ ] **Step 1: Write a failing test for the type module**

Create `frontend/lib/types/types.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import {
  CONFIDENCE_LEVELS,
  QUALITY_STATUSES,
  CONSTRAINT_TYPES,
  EVALUATION_CATEGORIES,
} from "@/lib/types";

describe("shared type constants", () => {
  it("exposes confidence levels", () => {
    expect(CONFIDENCE_LEVELS).toEqual(["low", "medium", "high"]);
  });

  it("exposes quality statuses", () => {
    expect(QUALITY_STATUSES).toEqual([
      "draft",
      "reviewed",
      "weak_evidence",
      "conflicting",
    ]);
  });

  it("exposes constraint types", () => {
    expect(CONSTRAINT_TYPES).toEqual([
      "hard",
      "strong_preference",
      "soft_preference",
    ]);
  });

  it("exposes evaluation categories", () => {
    expect(EVALUATION_CATEGORIES).toEqual(["safe", "balanced", "challenging"]);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `frontend/`:

```powershell
npm test -- lib/types/types.test.ts
```

Expected: FAIL with a module-not-found / import error for `@/lib/types`.

- [ ] **Step 3: Implement the types**

Create `frontend/lib/types/index.ts`:

```ts
// Shared enums (mirror backend app/schemas/common.py).
export const CONFIDENCE_LEVELS = ["low", "medium", "high"] as const;
export type ConfidenceLevel = (typeof CONFIDENCE_LEVELS)[number];

export const QUALITY_STATUSES = [
  "draft",
  "reviewed",
  "weak_evidence",
  "conflicting",
] as const;
export type QualityStatus = (typeof QUALITY_STATUSES)[number];

export const CONSTRAINT_TYPES = [
  "hard",
  "strong_preference",
  "soft_preference",
] as const;
export type ConstraintType = (typeof CONSTRAINT_TYPES)[number];

export interface EvidenceRef {
  title: string;
  url?: string;
  quote_or_summary?: string;
  notes: string;
}

// Core artifacts (mirror backend app/schemas/artifacts.py).
export interface SeedGame {
  id: string;
  title: string;
  source_refs: EvidenceRef[];
  short_description: string;
  selection_reason: string;
}

export interface DesignClaim {
  id: string;
  subject: string;
  relation: string;
  object: string;
  explanation: string;
  evidence: EvidenceRef[];
  confidence: ConfidenceLevel;
  quality_status: QualityStatus;
}

export interface GraphRelation {
  id: string;
  source_node: string;
  relation: string;
  target_node: string;
  claim_id: string;
  evidence: EvidenceRef[];
  confidence: ConfidenceLevel;
  quality_status: QualityStatus;
}

export interface DeveloperConstraint {
  id: string;
  type: ConstraintType;
  statement: string;
}

export interface DeveloperProfile {
  id: string;
  team_size: string;
  time_budget: string;
  programming_ability: string;
  art_ability: string;
  audio_ability: string;
  content_production_ability: string;
  liked_references: string[];
  disliked_references_or_mechanics: string[];
  desired_player_experiences: string[];
  constraints: DeveloperConstraint[];
}

export interface OpportunityFrame {
  id: string;
  developer_profile_id: string;
  opportunity_area: string;
  source_game_ids: string[];
  related_mechanics: string[];
  related_player_experiences: string[];
  related_constraints: string[];
  related_innovation_patterns: string[];
  recommended_transformations: string[];
  forbidden_directions: string[];
  evidence_path: string[];
  fit_reason: string;
  risk_reason: string;
}

export interface ConceptCard {
  id: string;
  opportunity_frame_id: string;
  title: string;
  one_sentence_concept: string;
  core_fantasy: string;
  core_loop: string;
  main_player_decisions: string[];
  main_mechanics: string[];
  reference_sources: string[];
  difference_from_references: string;
  fit_reason: string;
  production_risks: string[];
  design_risks: string[];
  novelty_reason: string;
  suggested_prototype_scope: string;
}

export interface PrototypeBrief {
  id: string;
  concept_card_id: string;
  largest_risk_hypothesis: string;
  minimum_prototype_scope: string;
  target_playtest_duration: string;
  success_signals: string[];
  failure_signals: string[];
  do_not_build_yet: string[];
}

// Frontend-only artifacts. The backend fixture contract does not yet implement
// full GameDesignProfile / ConceptEvaluation; these shapes drive the read-only
// views and will be aligned with the backend schema once it lands.
export interface GameDesignProfile {
  id: string;
  game_id: string;
  one_sentence_summary: string;
  core_loop: string;
  main_player_actions: string[];
  main_player_decisions: string[];
  main_experiences: string[];
  main_mechanics: string[];
  reference_value_tags: string[];
  hard_to_copy_risks: string[];
  evidence: EvidenceRef[];
  confidence: ConfidenceLevel;
  quality_status: QualityStatus;
}

export const EVALUATION_CATEGORIES = [
  "safe",
  "balanced",
  "challenging",
] as const;
export type EvaluationCategory = (typeof EVALUATION_CATEGORIES)[number];

export interface ConceptEvaluation {
  id: string;
  concept_card_id: string;
  fit_score: number;
  feasibility_score: number;
  novelty_score: number;
  risk_score: number;
  evidence_quality_score: number;
  category: EvaluationCategory;
  notes: string;
}

// Whole-flow shape, equivalent to backend FixturePipelineResult.
export interface GoldenFlow {
  seed_games: SeedGame[];
  design_claims: DesignClaim[];
  graph_relations: GraphRelation[];
  developer_profile: DeveloperProfile;
  opportunity_frame: OpportunityFrame;
  concept_cards: ConceptCard[];
  prototype_brief: PrototypeBrief;
  game_design_profiles: GameDesignProfile[];
  concept_evaluations: ConceptEvaluation[];
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `frontend/`:

```powershell
npm test -- lib/types/types.test.ts
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```powershell
git add frontend/lib/types
git commit -m "Add frontend artifact and shared types"
```

---
### Task 4: Fixture, Data Layer, Query Hooks, And Providers

**Files:**
- Create: `frontend/lib/fixtures/golden-flow.ts`
- Create: `frontend/lib/data/index.ts`
- Create: `frontend/lib/data/data.test.ts`
- Create: `frontend/lib/queries/index.ts`
- Create: `frontend/app/providers.tsx`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Create the typed fixture**

Create `frontend/lib/fixtures/golden-flow.ts` (mirrors backend `golden_flow.json`, plus frontend-only `game_design_profiles` and `concept_evaluations`):

```ts
import type { GoldenFlow } from "@/lib/types";

export const goldenFlow: GoldenFlow = {
  seed_games: [
    {
      id: "game_balatro",
      title: "Balatro",
      source_refs: [
        {
          title: "Balatro store page",
          url: "https://store.steampowered.com/app/2379780/Balatro/",
          notes: "Primary reference for the game candidate.",
        },
      ],
      short_description:
        "Poker-inspired roguelike deckbuilder built around familiar card semantics.",
      selection_reason:
        "Strong sample for transforming familiar rules into systemic depth.",
    },
    {
      id: "game_into_the_breach",
      title: "Into the Breach",
      source_refs: [
        {
          title: "Into the Breach store page",
          url: "https://store.steampowered.com/app/590380/Into_the_Breach/",
          notes: "Primary reference for the game candidate.",
        },
      ],
      short_description:
        "Compact tactical game using small boards, complete information, and readable enemy intent.",
      selection_reason:
        "Strong sample for high tactical depth with constrained presentation scope.",
    },
    {
      id: "game_baba_is_you",
      title: "Baba Is You",
      source_refs: [
        {
          title: "Baba Is You store page",
          url: "https://store.steampowered.com/app/736260/Baba_Is_You/",
          notes: "Primary reference for the game candidate.",
        },
      ],
      short_description:
        "Puzzle game where players manipulate explicit rules as objects.",
      selection_reason:
        "Strong sample for rule manipulation as a central design pattern.",
    },
  ],
  design_claims: [
    {
      id: "claim_balatro_familiar_rules",
      subject: "Balatro",
      relation: "uses",
      object: "familiar card rules to reduce learning cost",
      explanation:
        "Poker-like hands give players an immediate rules vocabulary before modifiers add depth.",
      evidence: [
        {
          title: "Balatro design summary",
          quote_or_summary:
            "The game starts from recognizable poker hand logic and layers score modifiers over it.",
          notes: "Curated design interpretation for the fixture.",
        },
      ],
      confidence: "high",
      quality_status: "reviewed",
    },
    {
      id: "claim_breach_compact_tactics",
      subject: "Into the Breach",
      relation: "creates",
      object: "high tactical depth through compact boards and visible enemy intent",
      explanation:
        "Small boards and readable future actions let players reason about consequences without large production scope.",
      evidence: [
        {
          title: "Into the Breach design summary",
          quote_or_summary:
            "Encounters emphasize small grids, visible threats, and consequence planning.",
          notes: "Curated design interpretation for the fixture.",
        },
      ],
      confidence: "high",
      quality_status: "reviewed",
    },
    {
      id: "claim_baba_rule_manipulation",
      subject: "Baba Is You",
      relation: "demonstrates",
      object: "rule manipulation as player-facing interaction",
      explanation: "Rules become explicit objects that players can inspect and alter.",
      evidence: [
        {
          title: "Baba Is You design summary",
          quote_or_summary:
            "Puzzle rules are represented as manipulable language-like objects.",
          notes: "Curated design interpretation for the fixture.",
        },
      ],
      confidence: "high",
      quality_status: "reviewed",
    },
    {
      id: "claim_symbolic_ui_low_art_cost",
      subject: "symbolic tactical UI",
      relation: "may_reduce",
      object: "animation and asset production burden",
      explanation:
        "Abstract symbolic feedback can reduce art load, but this depends on clarity and feedback design.",
      evidence: [
        {
          title: "Curator hypothesis",
          quote_or_summary:
            "Symbolic UI is expected to be cheaper than animation-heavy combat for a solo prototype.",
          notes: "Weak evidence included to prove downstream confidence handling.",
        },
      ],
      confidence: "low",
      quality_status: "weak_evidence",
    },
  ],
  graph_relations: [
    {
      id: "rel_claim_balatro_familiar_rules",
      source_node: "Balatro",
      relation: "uses",
      target_node: "familiar card rules to reduce learning cost",
      claim_id: "claim_balatro_familiar_rules",
      evidence: [
        {
          title: "Balatro design summary",
          quote_or_summary:
            "The game starts from recognizable poker hand logic and layers score modifiers over it.",
          notes: "Curated design interpretation for the fixture.",
        },
      ],
      confidence: "high",
      quality_status: "reviewed",
    },
    {
      id: "rel_claim_breach_compact_tactics",
      source_node: "Into the Breach",
      relation: "creates",
      target_node: "high tactical depth through compact boards and visible enemy intent",
      claim_id: "claim_breach_compact_tactics",
      evidence: [
        {
          title: "Into the Breach design summary",
          quote_or_summary:
            "Encounters emphasize small grids, visible threats, and consequence planning.",
          notes: "Curated design interpretation for the fixture.",
        },
      ],
      confidence: "high",
      quality_status: "reviewed",
    },
    {
      id: "rel_claim_baba_rule_manipulation",
      source_node: "Baba Is You",
      relation: "demonstrates",
      target_node: "rule manipulation as player-facing interaction",
      claim_id: "claim_baba_rule_manipulation",
      evidence: [
        {
          title: "Baba Is You design summary",
          quote_or_summary:
            "Puzzle rules are represented as manipulable language-like objects.",
          notes: "Curated design interpretation for the fixture.",
        },
      ],
      confidence: "high",
      quality_status: "reviewed",
    },
    {
      id: "rel_claim_symbolic_ui_low_art_cost",
      source_node: "symbolic tactical UI",
      relation: "may_reduce",
      target_node: "animation and asset production burden",
      claim_id: "claim_symbolic_ui_low_art_cost",
      evidence: [
        {
          title: "Curator hypothesis",
          quote_or_summary:
            "Symbolic UI is expected to be cheaper than animation-heavy combat for a solo prototype.",
          notes: "Weak evidence included to prove downstream confidence handling.",
        },
      ],
      confidence: "low",
      quality_status: "weak_evidence",
    },
  ],
  developer_profile: {
    id: "profile_solo_systems",
    team_size: "solo",
    time_budget: "three month prototype",
    programming_ability: "strong",
    art_ability: "weak",
    audio_ability: "basic",
    content_production_ability: "limited",
    liked_references: ["Balatro", "Into the Breach"],
    disliked_references_or_mechanics: ["online multiplayer", "long scripted narrative"],
    desired_player_experiences: ["short runs", "systemic decisions", "tactical prediction"],
    constraints: [
      {
        id: "constraint_no_online",
        type: "hard",
        statement: "Do not require online multiplayer.",
      },
      {
        id: "constraint_low_art",
        type: "strong_preference",
        statement: "Prefer concepts that can start with symbolic or low-volume art.",
      },
    ],
  },
  opportunity_frame: {
    id: "frame_rule_tactics",
    developer_profile_id: "profile_solo_systems",
    opportunity_area: "Low-art, short-run tactical rule manipulation.",
    source_game_ids: ["game_balatro", "game_into_the_breach", "game_baba_is_you"],
    related_mechanics: ["rule modification", "compact tactical boards", "familiar rule vocabulary"],
    related_player_experiences: ["tactical prediction", "chain satisfaction", "emergent problem solving"],
    related_constraints: ["weak art ability", "three month prototype", "solo development"],
    related_innovation_patterns: ["combine rule editing with short tactical runs"],
    recommended_transformations: [
      "compress tactical space into a small board",
      "replace animation-heavy feedback with symbolic state changes",
      "combine editable rules with short encounter runs",
    ],
    forbidden_directions: [
      "online multiplayer",
      "large open world",
      "long scripted narrative",
      "animation-heavy combat",
    ],
    evidence_path: [
      "claim_balatro_familiar_rules",
      "claim_breach_compact_tactics",
      "claim_baba_rule_manipulation",
      "claim_symbolic_ui_low_art_cost",
    ],
    fit_reason:
      "The area emphasizes systemic depth and readable rules over asset volume, matching a strong-programming solo developer with weak art capacity.",
    risk_reason:
      "The largest risk is whether players can understand rule consequences quickly enough for short tactical runs.",
  },
  concept_cards: [
    {
      id: "concept_ruleforge_tactics",
      opportunity_frame_id: "frame_rule_tactics",
      title: "Ruleforge Tactics",
      one_sentence_concept:
        "A short-run tactics game where players win by editing small battlefield rules instead of directly commanding every unit.",
      core_fantasy: "Outsmarting a compact battlefield by rewriting its laws.",
      core_loop:
        "Inspect enemy intents, draft rule cards, apply one rule change, resolve the turn, and adapt the next encounter.",
      main_player_decisions: [
        "which battlefield rule to alter",
        "when to accept a risky rule interaction",
        "which encounter reward supports the current rule plan",
      ],
      main_mechanics: ["4x4 tactical board", "rule cards", "visible enemy intent", "short encounter chain"],
      reference_sources: ["Balatro", "Into the Breach", "Baba Is You"],
      difference_from_references:
        "It uses tactical forecasting and rule manipulation, but turns them into short encounter runs rather than poker scoring, pure tactics, or puzzle levels.",
      fit_reason:
        "The concept can begin with symbols, simple boards, and rules-first feedback before any polished asset work.",
      production_risks: [
        "rule interactions need readable feedback",
        "symbolic presentation may still require careful UI polish",
      ],
      design_risks: [
        "players may not predict rule consequences",
        "runs may feel arbitrary if rule feedback is unclear",
      ],
      novelty_reason:
        "It combines rule editing with tactical run structure under low-art production constraints.",
      suggested_prototype_scope: "A 4x4 board, three unit types, six rule cards, and five encounters.",
    },
  ],
  prototype_brief: {
    id: "brief_ruleforge_tactics",
    concept_card_id: "concept_ruleforge_tactics",
    largest_risk_hypothesis:
      "Players can understand and enjoy changing battlefield rules within the first few minutes.",
    minimum_prototype_scope: "A 4x4 board, three unit types, six rule cards, and five encounters.",
    target_playtest_duration: "10 minutes",
    success_signals: [
      "player can explain a rule consequence after one encounter",
      "player voluntarily restarts to try a different rule combination",
    ],
    failure_signals: [
      "player says outcomes feel arbitrary",
      "player cannot predict what a rule change will affect",
    ],
    do_not_build_yet: ["campaign progression", "polished art", "large content set", "online features"],
  },
  game_design_profiles: [
    {
      id: "profile_balatro",
      game_id: "game_balatro",
      one_sentence_summary:
        "A roguelike deckbuilder that layers score modifiers over familiar poker hands.",
      core_loop: "Play hands, bank chips, buy jokers, push a rising score target each round.",
      main_player_actions: ["select cards", "play or discard hands", "buy modifiers"],
      main_player_decisions: ["which hand to commit", "which joker synergy to chase"],
      main_experiences: ["escalating combos", "build optimization"],
      main_mechanics: ["poker hands", "score modifiers", "shop drafting"],
      reference_value_tags: ["mechanic-distinct", "low-art reference", "high systemic depth"],
      hard_to_copy_risks: ["balance of exponential scoring is hard to tune"],
      evidence: [
        {
          title: "Balatro design summary",
          quote_or_summary: "Recognizable poker logic with score modifiers layered on top.",
          notes: "Curated design interpretation for the fixture.",
        },
      ],
      confidence: "high",
      quality_status: "reviewed",
    },
    {
      id: "profile_into_the_breach",
      game_id: "game_into_the_breach",
      one_sentence_summary:
        "A compact tactics game built on complete information and readable enemy intent.",
      core_loop: "Read enemy intents, reposition, block or redirect attacks, protect the grid.",
      main_player_actions: ["move mechs", "trigger attacks", "shield buildings"],
      main_player_decisions: ["which threat to neutralize", "what to sacrifice"],
      main_experiences: ["puzzle-like tactics", "consequence planning"],
      main_mechanics: ["small grid", "visible enemy intent", "positional pushing"],
      reference_value_tags: ["high systemic depth", "low-art reference", "solo-friendly reference"],
      hard_to_copy_risks: ["perfect-information design needs careful encounter authoring"],
      evidence: [
        {
          title: "Into the Breach design summary",
          quote_or_summary: "Small grids, visible threats, and consequence planning.",
          notes: "Curated design interpretation for the fixture.",
        },
      ],
      confidence: "high",
      quality_status: "reviewed",
    },
  ],
  concept_evaluations: [
    {
      id: "eval_ruleforge_tactics",
      concept_card_id: "concept_ruleforge_tactics",
      fit_score: 4,
      feasibility_score: 3,
      novelty_score: 4,
      risk_score: 3,
      evidence_quality_score: 3,
      category: "balanced",
      notes:
        "Strong fit for a systems-first solo developer; main uncertainty is whether rule feedback reads clearly enough.",
    },
  ],
};
```

- [ ] **Step 2: Write a failing test for the data layer**

Create `frontend/lib/data/data.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { getGoldenFlow, getGameProfile, getGraph } from "@/lib/data";

describe("data layer", () => {
  it("returns the whole golden flow", async () => {
    const flow = await getGoldenFlow();
    expect(flow.seed_games).toHaveLength(3);
    expect(flow.design_claims).toHaveLength(4);
    expect(flow.concept_cards[0].id).toBe("concept_ruleforge_tactics");
  });

  it("returns a game profile bundle with its claims", async () => {
    const bundle = await getGameProfile("game_balatro");
    expect(bundle?.game.title).toBe("Balatro");
    expect(bundle?.profile?.game_id).toBe("game_balatro");
    expect(bundle?.claims.some((c) => c.subject === "Balatro")).toBe(true);
  });

  it("derives graph nodes and edges from relations", async () => {
    const { nodes, edges } = await getGraph();
    expect(edges).toHaveLength(4);
    // Every edge endpoint must exist as a node.
    const nodeIds = new Set(nodes.map((n) => n.id));
    for (const edge of edges) {
      expect(nodeIds.has(edge.source)).toBe(true);
      expect(nodeIds.has(edge.target)).toBe(true);
    }
  });
});
```

- [ ] **Step 3: Run the test to verify it fails**

Run from `frontend/`:

```powershell
npm test -- lib/data/data.test.ts
```

Expected: FAIL with import error for `@/lib/data`.

- [ ] **Step 4: Implement the data layer**

Create `frontend/lib/data/index.ts`:

```ts
import { goldenFlow } from "@/lib/fixtures/golden-flow";
import type {
  ConceptCard,
  ConceptEvaluation,
  DeveloperProfile,
  DesignClaim,
  GameDesignProfile,
  GoldenFlow,
  OpportunityFrame,
  PrototypeBrief,
  SeedGame,
} from "@/lib/types";

// Simulate a network round-trip so loading/error states are real.
// Swap these bodies for `fetch(...)` when the backend API lands; signatures stay.
const LATENCY_MS = 120;

function settle<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), LATENCY_MS));
}

export async function getGoldenFlow(): Promise<GoldenFlow> {
  return settle(goldenFlow);
}

export async function getSeedGames(): Promise<SeedGame[]> {
  return settle(goldenFlow.seed_games);
}

export interface GameProfileBundle {
  game: SeedGame;
  profile: GameDesignProfile | null;
  claims: DesignClaim[];
}

export async function getGameProfile(id: string): Promise<GameProfileBundle | null> {
  const game = goldenFlow.seed_games.find((g) => g.id === id);
  if (!game) return settle(null);
  const profile = goldenFlow.game_design_profiles.find((p) => p.game_id === id) ?? null;
  const claims = goldenFlow.design_claims.filter((c) => c.subject === game.title);
  return settle({ game, profile, claims });
}

export interface GraphNode {
  id: string;
  label: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  confidence: GoldenFlow["graph_relations"][number]["confidence"];
  quality_status: GoldenFlow["graph_relations"][number]["quality_status"];
  claim_id: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export async function getGraph(): Promise<GraphData> {
  const nodeMap = new Map<string, GraphNode>();
  const edges: GraphEdge[] = [];
  for (const rel of goldenFlow.graph_relations) {
    for (const label of [rel.source_node, rel.target_node]) {
      if (!nodeMap.has(label)) nodeMap.set(label, { id: label, label });
    }
    edges.push({
      id: rel.id,
      source: rel.source_node,
      target: rel.target_node,
      relation: rel.relation,
      confidence: rel.confidence,
      quality_status: rel.quality_status,
      claim_id: rel.claim_id,
    });
  }
  return settle({ nodes: [...nodeMap.values()], edges });
}

export async function getDeveloperProfile(): Promise<DeveloperProfile> {
  return settle(goldenFlow.developer_profile);
}

export async function getOpportunityFrame(): Promise<OpportunityFrame> {
  return settle(goldenFlow.opportunity_frame);
}

export interface ConceptsBundle {
  cards: ConceptCard[];
  evaluations: ConceptEvaluation[];
}

export async function getConcepts(): Promise<ConceptsBundle> {
  return settle({
    cards: goldenFlow.concept_cards,
    evaluations: goldenFlow.concept_evaluations,
  });
}

export async function getPrototypeBrief(): Promise<PrototypeBrief> {
  return settle(goldenFlow.prototype_brief);
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run from `frontend/`:

```powershell
npm test -- lib/data/data.test.ts
```

Expected: `3 passed`.

- [ ] **Step 6: Implement the query hooks**

Create `frontend/lib/queries/index.ts`:

```ts
"use client";

import { useQuery } from "@tanstack/react-query";
import {
  getConcepts,
  getDeveloperProfile,
  getGameProfile,
  getGoldenFlow,
  getGraph,
  getOpportunityFrame,
  getPrototypeBrief,
  getSeedGames,
} from "@/lib/data";

export function useGoldenFlow() {
  return useQuery({ queryKey: ["golden-flow"], queryFn: getGoldenFlow });
}

export function useSeedGames() {
  return useQuery({ queryKey: ["seed-games"], queryFn: getSeedGames });
}

export function useGameProfile(id: string) {
  return useQuery({
    queryKey: ["game-profile", id],
    queryFn: () => getGameProfile(id),
  });
}

export function useGraph() {
  return useQuery({ queryKey: ["graph"], queryFn: getGraph });
}

export function useDeveloperProfile() {
  return useQuery({ queryKey: ["developer-profile"], queryFn: getDeveloperProfile });
}

export function useOpportunityFrame() {
  return useQuery({ queryKey: ["opportunity-frame"], queryFn: getOpportunityFrame });
}

export function useConcepts() {
  return useQuery({ queryKey: ["concepts"], queryFn: getConcepts });
}

export function usePrototypeBrief() {
  return useQuery({ queryKey: ["prototype-brief"], queryFn: getPrototypeBrief });
}
```

- [ ] **Step 7: Create the Providers client component**

Create `frontend/app/providers.tsx`:

```tsx
"use client";

import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 60_000, retry: 1 } },
      }),
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
```

- [ ] **Step 8: Mount Providers in the root layout**

Replace the body of `frontend/app/layout.tsx` so the children are wrapped in `Providers`. Keep the generated font and metadata code; only change the `<body>` content. The result should look like:

```tsx
import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "GameGraph Workbench",
  description: "Indie game idea graph workbench",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

> If the generated `layout.tsx` imports `next/font` and applies font className variables, keep those imports and merge their classNames onto `<body>` instead of replacing them. The only required change is wrapping `{children}` with `<Providers>`.

- [ ] **Step 9: Run the full suite**

Run from `frontend/`:

```powershell
npm test
```

Expected: all tests pass (structure, types, data).

- [ ] **Step 10: Commit**

```powershell
git add frontend/lib/fixtures frontend/lib/data frontend/lib/queries frontend/app/providers.tsx frontend/app/layout.tsx
git commit -m "Add fixture, data layer, query hooks, and providers"
```

---

### Task 5: Workbench Shell And Navigation

**Files:**
- Create: `frontend/lib/nav.ts`
- Create: `frontend/components/shell/app-sidebar.tsx`
- Create: `frontend/components/shell/top-bar.tsx`
- Create: `frontend/components/shell/task-progress.tsx`
- Create: `frontend/components/shell/app-sidebar.test.tsx`
- Create: `frontend/app/(workbench)/layout.tsx`
- Create: `frontend/app/page.tsx` (replace generated home)

- [ ] **Step 1: Create the navigation config**

Create `frontend/lib/nav.ts`:

```ts
export interface NavItem {
  href: string;
  label: string;
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    title: "资料库",
    items: [
      { href: "/games", label: "游戏入库" },
      { href: "/graph", label: "知识图谱" },
    ],
  },
  {
    title: "创意流程",
    items: [
      { href: "/profile", label: "开发者画像" },
      { href: "/opportunities", label: "机会框架" },
      { href: "/concepts", label: "概念卡" },
      { href: "/prototype", label: "原型简报" },
    ],
  },
];

export const OVERVIEW_ITEM: NavItem = { href: "/overview", label: "总览" };
```

> Note: the game design profile lives at `/games/[id]` and is reached from the `/games` list, so it is intentionally not a top-level nav item.

- [ ] **Step 2: Write a failing test for the sidebar**

Create `frontend/components/shell/app-sidebar.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppSidebar } from "@/components/shell/app-sidebar";

describe("AppSidebar", () => {
  it("renders both nav groups and their items", () => {
    render(<AppSidebar />);
    expect(screen.getByText("资料库")).toBeInTheDocument();
    expect(screen.getByText("创意流程")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "机会框架" })).toHaveAttribute(
      "href",
      "/opportunities",
    );
    expect(screen.getByRole("link", { name: "总览" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run the test to verify it fails**

Run from `frontend/`:

```powershell
npm test -- components/shell/app-sidebar.test.tsx
```

Expected: FAIL with import error for `@/components/shell/app-sidebar`.

- [ ] **Step 4: Implement the sidebar**

Create `frontend/components/shell/app-sidebar.tsx`:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_GROUPS, OVERVIEW_ITEM } from "@/lib/nav";
import { cn } from "@/lib/utils";

function NavLink({ href, label }: { href: string; label: string }) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(`${href}/`);
  return (
    <Link
      href={href}
      className={cn(
        "block rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground",
        active && "bg-accent font-medium text-accent-foreground",
      )}
    >
      {label}
    </Link>
  );
}

export function AppSidebar() {
  return (
    <aside className="flex w-56 flex-col gap-4 border-r bg-background p-3">
      <div className="flex items-center gap-2 px-2 py-1 font-semibold">
        <span className="inline-block h-4 w-4 rounded bg-primary" />
        GameGraph
      </div>
      {NAV_GROUPS.map((group) => (
        <div key={group.title}>
          <div className="px-3 pb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
            {group.title}
          </div>
          {group.items.map((item) => (
            <NavLink key={item.href} {...item} />
          ))}
        </div>
      ))}
      <div className="mt-auto border-t pt-2">
        <NavLink {...OVERVIEW_ITEM} />
      </div>
    </aside>
  );
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run from `frontend/`:

```powershell
npm test -- components/shell/app-sidebar.test.tsx
```

Expected: `1 passed`.

- [ ] **Step 6: Implement the task progress chip**

Create `frontend/components/shell/task-progress.tsx`:

```tsx
"use client";

// Placeholder for long-task progress. A real SSE/polling source replaces the
// static value later; the component contract stays the same.
export function TaskProgress() {
  return (
    <span className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-green-200 bg-green-50 px-2.5 py-1 text-xs text-green-700">
      <span aria-hidden>●</span>
      图谱构建 完成
    </span>
  );
}
```

- [ ] **Step 7: Implement the top bar**

Create `frontend/components/shell/top-bar.tsx`:

```tsx
import { TaskProgress } from "@/components/shell/task-progress";

export function TopBar({ title }: { title: string }) {
  return (
    <header className="flex h-12 items-center gap-3 border-b bg-background px-4">
      <span className="text-sm font-medium">{title}</span>
      <TaskProgress />
    </header>
  );
}
```

- [ ] **Step 8: Implement the workbench layout**

Create `frontend/app/(workbench)/layout.tsx`:

```tsx
import type { ReactNode } from "react";
import { AppSidebar } from "@/components/shell/app-sidebar";
import { TopBar } from "@/components/shell/top-bar";

export default function WorkbenchLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <AppSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar title="GameGraph 工作台" />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 9: Redirect the home route to the overview**

Replace `frontend/app/page.tsx` with:

```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/overview");
}
```

- [ ] **Step 10: Run the suite**

Run from `frontend/`:

```powershell
npm test
```

Expected: all tests pass.

- [ ] **Step 11: Commit**

```powershell
git add frontend/lib/nav.ts frontend/components/shell "frontend/app/(workbench)/layout.tsx" frontend/app/page.tsx
git commit -m "Add workbench shell and navigation"
```

---
### Task 6: Reusable Artifact Components

**Files:**
- Create: `frontend/components/artifacts/confidence-badge.tsx`
- Create: `frontend/components/artifacts/quality-badge.tsx`
- Create: `frontend/components/artifacts/evidence-list.tsx`
- Create: `frontend/components/artifacts/claim-row.tsx`
- Create: `frontend/components/artifacts/constraint-tag.tsx`
- Create: `frontend/components/artifacts/artifacts.test.tsx`

- [ ] **Step 1: Write failing tests for the artifact components**

Create `frontend/components/artifacts/artifacts.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceBadge } from "@/components/artifacts/confidence-badge";
import { QualityBadge } from "@/components/artifacts/quality-badge";
import { ClaimRow } from "@/components/artifacts/claim-row";
import { ConstraintTag } from "@/components/artifacts/constraint-tag";
import type { DesignClaim } from "@/lib/types";

const lowClaim: DesignClaim = {
  id: "claim_low",
  subject: "symbolic tactical UI",
  relation: "may_reduce",
  object: "animation burden",
  explanation: "Abstract feedback can reduce art load.",
  evidence: [
    {
      title: "Curator hypothesis",
      quote_or_summary: "Expected to be cheaper than animation-heavy combat.",
      notes: "Weak evidence.",
    },
  ],
  confidence: "low",
  quality_status: "weak_evidence",
};

describe("artifact components", () => {
  it("labels confidence level", () => {
    render(<ConfidenceBadge level="high" />);
    expect(screen.getByText(/置信度 高/)).toBeInTheDocument();
  });

  it("flags weak evidence as a downgraded quality status", () => {
    const { container } = render(<QualityBadge status="weak_evidence" />);
    expect(screen.getByText("弱证据")).toBeInTheDocument();
    // Downgraded statuses carry the data attribute the styling keys off of.
    expect(container.querySelector('[data-downgraded="true"]')).not.toBeNull();
  });

  it("does not downgrade a reviewed status", () => {
    const { container } = render(<QualityBadge status="reviewed" />);
    expect(container.querySelector('[data-downgraded="true"]')).toBeNull();
  });

  it("renders a low-confidence claim with both downgrade signals", () => {
    render(<ClaimRow claim={lowClaim} />);
    expect(screen.getByText(/置信度 低/)).toBeInTheDocument();
    expect(screen.getByText("弱证据")).toBeInTheDocument();
    expect(screen.getByText(/Curator hypothesis/)).toBeInTheDocument();
  });

  it("marks a hard constraint", () => {
    const { container } = render(
      <ConstraintTag
        constraint={{ id: "c1", type: "hard", statement: "No online." }}
      />,
    );
    expect(screen.getByText("No online.")).toBeInTheDocument();
    expect(container.querySelector('[data-constraint="hard"]')).not.toBeNull();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run from `frontend/`:

```powershell
npm test -- components/artifacts/artifacts.test.tsx
```

Expected: FAIL with import errors for the artifact components.

- [ ] **Step 3: Implement ConfidenceBadge**

Create `frontend/components/artifacts/confidence-badge.tsx`:

```tsx
import type { ConfidenceLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

const LABEL: Record<ConfidenceLevel, string> = {
  high: "置信度 高",
  medium: "置信度 中",
  low: "置信度 低",
};

const STYLE: Record<ConfidenceLevel, string> = {
  high: "bg-green-100 text-green-700",
  medium: "bg-zinc-100 text-zinc-700",
  low: "bg-amber-100 text-amber-700",
};

export function ConfidenceBadge({ level }: { level: ConfidenceLevel }) {
  return (
    <span
      data-confidence={level}
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-xs font-semibold",
        STYLE[level],
      )}
    >
      {LABEL[level]}
    </span>
  );
}
```

- [ ] **Step 4: Implement QualityBadge**

Create `frontend/components/artifacts/quality-badge.tsx`:

```tsx
import type { QualityStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const LABEL: Record<QualityStatus, string> = {
  draft: "草稿",
  reviewed: "已评审",
  weak_evidence: "弱证据",
  conflicting: "证据冲突",
};

// weak_evidence and conflicting must be visibly downgraded.
const DOWNGRADED: Record<QualityStatus, boolean> = {
  draft: false,
  reviewed: false,
  weak_evidence: true,
  conflicting: true,
};

export function QualityBadge({ status }: { status: QualityStatus }) {
  const downgraded = DOWNGRADED[status];
  return (
    <span
      data-quality={status}
      data-downgraded={downgraded ? "true" : undefined}
      className={cn(
        "inline-flex rounded-full border px-2 py-0.5 text-xs",
        downgraded
          ? "border-amber-200 bg-amber-50 text-amber-700"
          : "border-zinc-200 bg-zinc-50 text-zinc-600",
      )}
    >
      {LABEL[status]}
    </span>
  );
}
```

- [ ] **Step 5: Implement EvidenceList**

Create `frontend/components/artifacts/evidence-list.tsx`:

```tsx
import type { EvidenceRef } from "@/lib/types";

export function EvidenceList({ evidence }: { evidence: EvidenceRef[] }) {
  if (evidence.length === 0) {
    return <p className="text-xs text-muted-foreground">无证据记录</p>;
  }
  return (
    <ul className="space-y-1 text-xs text-muted-foreground">
      {evidence.map((ref, i) => (
        <li key={`${ref.title}-${i}`}>
          <span className="font-medium text-foreground/80">{ref.title}</span>
          {ref.url ? (
            <>
              {" — "}
              <a href={ref.url} className="underline" target="_blank" rel="noreferrer">
                {ref.url}
              </a>
            </>
          ) : ref.quote_or_summary ? (
            <>{" — “"}{ref.quote_or_summary}{"”"}</>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 6: Implement ClaimRow**

Create `frontend/components/artifacts/claim-row.tsx`:

```tsx
import type { DesignClaim } from "@/lib/types";
import { ConfidenceBadge } from "@/components/artifacts/confidence-badge";
import { QualityBadge } from "@/components/artifacts/quality-badge";
import { EvidenceList } from "@/components/artifacts/evidence-list";
import { cn } from "@/lib/utils";

export function ClaimRow({ claim }: { claim: DesignClaim }) {
  const downgraded =
    claim.confidence === "low" ||
    claim.quality_status === "weak_evidence" ||
    claim.quality_status === "conflicting";
  return (
    <div
      className={cn(
        "rounded-lg border p-3",
        downgraded ? "border-amber-200" : "border-border",
      )}
    >
      <div className="mb-2 flex items-center gap-2">
        <span className="font-medium">
          {claim.subject} · {claim.relation} · {claim.object}
        </span>
        <span className="ml-auto flex items-center gap-2">
          <ConfidenceBadge level={claim.confidence} />
          <QualityBadge status={claim.quality_status} />
        </span>
      </div>
      <p className="mb-2 text-sm text-muted-foreground">{claim.explanation}</p>
      <EvidenceList evidence={claim.evidence} />
    </div>
  );
}
```

- [ ] **Step 7: Implement ConstraintTag**

Create `frontend/components/artifacts/constraint-tag.tsx`:

```tsx
import type { DeveloperConstraint, ConstraintType } from "@/lib/types";
import { cn } from "@/lib/utils";

const LABEL: Record<ConstraintType, string> = {
  hard: "硬性约束",
  strong_preference: "强偏好",
  soft_preference: "软偏好",
};

const STYLE: Record<ConstraintType, string> = {
  hard: "border-red-200 bg-red-50 text-red-700",
  strong_preference: "border-amber-200 bg-amber-50 text-amber-700",
  soft_preference: "border-zinc-200 bg-zinc-50 text-zinc-600",
};

export function ConstraintTag({ constraint }: { constraint: DeveloperConstraint }) {
  return (
    <div
      data-constraint={constraint.type}
      className={cn("rounded-md border px-3 py-2 text-sm", STYLE[constraint.type])}
    >
      <span className="mr-2 text-xs font-semibold">{LABEL[constraint.type]}</span>
      {constraint.statement}
    </div>
  );
}
```

- [ ] **Step 8: Run the tests to verify they pass**

Run from `frontend/`:

```powershell
npm test -- components/artifacts/artifacts.test.tsx
```

Expected: `5 passed`.

- [ ] **Step 9: Commit**

```powershell
git add frontend/components/artifacts
git commit -m "Add reusable artifact components"
```

---

### Task 7: Shared View Helpers, Overview, Games List, And Game Profile

**Files:**
- Create: `frontend/components/shell/view-states.tsx`
- Create: `frontend/app/(workbench)/overview/page.tsx`
- Create: `frontend/app/(workbench)/games/page.tsx`
- Create: `frontend/app/(workbench)/games/games-page.test.tsx`
- Create: `frontend/app/(workbench)/games/[id]/page.tsx`

- [ ] **Step 1: Create shared loading/error/empty helpers**

Create `frontend/components/shell/view-states.tsx`:

```tsx
"use client";

import { Skeleton } from "@/components/ui/skeleton";

export function LoadingState() {
  return (
    <div className="space-y-3" role="status" aria-label="加载中">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}

export function ErrorState({ onRetry }: { onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      <p className="mb-2 font-medium">加载失败</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md border border-red-300 px-3 py-1 text-red-700 hover:bg-red-100"
        >
          重试
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
      {message}
    </div>
  );
}

export function PageHeader({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="mb-5">
      <h1 className="text-xl font-semibold">{title}</h1>
      {description ? (
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 2: Implement the overview page**

Create `frontend/app/(workbench)/overview/page.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useGoldenFlow } from "@/lib/queries";
import { ErrorState, LoadingState, PageHeader } from "@/components/shell/view-states";

const STAGES: { label: string; href: string; count: (f: ReturnType<typeof useGoldenFlow>["data"]) => number }[] =
  [
    { label: "种子游戏", href: "/games", count: (f) => f?.seed_games.length ?? 0 },
    { label: "设计论断", href: "/games", count: (f) => f?.design_claims.length ?? 0 },
    { label: "图谱关系", href: "/graph", count: (f) => f?.graph_relations.length ?? 0 },
    { label: "机会框架", href: "/opportunities", count: (f) => (f?.opportunity_frame ? 1 : 0) },
    { label: "概念卡", href: "/concepts", count: (f) => f?.concept_cards.length ?? 0 },
    { label: "原型简报", href: "/prototype", count: (f) => (f?.prototype_brief ? 1 : 0) },
  ];

export default function OverviewPage() {
  const { data, isLoading, isError, refetch } = useGoldenFlow();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div>
      <PageHeader
        title="总览"
        description="核心流程:种子游戏 → 设计论断 → 图谱 → 开发者画像 → 机会框架 → 概念卡 → 原型简报"
      />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {STAGES.map((stage) => (
          <Link
            key={stage.label}
            href={stage.href}
            className="rounded-lg border p-4 hover:bg-accent"
          >
            <div className="text-2xl font-semibold">{stage.count(data)}</div>
            <div className="text-sm text-muted-foreground">{stage.label}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Write a failing test for the games list**

Create `frontend/app/(workbench)/games/games-page.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import GamesPage from "@/app/(workbench)/games/page";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("GamesPage", () => {
  it("lists seed games once loaded", async () => {
    renderWithClient(<GamesPage />);
    await waitFor(() => {
      expect(screen.getByText("Balatro")).toBeInTheDocument();
    });
    expect(screen.getByText("Into the Breach")).toBeInTheDocument();
    expect(screen.getByText("Baba Is You")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run the test to verify it fails**

Run from `frontend/`:

```powershell
npm test -- "app/(workbench)/games/games-page.test.tsx"
```

Expected: FAIL with import error for the games page.

- [ ] **Step 5: Implement the games list page**

Create `frontend/app/(workbench)/games/page.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useSeedGames } from "@/lib/queries";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function GamesPage() {
  const { data, isLoading, isError, refetch } = useSeedGames();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;
  if (data.length === 0) return <EmptyState message="种子库暂无游戏" />;

  return (
    <div>
      <PageHeader title="游戏入库" description="按设计相关性精选的种子游戏" />
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>标题</TableHead>
            <TableHead>简述</TableHead>
            <TableHead>选择理由</TableHead>
            <TableHead className="text-right">来源</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((game) => (
            <TableRow key={game.id}>
              <TableCell className="font-medium">
                <Link href={`/games/${game.id}`} className="hover:underline">
                  {game.title}
                </Link>
              </TableCell>
              <TableCell className="text-muted-foreground">
                {game.short_description}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {game.selection_reason}
              </TableCell>
              <TableCell className="text-right">{game.source_refs.length}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

- [ ] **Step 6: Run the test to verify it passes**

Run from `frontend/`:

```powershell
npm test -- "app/(workbench)/games/games-page.test.tsx"
```

Expected: `1 passed`.

- [ ] **Step 7: Implement the game design profile page**

Create `frontend/app/(workbench)/games/[id]/page.tsx`:

```tsx
"use client";

import { use } from "react";
import { useGameProfile } from "@/lib/queries";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";
import { ClaimRow } from "@/components/artifacts/claim-row";
import { ConfidenceBadge } from "@/components/artifacts/confidence-badge";
import { QualityBadge } from "@/components/artifacts/quality-badge";

export default function GameProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data, isLoading, isError, refetch } = useGameProfile(id);

  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState onRetry={() => refetch()} />;
  if (!data) return <EmptyState message="未找到该游戏" />;

  const { game, profile, claims } = data;

  return (
    <div className="space-y-6">
      <div>
        <PageHeader title={game.title} description={game.short_description} />
        {profile ? (
          <div className="flex flex-wrap items-center gap-2">
            {profile.reference_value_tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground"
              >
                {tag}
              </span>
            ))}
            <span className="ml-2 flex items-center gap-2">
              <ConfidenceBadge level={profile.confidence} />
              <QualityBadge status={profile.quality_status} />
            </span>
          </div>
        ) : null}
      </div>

      {profile ? (
        <section className="rounded-lg border p-4">
          <p className="mb-3 text-sm">{profile.one_sentence_summary}</p>
          <dl className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
            <div>
              <dt className="text-muted-foreground">核心循环</dt>
              <dd>{profile.core_loop}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">主要机制</dt>
              <dd>{profile.main_mechanics.join("、")}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">主要体验</dt>
              <dd>{profile.main_experiences.join("、")}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">不可复制风险</dt>
              <dd>{profile.hard_to_copy_risks.join("、")}</dd>
            </div>
          </dl>
        </section>
      ) : (
        <EmptyState message="该游戏暂无设计档案" />
      )}

      <section>
        <h2 className="mb-3 text-xs uppercase tracking-wide text-muted-foreground/70">
          设计论断
        </h2>
        {claims.length === 0 ? (
          <EmptyState message="暂无设计论断" />
        ) : (
          <div className="space-y-3">
            {claims.map((claim) => (
              <ClaimRow key={claim.id} claim={claim} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 8: Run the suite**

Run from `frontend/`:

```powershell
npm test
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```powershell
git add frontend/components/shell/view-states.tsx "frontend/app/(workbench)/overview" "frontend/app/(workbench)/games"
git commit -m "Add overview, games list, and game profile views"
```

---
### Task 8: Knowledge Graph View (React Flow)

**Files:**
- Modify: `frontend/vitest.setup.ts` (add ResizeObserver polyfill for React Flow)
- Create: `frontend/components/graph/graph-canvas.tsx`
- Create: `frontend/app/(workbench)/graph/page.tsx`
- Create: `frontend/app/(workbench)/graph/graph-page.test.tsx`

- [ ] **Step 1: Add a ResizeObserver polyfill to the test setup**

React Flow needs `ResizeObserver`, which jsdom lacks. Replace `frontend/vitest.setup.ts` with:

```ts
import "@testing-library/jest-dom/vitest";

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// React Flow measures its container with ResizeObserver; jsdom has none.
globalThis.ResizeObserver = globalThis.ResizeObserver ?? (ResizeObserverStub as unknown as typeof ResizeObserver);
```

- [ ] **Step 2: Implement the graph canvas**

Create `frontend/components/graph/graph-canvas.tsx`:

```tsx
"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { GraphData, GraphEdge } from "@/lib/data";

const EDGE_COLOR: Record<GraphEdge["confidence"], string> = {
  high: "#16a34a",
  medium: "#71717a",
  low: "#d97706",
};

export function GraphCanvas({
  graph,
  onSelectEdge,
}: {
  graph: GraphData;
  onSelectEdge?: (edgeId: string) => void;
}) {
  const nodes = useMemo<Node[]>(
    () =>
      graph.nodes.map((node, index) => ({
        id: node.id,
        position: { x: (index % 2) * 320, y: index * 90 },
        data: { label: node.label },
        style: { fontSize: 12, width: 220 },
      })),
    [graph.nodes],
  );

  const edges = useMemo<Edge[]>(
    () =>
      graph.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.relation,
        animated: edge.confidence === "low",
        style: {
          stroke: EDGE_COLOR[edge.confidence],
          strokeDasharray: edge.confidence === "low" ? "5 5" : undefined,
        },
      })),
    [graph.edges],
  );

  return (
    <div className="h-[520px] rounded-lg border">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        onEdgeClick={(_, edge) => onSelectEdge?.(edge.id)}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
```

- [ ] **Step 3: Write a failing test for the graph page side panel**

Create `frontend/app/(workbench)/graph/graph-page.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import GraphPage from "@/app/(workbench)/graph/page";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("GraphPage", () => {
  it("lists relations with a downgraded low-confidence edge", async () => {
    renderWithClient(<GraphPage />);
    await waitFor(() => {
      expect(screen.getByText(/symbolic tactical UI/)).toBeInTheDocument();
    });
    // The weak-evidence relation is rendered with its downgraded quality badge.
    expect(screen.getAllByText("弱证据").length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 4: Run the test to verify it fails**

Run from `frontend/`:

```powershell
npm test -- "app/(workbench)/graph/graph-page.test.tsx"
```

Expected: FAIL with import error for the graph page.

- [ ] **Step 5: Implement the graph page**

Create `frontend/app/(workbench)/graph/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useGraph } from "@/lib/queries";
import { GraphCanvas } from "@/components/graph/graph-canvas";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";
import { ConfidenceBadge } from "@/components/artifacts/confidence-badge";
import { QualityBadge } from "@/components/artifacts/quality-badge";
import { cn } from "@/lib/utils";

export default function GraphPage() {
  const { data, isLoading, isError, refetch } = useGraph();
  const [selected, setSelected] = useState<string | null>(null);

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;
  if (data.edges.length === 0) return <EmptyState message="图谱暂无关系" />;

  return (
    <div>
      <PageHeader
        title="知识图谱"
        description="由设计论断派生的可查询关系;低置信度关系以琥珀色虚线降级展示。"
      />
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <GraphCanvas graph={data} onSelectEdge={setSelected} />
        <aside className="space-y-2">
          <h2 className="text-xs uppercase tracking-wide text-muted-foreground/70">
            关系列表
          </h2>
          {data.edges.map((edge) => (
            <button
              key={edge.id}
              type="button"
              onClick={() => setSelected(edge.id)}
              className={cn(
                "w-full rounded-lg border p-3 text-left text-sm hover:bg-accent",
                selected === edge.id && "ring-2 ring-primary",
                (edge.confidence === "low" ||
                  edge.quality_status === "weak_evidence") &&
                  "border-amber-200",
              )}
            >
              <div className="mb-1 font-medium">
                {edge.source} · {edge.relation} · {edge.target}
              </div>
              <div className="flex items-center gap-2">
                <ConfidenceBadge level={edge.confidence} />
                <QualityBadge status={edge.quality_status} />
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                来源论断:{edge.claim_id}
              </div>
            </button>
          ))}
        </aside>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Run the test to verify it passes**

Run from `frontend/`:

```powershell
npm test -- "app/(workbench)/graph/graph-page.test.tsx"
```

Expected: `1 passed`.

- [ ] **Step 7: Commit**

```powershell
git add frontend/vitest.setup.ts frontend/components/graph "frontend/app/(workbench)/graph"
git commit -m "Add knowledge graph view with React Flow"
```

---

### Task 9: Developer Profile And Opportunity Frame Views

**Files:**
- Create: `frontend/app/(workbench)/profile/page.tsx`
- Create: `frontend/app/(workbench)/opportunities/page.tsx`
- Create: `frontend/app/(workbench)/opportunities/opportunities-page.test.tsx`

- [ ] **Step 1: Implement the developer profile page**

Create `frontend/app/(workbench)/profile/page.tsx`:

```tsx
"use client";

import { useDeveloperProfile } from "@/lib/queries";
import {
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";
import { ConstraintTag } from "@/components/artifacts/constraint-tag";

export default function ProfilePage() {
  const { data, isLoading, isError, refetch } = useDeveloperProfile();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;

  const fields: [string, string][] = [
    ["团队规模", data.team_size],
    ["时间预算", data.time_budget],
    ["程序能力", data.programming_ability],
    ["美术能力", data.art_ability],
    ["音频能力", data.audio_ability],
    ["内容生产能力", data.content_production_ability],
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="开发者画像" description="能力、约束与偏好" />

      <section className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {fields.map(([label, value]) => (
          <div key={label} className="rounded-lg border p-3">
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className="text-sm font-medium">{value}</div>
          </div>
        ))}
      </section>

      <section>
        <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
          约束与偏好
        </h2>
        <div className="space-y-2">
          {data.constraints.map((constraint) => (
            <ConstraintTag key={constraint.id} constraint={constraint} />
          ))}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div>
          <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
            喜欢的参考
          </h2>
          <p className="text-sm">{data.liked_references.join("、")}</p>
        </div>
        <div>
          <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
            讨厌的参考或机制
          </h2>
          <p className="text-sm">{data.disliked_references_or_mechanics.join("、")}</p>
        </div>
        <div className="md:col-span-2">
          <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
            期望的玩家体验
          </h2>
          <p className="text-sm">{data.desired_player_experiences.join("、")}</p>
        </div>
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Write a failing test for the opportunity frame page**

Create `frontend/app/(workbench)/opportunities/opportunities-page.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import OpportunitiesPage from "@/app/(workbench)/opportunities/page";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("OpportunitiesPage", () => {
  it("shows the opportunity area and forbidden directions", async () => {
    renderWithClient(<OpportunitiesPage />);
    await waitFor(() => {
      expect(
        screen.getByText(/Low-art, short-run tactical rule manipulation/),
      ).toBeInTheDocument();
    });
    // Forbidden directions must be visible.
    expect(screen.getByText("禁止方向")).toBeInTheDocument();
    expect(screen.getByText("online multiplayer")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run the test to verify it fails**

Run from `frontend/`:

```powershell
npm test -- "app/(workbench)/opportunities/opportunities-page.test.tsx"
```

Expected: FAIL with import error for the opportunities page.

- [ ] **Step 4: Implement the opportunity frame page**

Create `frontend/app/(workbench)/opportunities/page.tsx`:

```tsx
"use client";

import { useOpportunityFrame } from "@/lib/queries";
import {
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";

function Chips({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span
          key={item}
          className="rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

export default function OpportunitiesPage() {
  const { data, isLoading, isError, refetch } = useOpportunityFrame();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div className="space-y-6">
      <PageHeader title="机会框架" description={data.opportunity_area} />

      <section className="grid gap-4 md:grid-cols-2">
        <div>
          <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
            相关机制
          </h2>
          <Chips items={data.related_mechanics} />
        </div>
        <div>
          <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
            相关玩家体验
          </h2>
          <Chips items={data.related_player_experiences} />
        </div>
        <div>
          <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
            推荐变形
          </h2>
          <ul className="list-disc pl-5 text-sm">
            {data.recommended_transformations.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50 p-3">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-red-700">
            禁止方向
          </h2>
          <ul className="list-disc pl-5 text-sm text-red-700">
            {data.forbidden_directions.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div>
          <h2 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
            适配理由
          </h2>
          <p className="text-sm text-muted-foreground">{data.fit_reason}</p>
        </div>
        <div>
          <h2 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
            风险理由
          </h2>
          <p className="text-sm text-muted-foreground">{data.risk_reason}</p>
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/70">
          证据路径
        </h2>
        <Chips items={data.evidence_path} />
      </section>
    </div>
  );
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run from `frontend/`:

```powershell
npm test -- "app/(workbench)/opportunities/opportunities-page.test.tsx"
```

Expected: `1 passed`.

- [ ] **Step 6: Commit**

```powershell
git add "frontend/app/(workbench)/profile" "frontend/app/(workbench)/opportunities"
git commit -m "Add developer profile and opportunity frame views"
```

---
### Task 10: Concept Comparison And Prototype Brief Views

**Files:**
- Create: `frontend/app/(workbench)/concepts/page.tsx`
- Create: `frontend/app/(workbench)/concepts/concepts-page.test.tsx`
- Create: `frontend/app/(workbench)/prototype/page.tsx`
- Create: `frontend/app/(workbench)/prototype/prototype-page.test.tsx`

- [ ] **Step 1: Write a failing test for the concepts page**

Create `frontend/app/(workbench)/concepts/concepts-page.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ConceptsPage from "@/app/(workbench)/concepts/page";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("ConceptsPage", () => {
  it("shows the concept with its difference, risks, and evaluation category", async () => {
    renderWithClient(<ConceptsPage />);
    await waitFor(() => {
      expect(screen.getByText("Ruleforge Tactics")).toBeInTheDocument();
    });
    expect(screen.getByText(/与参考作品的差异/)).toBeInTheDocument();
    expect(screen.getByText(/制作风险/)).toBeInTheDocument();
    expect(screen.getByText(/设计风险/)).toBeInTheDocument();
    expect(screen.getByText("平衡型")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `frontend/`:

```powershell
npm test -- "app/(workbench)/concepts/concepts-page.test.tsx"
```

Expected: FAIL with import error for the concepts page.

- [ ] **Step 3: Implement the concepts page**

Create `frontend/app/(workbench)/concepts/page.tsx`:

```tsx
"use client";

import { useConcepts } from "@/lib/queries";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";
import type { EvaluationCategory } from "@/lib/types";
import { cn } from "@/lib/utils";

const CATEGORY_LABEL: Record<EvaluationCategory, string> = {
  safe: "稳妥型",
  balanced: "平衡型",
  challenging: "挑战型",
};

const CATEGORY_STYLE: Record<EvaluationCategory, string> = {
  safe: "border-zinc-200 bg-zinc-50 text-zinc-600",
  balanced: "border-blue-200 bg-blue-50 text-blue-700",
  challenging: "border-amber-200 bg-amber-50 text-amber-700",
};

export default function ConceptsPage() {
  const { data, isLoading, isError, refetch } = useConcepts();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;
  if (data.cards.length === 0) return <EmptyState message="暂无概念卡" />;

  return (
    <div>
      <PageHeader title="概念卡对比" description="由机会框架推导出的具体概念,附评估分类" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.cards.map((card) => {
          const evaluation = data.evaluations.find(
            (e) => e.concept_card_id === card.id,
          );
          return (
            <article key={card.id} className="flex flex-col rounded-lg border p-4">
              <div className="mb-2 flex items-start gap-2">
                <h2 className="font-semibold">{card.title}</h2>
                {evaluation ? (
                  <span
                    className={cn(
                      "ml-auto rounded-full border px-2 py-0.5 text-xs",
                      CATEGORY_STYLE[evaluation.category],
                    )}
                  >
                    {CATEGORY_LABEL[evaluation.category]}
                  </span>
                ) : null}
              </div>
              <p className="mb-3 text-sm text-muted-foreground">
                {card.one_sentence_concept}
              </p>

              <div className="mb-2">
                <div className="text-xs font-medium text-muted-foreground">
                  与参考作品的差异
                </div>
                <p className="text-sm">{card.difference_from_references}</p>
              </div>

              <div className="mb-2">
                <div className="text-xs font-medium text-muted-foreground">制作风险</div>
                <ul className="list-disc pl-5 text-sm">
                  {card.production_risks.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </div>

              <div>
                <div className="text-xs font-medium text-muted-foreground">设计风险</div>
                <ul className="list-disc pl-5 text-sm">
                  {card.design_risks.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </div>

              {evaluation ? (
                <dl className="mt-3 grid grid-cols-2 gap-2 border-t pt-3 text-xs">
                  <div>适配 {evaluation.fit_score}/5</div>
                  <div>可行 {evaluation.feasibility_score}/5</div>
                  <div>新颖 {evaluation.novelty_score}/5</div>
                  <div>风险 {evaluation.risk_score}/5</div>
                  <div className="col-span-2">
                    证据质量 {evaluation.evidence_quality_score}/5
                  </div>
                </dl>
              ) : null}
            </article>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `frontend/`:

```powershell
npm test -- "app/(workbench)/concepts/concepts-page.test.tsx"
```

Expected: `1 passed`.

- [ ] **Step 5: Write a failing test for the prototype brief page**

Create `frontend/app/(workbench)/prototype/prototype-page.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import PrototypePage from "@/app/(workbench)/prototype/page";

function renderWithClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("PrototypePage", () => {
  it("shows both success and failure signals", async () => {
    renderWithClient(<PrototypePage />);
    await waitFor(() => {
      expect(screen.getByText("成功信号")).toBeInTheDocument();
    });
    expect(screen.getByText("失败信号")).toBeInTheDocument();
    expect(
      screen.getByText(/player can explain a rule consequence/),
    ).toBeInTheDocument();
    expect(screen.getByText(/player says outcomes feel arbitrary/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Run the test to verify it fails**

Run from `frontend/`:

```powershell
npm test -- "app/(workbench)/prototype/prototype-page.test.tsx"
```

Expected: FAIL with import error for the prototype page.

- [ ] **Step 7: Implement the prototype brief page**

Create `frontend/app/(workbench)/prototype/page.tsx`:

```tsx
"use client";

import { usePrototypeBrief } from "@/lib/queries";
import {
  ErrorState,
  LoadingState,
  PageHeader,
} from "@/components/shell/view-states";

function SignalList({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "success" | "failure";
}) {
  const toneClass =
    tone === "success"
      ? "border-green-200 bg-green-50 text-green-800"
      : "border-red-200 bg-red-50 text-red-800";
  return (
    <div className={`rounded-lg border p-3 ${toneClass}`}>
      <h2 className="mb-2 text-sm font-semibold">{title}</h2>
      <ul className="list-disc pl-5 text-sm">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default function PrototypePage() {
  const { data, isLoading, isError, refetch } = usePrototypeBrief();

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div className="space-y-6">
      <PageHeader title="原型验证简报" description="把最大不确定性转化为最小可执行测试" />

      <section className="rounded-lg border p-4">
        <h2 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
          最大风险假设
        </h2>
        <p className="text-sm">{data.largest_risk_hypothesis}</p>
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border p-3">
          <h2 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
            最小原型范围
          </h2>
          <p className="text-sm">{data.minimum_prototype_scope}</p>
        </div>
        <div className="rounded-lg border p-3">
          <h2 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
            目标试玩时长
          </h2>
          <p className="text-sm">{data.target_playtest_duration}</p>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <SignalList title="成功信号" items={data.success_signals} tone="success" />
        <SignalList title="失败信号" items={data.failure_signals} tone="failure" />
      </section>

      <section className="rounded-lg border border-dashed p-3">
        <h2 className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/70">
          暂时不要做
        </h2>
        <p className="text-sm text-muted-foreground">
          {data.do_not_build_yet.join("、")}
        </p>
      </section>
    </div>
  );
}
```

- [ ] **Step 8: Run the test to verify it passes**

Run from `frontend/`:

```powershell
npm test -- "app/(workbench)/prototype/prototype-page.test.tsx"
```

Expected: `1 passed`.

- [ ] **Step 9: Commit**

```powershell
git add "frontend/app/(workbench)/concepts" "frontend/app/(workbench)/prototype"
git commit -m "Add concept comparison and prototype brief views"
```

---

### Task 11: Final Verification

**Files:**
- Verify: all files under `frontend/`

- [ ] **Step 1: Run the full test suite**

Run from `frontend/`:

```powershell
npm test
```

Expected: all test files pass (structure, types, data, artifacts, sidebar, games, graph, opportunities, concepts, prototype).

- [ ] **Step 2: Type-check the whole project**

Run from `frontend/`:

```powershell
npx tsc --noEmit
```

Expected: no type errors.

- [ ] **Step 3: Production build**

Run from `frontend/`:

```powershell
npm run build
```

Expected: build succeeds; the App Router routes `/overview`, `/games`, `/games/[id]`, `/graph`, `/profile`, `/opportunities`, `/concepts`, `/prototype` all compile.

- [ ] **Step 4: Manual smoke (optional, recommended)**

Run from `frontend/`:

```powershell
npm run dev
```

Open `http://localhost:3000`. Expected: redirects to `/overview`; sidebar navigates between all views; the graph renders nodes/edges; the low-confidence claim/relation shows amber downgrade treatment.

- [ ] **Step 5: Confirm worktree state**

Run from repo root:

```powershell
git status --short --branch
```

Expected: current branch shown with no uncommitted changes after the task commits.

---

## Self-Review Results

**Spec coverage:**

- §2 范围内 — `frontend/` scaffold (Task 1); Tailwind + shadcn (Tasks 1–2); workbench shell + sidebar/topbar (Task 5); seven read-only views + overview (Tasks 7–10); TS types mirroring backend (Task 3); typed fixture (Task 4); data layer + TanStack Query with loading/error/empty (Tasks 4, 7); Vitest downgrade-rule tests (Tasks 6, 8, 9, 10).
- §2 范围外 — no login/auth routes, no real API/SSE (data layer only simulates latency), no write forms, no Neo4j/LLM/SSR, no global state library, no Playwright, no scoring algorithm (evaluations are mock values). None of these appear in any task.
- §3 原则 — single data source in `lib/data` (Task 4 §3.2); no reasoning logic in frontend (views only display); evidence/confidence/quality components downgrade low-confidence material (Task 6, asserted in Tasks 6/8).
- §6–§7 数据模型/数据层 — types (Task 3), fixture + data functions + hooks (Task 4).
- §8 外壳 — nav config + sidebar + topbar + TaskProgress (Task 5).
- §9 视图 — overview (Task 7), games (Task 7), game profile (Task 7), graph (Task 8), profile (Task 9), opportunities (Task 9), concepts (Task 10), prototype (Task 10).
- §10 产物组件 — ConfidenceBadge, QualityBadge, EvidenceList, ClaimRow, ConstraintTag (Task 6). ArtifactCard from the spec is not separately created; shadcn `Card` plus per-view `border` containers cover the same need, so it is intentionally dropped (YAGNI).
- §11 状态处理 — LoadingState/ErrorState/EmptyState helpers (Task 7), TaskProgress (Task 5).
- §12 测试 — component + integration (mock data layer via QueryClient), downgrade assertions, page smoke; Playwright explicitly deferred.

**Placeholder scan:** No "TBD/TODO/handle edge cases" placeholders. Every code step contains complete file content. The only intentionally-static value is `TaskProgress` (documented as the SSE/polling stub per spec §11) and the data-layer `LATENCY_MS` simulation (documented as the `fetch` swap point per spec §3.2).

**Type consistency:**

- `GoldenFlow` shape in Task 3 includes `game_design_profiles` and `concept_evaluations`; the Task 4 fixture and data layer use exactly those keys.
- Data layer exports consumed by hooks match: `getGoldenFlow`, `getSeedGames`, `getGameProfile`, `getGraph`, `getDeveloperProfile`, `getOpportunityFrame`, `getConcepts`, `getPrototypeBrief` (Task 4 ⇄ hooks in Task 4 ⇄ pages in Tasks 7–10).
- `GraphData` / `GraphEdge` defined in Task 4 are imported by `GraphCanvas` and the graph page (Task 8).
- `EvaluationCategory` union (`safe`/`balanced`/`challenging`) defined in Task 3 keys the label/style maps in Task 10.
- Component prop names are stable: `ConfidenceBadge level=`, `QualityBadge status=`, `ClaimRow claim=`, `ConstraintTag constraint=` — used identically in tests and pages.




