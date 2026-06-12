# 游戏导入 JSON 生成指南

把下面的「指令模板」连同一个游戏名（或商店链接）发给 Claude，得到一个 `GameImportDocument` JSON，再 `POST /import/game` 导入。

## 指令模板（直接复制）

> 你是游戏设计标注员。请为我给定的游戏产出**单个合法 JSON**，符合下方 `GameImportDocument` 结构，不要输出 JSON 以外的任何文字。
>
> 硬规则：
> - `candidate` 只写入库理由与客观描述，**不要**写设计判断或机制推断。
> - `profile` 必须填满全部字段，列表字段不得为空。
> - `claims` 可选（0 条也行）；只为「非显而易见、可跨概念复用」的设计因果写，形如 `主体 - 关系 - 客体`，能落成图的一条边。
> - 区分可观察事实与解释性判断；不确定的设计判断写入 `claims`，不要写进 `candidate`。
> - 不要断言这款游戏「好玩」或「会商业成功」。
> - **全部输出简体中文**；专有名词（游戏名/人名/引擎/语言如 `C++`）保留原文。
> - **进图字段必须是原子标签**：`main_player_actions` / `main_player_decisions` / `main_player_experiences` / `main_mechanics` / `replayability_sources` / `production_constraints` / `innovation_patterns` / `reusable_reference_patterns` / `non_replicable_risks` / `genre` / `art_style` / `audio_style` / `perspective` / `theme` / `narrative_style` / `game_feel` / `team_model` / `reference_value_tags` / `claims[].object`（含 `subject`）——每项一个名词或 1–4 字名词短语，不写整句、不带「玩法/参考/设计」等填充后缀，复合的拆成多项。散文字段（各 `*_summary`/`core_loop`/`progression_model`/`failure_model`/`content_structure`/`explanation`）写成完整中文句子。
> - **原子标签优先从 `.claude/skills/researching-games-for-import/preferred-terms.md` 选词**；没有合适的才造新词，并在交付 JSON 时另行列出新词供人工回填。
> - `core_hook`（核心创意/钩子）是**一句话散文**：用一句中文点出这款游戏最差异化的卖点，不拆成标签。

## JSON 骨架（字段说明见注释）

```jsonc
{
  "candidate": {
    "id": "game_<slug>",                  // 唯一 id，与 profile.game_id 一致
    "title": "<游戏标题>",
    "short_description": "<一句话客观描述>",
    "selection_reason": "<为什么值得进种子库>"
  },
  "profile": {
    "game_id": "game_<slug>",             // 必须等于 candidate.id
    "one_sentence_summary": "...",
    "core_hook": "<一句话核心创意/钩子>",
    "core_loop": "...",
    "progression_model": "...",
    "failure_model": "...",
    "content_structure": "...",
    "main_player_actions": ["..."],        // 原子标签
    "main_player_decisions": ["..."],      // 原子标签
    "main_player_experiences": ["..."],    // 原子标签
    "main_mechanics": ["..."],             // 原子标签
    "replayability_sources": ["..."],      // 原子标签
    "production_constraints": ["..."],     // 原子标签
    "innovation_patterns": ["..."],        // 原子标签
    "reusable_reference_patterns": ["..."],// 原子标签
    "non_replicable_risks": ["..."],       // 原子标签
    "genre": ["..."],                      // 原子标签
    "art_style": ["..."],                  // 原子标签
    "audio_style": ["..."],                // 原子标签
    "perspective": ["..."],                // 原子标签
    "theme": ["..."],                      // 原子标签
    "narrative_style": ["..."],            // 原子标签
    "game_feel": ["..."],                  // 原子标签
    "team_model": ["..."],                 // 原子标签
    "reference_value_tags": ["...", "..."] // 原子标签字符串列表，从 preferred-terms.md 选词
  },
  "claims": [
    {
      "id": "claim_<slug>",
      "subject": "<主体，可为游戏名或某机制>",
      "relation": "<关系动词，如 reduces / creates>",
      "object": "<客体概念，原子标签>",
      "explanation": "..."
    }
  ]
}
```

## 真实样例

见 `backend/app/fixtures/games/animal_well.json`（中文 + 原子标签），可照着改游戏名复用。

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

### 批量导入脚本

`backend/scripts/import_games.py` 封装了上面的 POST，支持单文件或整个文件夹，
并打印成功/失败汇总（仅走 HTTP，校验仍在服务端）：

```bash
cd backend

# 导入单个文件
python scripts/import_games.py path/to/your-game.json

# 导入整个文件夹下所有 *.json
python scripts/import_games.py app/fixtures/games/

# 指向远程 ECS（默认 http://localhost:8000）
GAMEGRAPH_API=http://<ECS_IP>:8100 python scripts/import_games.py games/
```

任一文件失败（422 schema 不合法 / 409 契约冲突 / 连接失败）脚本会以非零退出码结束。

