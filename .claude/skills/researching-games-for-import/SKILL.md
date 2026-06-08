---
name: researching-games-for-import
description: Use when given one or more game names/titles and asked to produce importable GameImportDocument JSON for the GameGraph seed library (the manual 6.1/6.2 import pipeline).
---

# Researching Games For Import

## Overview

Turn a game name into an importable `GameImportDocument` JSON by researching the game online, then mapping findings into the schema with **honestly calibrated confidence**. One JSON file per game.

Core principle: the value is honest, sourced design analysis — not confident-sounding text. The main failure mode is over-claiming `confidence`/`quality_status`.

## When to use

- User gives one or more game titles and wants seed-library JSON ("搜索分析生成导入 json", "给这几个游戏生成导入文件").
- Multiple names → produce one file per game.

Not for: generating concept cards, or changing the schema itself.

## Authoritative contract (read these, don't reinvent)

- Schema: `backend/app/schemas/import_document.py`, `artifacts.py`, `common.py`
- Filled sample to copy from: `backend/app/fixtures/games/balatro.json`
- Field skeleton + enums + hard rules: `docs/superpowers/import-guide/game-import-prompt.md`

Document is `{ candidate, profile, claims }`. `profile.game_id` MUST equal `candidate.id`. `claims` is optional (0..n). All list fields in `profile` must be non-empty.

## Workflow (per game)

1. **Research.** Use WebSearch + WebFetch on the store page (Steam/itch), Wikipedia, and 1–2 design write-ups or reviews. Keep the real source URLs you actually opened.
2. **candidate** — title, `source_refs` (real URLs), one-line factual `short_description`, and `selection_reason` (why it's a useful design reference). No design judgments here.
3. **profile** — fill all 18 fields from research; no empty lists.
4. **claims** (optional) — only non-obvious, reusable design cause→effect (`subject relation object`) that the fixed profile fields can't express. Skip when there's none.
5. **Calibrate confidence honestly** — see table below.
6. **Name & save** — `id` = `game_<snake_case_title>`; save to `backend/app/fixtures/games/<snake_case_title>.json` (or the path the user specified). One file per game.
7. **Verify before claiming done** — run the snippet below; do not report success until it validates.

## Confidence calibration (the #1 thing to get right)

`confidence` = strength of evidence. `quality_status` = lifecycle state.

| Content | confidence |
|---|---|
| Directly observable, or backed by multiple authoritative sources (visible mechanics, release facts, store description) | `high` |
| Interpretive design judgment, even when drawn from an analysis article ("genre-defining", "casino-like reward cadence") | `medium` |
| Pure model inference with no external source | `low` |

`quality_status`: machine-generated output is `draft` (use `weak_evidence` when evidence is thin, `conflicting` when sources disagree). **Never emit `reviewed`** — that is reserved for human-checked entries. `high` confidence with `draft` quality is the *normal* combo: strong evidence, but no human has reviewed your output yet.

⚠️ The `balatro.json` sample shows `quality_status: "reviewed"` because it was hand-curated. **Do not copy `reviewed` from it** — your generated output is `draft`.

🚩 Red flag: everything is `high`/`reviewed`. That means you did not calibrate — go fix it.

## Field guidance (where the schema gets misread)

- `failure_model`: how a run/session ends in loss. Describe the lose condition even if the game reframes it.
- `production_constraints`: what made the game cheap/feasible to **build** (art style, scope, team size) — observable facts, not "preferences".
- claim `relation`: a short verb — `uses`, `reduces`, `increases`, `creates`, `demonstrates`, `enables`.
- `EvidenceRef`: needs `title` + `notes`, plus `url` OR `quote_or_summary`. Use `quote_or_summary` when paraphrasing without a link — never fabricate a URL.

## Verify before declaring done

```bash
cd backend && python -c "import json,sys; sys.path.insert(0,'.'); from app.services.import_service import validate_import_document, build_graph_write_plan; d=validate_import_document(json.load(open('app/fixtures/games/<slug>.json',encoding='utf-8'))); build_graph_write_plan(d); print('OK', d.candidate.id)"
```

Or, against a running backend, `python scripts/import_games.py app/fixtures/games/<slug>.json` (if that script is present).

## Common mistakes

- Marking everything `high`/`reviewed` → over-claims certainty. Calibrate per the table; never `reviewed`.
- Fabricating source URLs. Only cite pages you actually fetched; otherwise use `quote_or_summary`.
- Putting design judgments in `candidate` (they belong in `profile`/`claims`).
- `claims` that just restate profile fields. Claims are for cross-concept, reusable insight.
- Declaring done without running the verify step.
