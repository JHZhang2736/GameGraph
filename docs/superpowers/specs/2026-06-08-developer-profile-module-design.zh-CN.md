# 开发者画像模块（6.4）设计 Spec

## 1. 目的

本文档定义独立游戏创意图谱系统中 6.4「开发者画像模块」的第一版实现边界。

该模块负责把开发者的自由表达转成下游可使用的结构化画像。它不是推荐模块，不生成机会框架或概念卡，也不把所有偏好都压成硬过滤条件。

第一版采用用户已确认的混合式工作流：

```text
自由文本输入
-> 确定性画像解析
-> 结构化草稿预览
-> 缺失信息提示
-> 用户可编辑确认
-> DeveloperProfile
```

这一版先用规则解析和本地数据层打通纵切 MVP，不接入真实 LLM，不要求新增完整后端 API 基础设施。后续接入 LLM 或 FastAPI route 时，必须复用本文定义的输入、草稿、解析结果和缺失字段契约。

## 2. 范围

### 范围内

- 扩展后端 schema：新增画像输入、草稿、解析结果、缺失字段、字段来源等契约。
- 新增确定性画像解析服务：将自由文本解析为 `DeveloperProfileDraft`。
- 识别硬性约束、强偏好、软偏好，并保留用户原始表达。
- 识别关键缺失信息，防止不完整画像被静默当作完整画像。
- 将完整草稿提升为现有 `DeveloperProfile`。
- 前端 `/profile` 改为混合式工作台：左侧输入，右侧结构化预览与缺失信息。
- 前端数据层提供同形状的本地解析函数，未来可替换为真实 `fetch`。
- 后端 pytest 和前端 Vitest 覆盖核心行为。

### 范围外

- 真实 LLM provider、prompt orchestration 或流式解析。
- 机会匹配、机会框架、概念生成或概念评分。
- 多用户、账号、权限、画像历史版本。
- 持久化数据库写入。
- 完整 FastAPI route 基础设施；若当前分支已有 API 层，可在实现计划中选择性接入，但不是本 spec 的必要条件。
- 自动从 Steam、商店页或游戏库推断用户偏好。

## 3. 当前上下文

已有后端 `DeveloperProfile` schema，字段包括团队规模、时间预算、程序能力、美术能力、音频能力、内容生产能力、喜欢参考、讨厌参考或机制、期望体验和约束列表。

已有前端 `/profile` 只读页和 typed fixture，可以展示当前 golden flow 中的 `developer_profile`。但它还不是 6.4 模块，因为它不能从用户输入生成画像，不能标出缺失信息，也不能解释字段来源。

因此本次工作不是重写所有画像展示，而是在现有 `DeveloperProfile` 之前补上一个稳定的“输入 -> 草稿 -> 确认”边界。

## 4. 设计原则

### 4.1 草稿和正式画像分离

`DeveloperProfileDraft` 可以不完整，必须显示缺失项。`DeveloperProfile` 是下游机会匹配使用的正式产物，只能由完整且确认过的草稿生成。

### 4.2 约束分级不可丢失

系统必须区分：

- 硬性约束：不得违反。
- 强偏好：通常应尊重，可在高收益挑战型方向中被明确权衡。
- 软偏好：影响排序和解释，不阻断方案。

解析器不得把所有 “我喜欢 / 我希望 / 我偏好” 都当成硬性约束。

### 4.3 保留原始表达

每个被解析出的字段和约束都应能追溯到用户原文片段。后续如果机会匹配引用某个画像字段，人类可以检查系统为什么这样理解用户。

### 4.4 确定性优先

第一版解析服务使用透明规则，目标是可测试、可调试、可替换。它不假装理解所有自然语言；遇到模糊信息时应标记缺失或低确定性。

## 5. 推荐目录结构

```text
backend/
  app/
    schemas/
      artifacts.py              # 现有 DeveloperProfile 保持下游正式产物
      developer_profile.py       # 新增：输入、草稿、解析结果、缺失字段
    services/
      developer_profile_parser.py # 新增：确定性解析 + 草稿提升
  tests/
    test_developer_profile_parser.py
    test_developer_profile_contracts.py

frontend/
  app/
    (workbench)/
      profile/
        page.tsx                 # 改为混合式工作台
        profile-page.test.tsx
  components/
    profile/
      profile-input-panel.tsx
      profile-draft-preview.tsx
      profile-missing-fields.tsx
      profile-source-list.tsx
  lib/
    profile/
      parser.ts                  # 前端本地解析适配器，镜像后端行为
      parser.test.ts
    data/
      index.ts                   # 暴露 parseDeveloperProfileInput 等函数
```

说明：

- 后端 `schemas/developer_profile.py` 是权威契约。
- 前端本地解析只为当前无 API 的工作台服务，必须保持与后端契约同形状。
- 页面只依赖 `lib/data` 或 `lib/queries`，不直接读 fixture 或散落解析逻辑。

## 6. 后端契约

### 6.1 ProfileParseInput

表示一次画像解析请求。

必需字段：

- `raw_text`: 用户自由文本。

可选字段：

- `liked_references`: 用户显式填写的喜欢游戏或参考。
- `disliked_references_or_mechanics`: 用户显式填写的讨厌游戏、机制或方向。
- `expected_project_scale`: 用户显式填写的项目规模。

规则：

- `raw_text` 允许很短，但不能全空。
- 可选列表字段中的空字符串应被清理或拒绝。
- 显式字段优先级高于从 `raw_text` 中推断出的同类信息。

### 6.2 ProfileFieldSource

记录字段来源。

必需字段：

- `field`: 字段名，例如 `team_size`、`time_budget`、`constraints`。
- `source_text`: 来自用户原文或显式字段的片段。
- `source_kind`: `raw_text` 或 `explicit_field`。
- `confidence`: `low`、`medium`、`high`。

用途：

- 解释解析结果。
- 帮助用户检查画像是否被误读。
- 为后续 LLM 解析器保留同一审计接口。

### 6.3 MissingProfileField

表示画像中仍缺少或模糊的信息。

必需字段：

- `field`: 缺失字段名。
- `reason`: 为什么缺失或模糊。
- `blocking`: 是否阻止草稿提升为正式画像。

第一版 blocking 字段：

- `team_size`
- `time_budget`
- `programming_ability`
- `art_ability`
- `content_production_ability`
- `desired_player_experiences`

第一版非 blocking 字段：

- `audio_ability`
- `liked_references`
- `disliked_references_or_mechanics`

说明：

- 音频能力缺失可以默认标为 `unknown/basic`，但必须显示来源不充分。
- 不喜欢的机制为空是允许的，不能强迫用户填写。

### 6.4 DeveloperProfileDraft

表示可编辑画像草稿。

字段与现有 `DeveloperProfile` 基本一致，但允许关键字段为 `null` 或空列表，并额外携带解析状态。

必需字段：

- `id`
- `team_size`
- `time_budget`
- `programming_ability`
- `art_ability`
- `audio_ability`
- `content_production_ability`
- `liked_references`
- `disliked_references_or_mechanics`
- `desired_player_experiences`
- `constraints`
- `missing_fields`
- `field_sources`
- `raw_text`
- `is_complete`

规则：

- `constraints` 可以为空，但如果用户文本中出现明显禁止或偏好措辞，必须生成对应约束。
- `is_complete` 由 blocking 缺失字段决定，不能由前端随意设置。
- 草稿不得直接用于机会匹配，除非 `is_complete=true` 且被提升为 `DeveloperProfile`。

### 6.5 ProfileParseResult

解析服务输出。

必需字段：

- `draft`: `DeveloperProfileDraft`
- `warnings`: 非阻断提示，例如“时间预算表述较模糊”。

### 6.6 promote_draft_to_profile

纯函数：

```text
promote_draft_to_profile(draft: DeveloperProfileDraft) -> DeveloperProfile
```

规则：

- 如果 `draft.is_complete=false`，抛出 `ContractViolation`，消息为 `DeveloperProfileDraft is incomplete`。
- 输出必须符合现有 `DeveloperProfile` schema。
- 输出不包含 `missing_fields`、`field_sources`、`raw_text` 等草稿审计字段。

## 7. 解析规则

第一版规则不追求覆盖所有自然语言，只覆盖产品示例和常见输入。

### 7.1 团队规模

示例匹配：

- `solo`、`一个人`、`单人`、`独立开发者` -> `solo`
- `两个人`、`2人`、`小团队` -> 保留原始表述，如 `small team`

### 7.2 时间预算

示例匹配：

- `三个月`、`3个月`、`three month` -> `three month prototype`
- `周末`、`业余`、`part-time` -> 记录为时间预算，但添加 warning，提示缺少周期长度。
- `尽快`、`短期` 等模糊表述 -> `time_budget` 为空，添加 blocking 缺失字段。

### 7.3 能力字段

示例匹配：

- 程序：`程序强`、`擅长编程`、`会写系统`、`strong programming` -> `strong`
- 美术：`美术弱`、`不会画`、`低美术`、`weak art` -> `weak`
- 音频：`音频一般`、`基础音效`、`basic audio` -> `basic`
- 内容生产：`不想做大量内容`、`内容产能有限` -> `limited`

如果能力没有出现：

- blocking 能力字段进入 `missing_fields`。
- 音频能力可默认 `basic` 或 `unknown`，但 field source 置信度为 `low`。

### 7.4 喜欢和讨厌

喜欢参考：

- 从 `喜欢 Balatro 和 Into the Breach`
- 从显式 `liked_references`
- 从 `参考 A / B` 这类表达

讨厌参考或机制：

- 从 `不想做在线多人`
- 从 `讨厌长剧情`
- 从显式 `disliked_references_or_mechanics`

规则：

- 喜欢的游戏只表示兴趣，不表示要复制。
- 讨厌或不想做的方向可能生成约束，但必须根据措辞分级。

### 7.5 期望体验

示例匹配：

- `短局`、`short runs`
- `系统性决策`、`systemic decisions`
- `战术预测`、`tactical prediction`
- `高重玩`、`replayability`

若用户只列喜欢游戏但没有表达想要的玩家体验，应将 `desired_player_experiences` 标为缺失，而不是从游戏名静默推断。

### 7.6 约束分级

硬性约束触发词：

- `不能`
- `绝对不要`
- `不做`
- `不要依赖`
- `must not`
- `do not`

强偏好触发词：

- `不想`
- `尽量不要`
- `偏向`
- `希望`
- `prefer`

软偏好触发词：

- `喜欢`
- `感兴趣`
- `可以`
- `倾向`

示例：

- “不要做在线多人” -> hard，`Do not require online multiplayer.`
- “我不想做长篇叙事” -> strong_preference，`Avoid long scripted narrative.`
- “喜欢短局和系统性决策” -> soft_preference 或 desired experience，不是 hard。

## 8. 前端交互设计

### 8.1 页面结构

`/profile` 第一屏就是可用工作台，不做 landing page。

布局：

```text
PageHeader

两栏工作区
左侧：自由文本输入 + 显式字段小表单 + 解析按钮
右侧：结构化画像预览 + 完整度状态

下方：
约束分区
缺失信息
字段来源
```

桌面端两栏并排；移动端上下堆叠。页面保持工作台风格，不使用营销式 hero。

### 8.2 左侧输入

组件：`ProfileInputPanel`

控件：

- 多行文本框：自由描述。
- 可选输入：喜欢参考、讨厌参考或机制、期望项目规模。
- 按钮：解析画像。

默认文本可使用 golden flow 示例，方便本地验证：

```text
我是 solo 开发者，程序能力强，美术能力弱，想做三个月内能验证的原型。
我喜欢 Balatro 和 Into the Breach，想要短局、系统性决策和战术预测。
不要做在线多人，我不想做长篇叙事内容。
```

### 8.3 右侧预览

组件：`ProfileDraftPreview`

展示：

- 完整度状态：`完整` / `缺少关键信息`。
- 能力与预算字段。
- 喜欢参考、讨厌方向、期望体验。
- 硬性约束、强偏好、软偏好分区。

硬性约束必须比偏好更醒目，但不要把页面做成警告墙。

### 8.4 缺失信息

组件：`ProfileMissingFields`

展示每个缺失字段：

- 字段名。
- 缺失原因。
- 是否阻断确认。

若存在 blocking 缺失字段，确认按钮 disabled，并显示明确原因。

### 8.5 字段来源

组件：`ProfileSourceList`

展示：

- 字段名。
- 原文片段。
- 来源类型。
- 置信度。

这是 6.4 的解释性基础，后续机会匹配引用画像字段时可以复用。

## 9. 数据流

当前无真实 API 的第一版：

```text
ProfilePage
-> useState 保存输入
-> parseDeveloperProfileInput(input) from lib/data
-> 本地确定性 parser 返回 ProfileParseResult
-> 页面渲染 draft / missing_fields / field_sources
```

未来接 API：

```text
ProfilePage
-> lib/data.parseDeveloperProfileInput
-> fetch('/api/profile/parse')
-> ProfileParseResult
```

要求：

- 页面不关心解析发生在本地还是后端。
- 后端 schema 与前端类型字段名保持一致。
- 若实现计划中新增 FastAPI route，route 只薄封装后端解析服务，不在 route 里写解析规则。

## 10. 测试策略

### 10.1 后端契约测试

`test_developer_profile_contracts.py`

覆盖：

- `ProfileParseInput` 拒绝空文本。
- `DeveloperProfileDraft` 接受不完整草稿。
- `MissingProfileField.blocking` 可区分阻断和非阻断。
- `promote_draft_to_profile` 拒绝不完整草稿。
- 完整草稿可提升为现有 `DeveloperProfile`。

### 10.2 后端解析测试

`test_developer_profile_parser.py`

覆盖：

- solo、三个月、程序强、美术弱、内容有限被正确解析。
- “不要做在线多人” 生成 hard constraint。
- “不想做长篇叙事” 生成 strong_preference。
- “喜欢短局和系统性决策” 不被当成 hard constraint。
- 只有喜欢游戏但无期望体验时，`desired_player_experiences` 被标为缺失。
- 模糊时间预算触发 blocking 缺失字段。
- 每个解析出的关键字段都有 `ProfileFieldSource`。

### 10.3 前端 parser 测试

`frontend/lib/profile/parser.test.ts`

覆盖：

- 默认示例文本返回完整草稿。
- 删除时间预算后显示 blocking 缺失字段。
- 硬性约束、强偏好、软偏好分级稳定。
- 显式字段优先于自由文本推断。

### 10.4 前端页面测试

`frontend/app/(workbench)/profile/profile-page.test.tsx`

覆盖：

- 页面渲染自由文本输入和结构化预览。
- 用户修改文本并点击解析后，预览更新。
- hard constraint 使用 `data-constraint="hard"` 或等价稳定标记。
- blocking 缺失字段可见，确认按钮 disabled。
- 完整画像时显示可确认状态。

## 11. 成功标准

这一步成功，如果：

- 用户能在 `/profile` 输入一段自然描述，并看到结构化画像草稿。
- 系统能明确区分硬性约束、强偏好和软偏好。
- 缺失关键信息不会被静默补全为确定事实。
- 每个关键字段可追溯到原始表达或显式输入。
- 完整草稿可以提升为现有 `DeveloperProfile`，供 6.5 机会匹配使用。
- 后端和前端测试能证明解析规则、缺失字段和约束分级稳定。
- 6.1、6.2、6.3 的导入、标注、图谱工作不受影响。

这一步失败，如果：

- 页面只是展示 fixture，没有从用户输入生成画像。
- 解析器把所有偏好都当成硬约束。
- 模糊时间预算被悄悄当作完整字段。
- 字段来源丢失，无法解释为什么这样解析。
- 前端页面直接耦合 fixture，未来接 API 要逐页重写。
- 6.4 直接生成机会框架或概念卡，越过 6.5/6.6 边界。

## 12. 后续扩展方向

1. 新增 `POST /profile/parse` 和 `POST /profile/confirm`，把当前本地解析切到后端服务。
2. 接入 LLM parser，但输出仍必须通过 `ProfileParseResult` schema。
3. 支持多轮补问：只针对 blocking 缺失字段提问。
4. 支持画像版本历史和人工确认记录。
5. 将 `field_sources` 接入 6.5 机会匹配解释链。
