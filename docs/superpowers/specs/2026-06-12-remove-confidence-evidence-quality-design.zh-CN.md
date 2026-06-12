# 移除 confidence / evidence / quality_status 设计

日期：2026-06-12
分支：`worktree-remove-confidence-evidence-quality`

## 背景与目标

项目早期把每条断言（claim）、关系（edge）、参考价值标签（tag）、游戏画像（profile）都设计成「证据支撑 + 可信度 + 质量状态」三件套：

- `confidence`（`ConfidenceLevel`：low/medium/high）
- `evidence` / `source_refs`（`EvidenceRef`：title/url/quote_or_summary/notes 来源引用）
- `quality_status`（`QualityStatus`：draft/reviewed/weak_evidence/conflicting）

现在的决策是**完全信任 LLM 输出，不再维护这套「信任/质量」元数据**。本设计把这三层从前后端契约、服务、图谱存储、约 200 个 fixture、测试与导入文档中彻底移除，只保留实质内容（subject/relation/object、explanation、tag、画像各字段等）。

## 范围边界（已确认）

**删除**——以下都用同一套「来源背书 + 可信度 + 质量」语义，全部移除：

- `ConfidenceLevel`、`QualityStatus`、`EvidenceRef` 三个类型本身
- 所有 `confidence`、`quality_status` 字段
- 所有 `EvidenceRef` 形态的字段：`SeedGame.source_refs`、`DesignClaim.evidence`、`GraphRelation.evidence`、`ReferenceValueTag.evidence`、`GameDesignProfile.evidence`、`GraphEdgeDTO.evidence`
- `ProfileFieldSource.confidence`（开发者画像解析器对每个抽取字段的把握度，用的是同一个 `ConfidenceLevel`）
- `ConceptEvaluation.evidence_quality_score`（前端概念评估里的「证据质量」打分项——证据没了即语义悬空）
- `ReferenceValueTag` 类整个删，`reference_value_tags` 拍扁成字符串数组

**保留**——名字里带 evidence 但语义不同、与「信不信 LLM」无关，**不动**：

- `OpportunityEvidence`（`anchor_game_id` / `target_value_game_ids` / `combination_game_ids`）：opportunity 匹配里由图谱**确定性**算出的「这个机会由哪些已有游戏推导而来」，是匹配算法的承重输入/输出结构。
- `OpportunityFrame.evidence_path`（推理路径文本，list[str]）：推导链路，不是来源出处。

> 注：`quality_status` 在早先讨论中曾考虑保留，最终决策为 confidence/evidence/quality_status 三者全删。

**超出本次范围**：

- `docs/superpowers/specs|plans/*` 的历史设计文档保持原样（带日期的历史记录，不回填改写）。
- 本 worktree 从 origin/main 起，批处理脚本作用于分支内已提交的 fixture；主工作区中尚未提交的新导入 fixture 由各自导入流程按更新后的 import skill 处理，不在本次直接覆盖。

## 改动设计（按层）

### 1. 后端 schema

**`backend/app/schemas/common.py`**
- 删 `ConfidenceLevel`、`QualityStatus`、`EvidenceRef`（含其 `require_reference_payload` validator）。
- 保留 `NonEmptyStr`、`StrictBaseModel`、`ConstraintType`。

**`backend/app/schemas/__init__.py`**
- 去掉 `ConfidenceLevel`、`QualityStatus`、`EvidenceRef` 的 import/export。

**`backend/app/schemas/artifacts.py`**
- `SeedGame`：删 `source_refs`。
- `DesignClaim`：删 `evidence`、`confidence`、`quality_status`。剩 id/subject/relation/object/explanation。
- `GraphRelation`：删 `evidence`、`confidence`、`quality_status`。剩 id/source_node/relation/target_node/claim_id。
- `ReferenceValueTag`：整个类删除。
- `GameDesignProfile`：`reference_value_tags` 改成 `list[NonEmptyStr] = Field(min_length=1)`；删 `evidence`、`confidence`、`quality_status`。
- 清理不再使用的 import（`ConfidenceLevel`、`EvidenceRef`、`QualityStatus`）。

**`backend/app/schemas/graph.py`**
- `GameSummary`：删 `confidence`、`quality_status`。
- `GraphEdgeDTO`：删 `confidence`、`quality_status`、`evidence`。
- 清理 import。

**`backend/app/schemas/developer_profile.py`**
- `ProfileFieldSource`：删 `confidence`。`field_sources` 与其余结构保留（仍记录哪段原文产出了哪个字段）。

**`backend/app/schemas/opportunity.py`**、**`import_document.py`**
- opportunity.py 不动。
- import_document.py 不改字段（`GameImportDocument` = candidate/profile/claims，随被引用的 schema 自动变窄）。

### 2. 后端服务 / 图谱存储

**`backend/app/services/import_service.py`**
- 节点/边写入属性中去掉 `confidence`、`quality_status`、`source_refs_json`、`evidence_json`（profile、reference_value_tag、claim 三处）。
- `reference_value_tags` 现在是字符串列表，按字符串写入标签节点。
- 删 `_EVIDENCE_LIST_ADAPTER`、`_evidence_json` 辅助。

**`backend/app/graph/game_repository.py`**
- Cypher 读取不再 `RETURN g.confidence / g.quality_status`。
- 写入端不再设置 Game 节点 `confidence/quality_status`、边/标签的 `evidence_json`。

**`backend/app/services/graph_query.py`**
- 组装 `GameSummary` / `GraphEdgeDTO` 时不再映射 confidence/quality_status/evidence。

**`backend/app/services/fixture_pipeline.py`**
- golden flow 组装去掉这些字段。

**`backend/app/services/developer_profile_parser.py`**
- `_source(...)` 去掉 `confidence` 参数及全部传参点（HIGH/MEDIUM/LOW）。

**`backend/app/services/profile_llm.py`**
- LLM 解析模型（line ~33）去掉 `confidence` 字段及其 prompt 指示。

**`backend/app/services/concept_llm.py`、`opportunity_llm.py`**
- 不动：用的是保留下来的 `frame.evidence_path` / `candidate.evidence.target_value_game_ids`。

### 3. 前端

**`frontend/lib/types/index.ts`**
- 删 `CONFIDENCE_LEVELS`/`ConfidenceLevel`、`QUALITY_STATUSES`/`QualityStatus`、`EvidenceRef` 接口。
- `SeedGame` 删 `source_refs`；`DesignClaim`、`GraphRelation` 删 evidence/confidence/quality_status；`ProfileFieldSource` 删 confidence；`GameDesignProfile` 删 evidence/confidence/quality_status（`reference_value_tags` 已是 `string[]`）；`GameSummary` 删 confidence/quality_status；`ConceptEvaluation` 删 `evidence_quality_score`。

**删除组件**：`frontend/components/artifacts/confidence-badge.tsx`、`quality-badge.tsx`、`evidence-list.tsx`。

**`frontend/components/artifacts/claim-row.tsx`**
- 去掉 `ConfidenceBadge`、`QualityBadge`、`EvidenceList` 引用与 `downgraded` 逻辑；只渲染 subject·relation·object + explanation。

**`frontend/components/graph/edge-style.ts`**
- 删 `isDowngraded`；`edgeColor` 回退单一默认色，`edgeSize` 固定值（不再按 confidence 分粗细/降级）。

**其余引用点清理**：`frontend/lib/data/index.ts`（`GraphEdge` 类型）、`components/import/import-preview.tsx`、`lib/import/schema.ts`、`app/(workbench)/games/page.tsx`、`app/(workbench)/games/[id]/page.tsx`、`app/(workbench)/graph/page.tsx`、`lib/fixtures/golden-flow.ts`、`lib/profile/parser.ts`。

### 4. Fixture 批处理（约 200 个 + `golden_flow.json`）

一次性 Python 脚本，遍历 `backend/app/fixtures/games/*.json`，对每个文件：

- 删 `candidate.source_refs`
- 删 `profile.evidence`、`profile.confidence`、`profile.quality_status`
- `profile.reference_value_tags`：`[{"tag": X, ...}]` → `[X, ...]`（拍扁为字符串）
- `claims[*]`：删 `evidence`、`confidence`、`quality_status`

要求：保持其余键顺序、2 空格缩进、`ensure_ascii=False`、末尾换行。`backend/app/fixtures/golden_flow.json` 按同一套规则处理（含 seed_games/design_claims/graph_relations/game_design_profiles 等结构）。脚本跑完即弃，不留在仓库。

### 5. 文档 / 导入 skill

防止以后又被生成回来：

- `.claude/skills/researching-games-for-import/SKILL.md`、`preferred-terms.md`
- `docs/.../import-guide/game-import-prompt.md`

去掉「产出 confidence / evidence / quality_status / source_refs」的指示，更新内嵌的示例 JSON schema，使其与新契约一致。历史 spec/plan 文档不动。

### 6. 测试

所有引用上述字段的测试更新到新契约（后端 `backend/tests/*`、前端 `*.test.ts(x)`）。关键校验：

- 加载全部 fixture 过 `GameImportDocument` 的测试在 strip 后仍绿。
- artifact 组件、edge-style、import schema、graph/games 页面相关测试更新断言。

## 验证口径

- **后端**：`cd backend; pytest`（worktree 内必须先 `cd backend/`，否则 import 到主仓库旧 editable app）。
- **前端**：`vitest --pool=threads`（本机 forks pool teardown 会崩；跑前确保 worktree 已 junction 链接主仓库 `node_modules`）。
- 两端全绿、`git status` 干净后再开 PR。

## 影响与权衡

- 这是破坏性契约变更，无向后兼容层——种子库内部项目、无外部消费者，刻意不做软删/Optional 过渡（YAGNI）。
- 前后端是 `extra="forbid"` 的镜像契约，字段必须同步删除，故单分支一次性改完，避免任何中间态校验失败。
- 图谱可视化失去「按可信度降级」表达；接受，因为「完全信任 LLM」前提下该表达无意义。
