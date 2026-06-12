---
name: researching-games-for-import
description: Use when given one or more game names/titles and asked to produce importable GameImportDocument JSON for the GameGraph seed library (the manual 6.1/6.2 import pipeline).
---

# Researching Games For Import

## Overview

Turn a game name into an importable `GameImportDocument` JSON by researching the game online, then mapping findings into the schema. One JSON file per game.

Core principle: the value is honest, well-researched design analysis. The project has removed the `confidence`, `evidence`, and `quality_status` fields from the schema and now trusts the LLM's structured output directly.

## When to use

- User gives one or more game titles and wants seed-library JSON ("搜索分析生成导入 json", "给这几个游戏生成导入文件").
- Multiple names → produce one file per game.

Not for: generating concept cards, or changing the schema itself.

## Authoritative contract (read these, don't reinvent)

- Schema: `backend/app/schemas/import_document.py`, `artifacts.py`, `common.py`
- Filled sample to copy from: `backend/app/fixtures/games/animal_well.json`（中文 + 原子标签）
- Field skeleton + enums + hard rules: `docs/superpowers/import-guide/game-import-prompt.md`

Document is `{ candidate, profile, claims }`. `profile.game_id` MUST equal `candidate.id`. `claims` is optional (0..n). All list fields in `profile` must be non-empty.

## Workflow (per game)

1. **Research.** Use WebSearch + WebFetch on the store page (Steam/itch), Wikipedia, and 1–2 design write-ups or reviews.
2. **candidate** — title, one-line factual `short_description`, and `selection_reason` (why it's a useful design reference). No design judgments here.
3. **profile** — fill all fields from research; no empty lists.
4. **claims** (optional) — only non-obvious, reusable design cause→effect (`subject relation object`) that the fixed profile fields can't express. Skip when there's none.
5. **Name & save** — `id` = `game_<snake_case_title>`; save to `backend/app/fixtures/games/<snake_case_title>.json` (or the path the user specified). One file per game.
6. **Verify before claiming done** — run the snippet below; do not report success until it validates.

## 输出规范：语言、原子化、词表（本项目硬约束）

**1. 全中文**：所有生成文本一律简体中文——散文字段、原子标签、`reference_value_tags`、claims（`subject`/`object`/`explanation`）。例外：专有名词（游戏标题、人名、引擎/语言如 `C++`、平台名）保留原文。

**2. 散文 vs 原子标签，分开处理**：
- **散文字段**（写成完整中文句子）：`short_description`、`selection_reason`、`one_sentence_summary`、`core_hook`、`core_loop`、`progression_model`、`failure_model`、`content_structure`、claim 的 `explanation`。
- **原子标签字段**（会进图建节点，必须原子）：`main_player_actions`、`main_player_decisions`、`main_player_experiences`、`main_mechanics`、`replayability_sources`、`production_constraints`、`innovation_patterns`、`reusable_reference_patterns`、`non_replicable_risks`、`genre`、`art_style`、`audio_style`、`perspective`、`theme`、`narrative_style`、`game_feel`、`team_model`、`reference_value_tags`（字符串列表）、`claims[].object`（以及 `claims[].subject`）。

**3. 原子标签格式**：一个名词或 1–4 字中文名词短语；去掉「玩法/机制/系统/参考/设计/体验」等填充后缀；不写整句；一个特征一项，复合短语拆成多项。粒度取中：禁用「类银河城」这类把所有游戏连成一片的全集级词；也别只用「翻屏房间」这种仅一款独有的过窄词，优先想还能不能更通用。

bad → good：
| 描述性短语（错） | 原子标签（对） |
|---|---|
| `multi-purpose toy/tool usage` | `多用途道具` |
| `nonlinear flip-screen exploration` | `非线性探索`、`翻屏房间` |
| `an unsettling, eerie atmosphere` | `氛围营造`、`诡异` |
| `solo-developer custom-engine reference` | `独立开发`、`自研引擎` |

**4. 优先选词 + 新词上报**：原子标签**优先从 `preferred-terms.md`（与本技能同目录）选词**；表里确无合适词才造新词。由于文档 schema 禁止额外字段，新词**不能**塞进 JSON——交付 JSON 的同时，在对话里单独列出「本次用到、但词表里没有的新词」，供人工决定是否回填 `preferred-terms.md`。

## Field guidance (where the schema gets misread)

- `failure_model`: how a run/session ends in loss. Describe the lose condition even if the game reframes it.
- `production_constraints`: what made the game cheap/feasible to **build** (art style, scope, team size) — observable facts, not "preferences".
- claim `relation`: a short verb — `uses`, `reduces`, `increases`, `creates`, `demonstrates`, `enables`.

## Verify before declaring done

```bash
cd backend && python -c "import json,sys; sys.path.insert(0,'.'); from app.services.import_service import validate_import_document, build_graph_write_plan; d=validate_import_document(json.load(open('app/fixtures/games/<slug>.json',encoding='utf-8'))); build_graph_write_plan(d); print('OK', d.candidate.id)"
```

Or, against a running backend, `python scripts/import_games.py app/fixtures/games/<slug>.json` (if that script is present).

## Common mistakes

- Putting design judgments in `candidate` (they belong in `profile`/`claims`).
- `claims` that just restate profile fields. Claims are for cross-concept, reusable insight.
- Declaring done without running the verify step.
