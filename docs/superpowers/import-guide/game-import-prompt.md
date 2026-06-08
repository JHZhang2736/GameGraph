# 游戏导入 JSON 生成指南

把下面的「指令模板」连同一个游戏名（或商店链接）发给 Claude，得到一个 `GameImportDocument` JSON，再 `POST /import/game` 导入。

## 指令模板（直接复制）

> 你是游戏设计标注员。请为我给定的游戏产出**单个合法 JSON**，符合下方 `GameImportDocument` 结构，不要输出 JSON 以外的任何文字。
>
> 硬规则：
> - `candidate` 只写入库理由与来源，**不要**写设计判断或机制推断。
> - `profile` 必须填满全部字段，列表字段不得为空。
> - `claims` 可选（0 条也行）；只为「非显而易见、可跨概念复用」的设计因果写，形如 `主体 - 关系 - 客体`，能落成图的一条边。
> - 仅凭你自身知识、没有外部出处的论断，`confidence` **不得**标 `high`，应标 `medium` 或 `low`，并在 `quality_status` 用 `draft` 或 `weak_evidence`。
> - 区分可观察事实与解释性判断；不确定就如实降置信度，不要假装确定。
> - 不要断言这款游戏「好玩」或「会商业成功」。
> - `confidence` 取值：`low` / `medium` / `high`。`quality_status` 取值：`draft` / `reviewed` / `weak_evidence` / `conflicting`。
> - 每个 `EvidenceRef` 必须有 `title` 与 `notes`，并且 `url` 与 `quote_or_summary` 至少有一个；没有外部链接时填 `quote_or_summary`。

## JSON 骨架（字段说明见注释）

```jsonc
{
  "candidate": {
    "id": "game_<slug>",                  // 唯一 id，与 profile.game_id 一致
    "title": "<游戏标题>",
    "source_refs": [
      { "title": "...", "url": "...", "notes": "..." }
    ],
    "short_description": "<一句话客观描述>",
    "selection_reason": "<为什么值得进种子库>"
  },
  "profile": {
    "game_id": "game_<slug>",             // 必须等于 candidate.id
    "one_sentence_summary": "...",
    "core_loop": "...",
    "progression_model": "...",
    "failure_model": "...",
    "content_structure": "...",
    "main_player_actions": ["..."],
    "main_player_decisions": ["..."],
    "main_player_experiences": ["..."],
    "main_mechanics": ["..."],
    "replayability_sources": ["..."],
    "production_constraints": ["..."],
    "innovation_patterns": ["..."],
    "reusable_reference_patterns": ["..."],
    "non_replicable_risks": ["..."],
    "reference_value_tags": [
      {
        "tag": "...",
        "confidence": "high|medium|low",
        "quality_status": "reviewed|draft|weak_evidence|conflicting",
        "evidence": [ { "title": "...", "quote_or_summary": "...", "notes": "..." } ]
      }
    ],
    "evidence": [ { "title": "...", "quote_or_summary": "...", "notes": "..." } ],
    "confidence": "high|medium|low",
    "quality_status": "reviewed|draft|weak_evidence|conflicting"
  },
  "claims": [
    {
      "id": "claim_<slug>",
      "subject": "<主体，可为游戏名或某机制>",
      "relation": "<关系动词，如 reduces / creates>",
      "object": "<客体概念>",
      "explanation": "...",
      "evidence": [ { "title": "...", "quote_or_summary": "...", "notes": "..." } ],
      "confidence": "high|medium|low",
      "quality_status": "reviewed|draft|weak_evidence|conflicting"
    }
  ]
}
```

## 真实样例

见 `backend/app/fixtures/games/balatro.json`，可照着改游戏名复用。

## 导入流程

```bash
# 1) 起本地 Neo4j（首次）
cd backend && docker compose up -d neo4j

# 2) 起后端
cd backend && uvicorn app.main:app --reload

# 3) 导入某个游戏 JSON
curl -X POST http://localhost:8000/import/game \
  -H "Content-Type: application/json" \
  -d @path/to/your-game.json

# 4) 读回核对
curl http://localhost:8000/games/game_<slug>
```
