# 前端游戏入库 & 知识图谱模块设计 Spec

## 1. 目的

后端已实现游戏入库(`POST /import/game` 写入 Neo4j)与图谱构建(Game 节点 + 类型化属性节点 + 带证据/置信度/质量的边)。本文档定义前端两个模块的完善方案,把它们从「只读 fixture 展示」升级为接入真实后端的可用功能:

- **游戏入库模块**:让用户在前端把生成好的 `GameImportDocument` JSON 粘贴/上传 → 本地校验 → 结构化预览 → 提交入库 → 查看结果。
- **知识图谱模块**:把图谱视图接到真实 Neo4j 数据,采用「聚焦 + 按需展开」探索方式,在 200+ 游戏规模下也不卡顿。

配套文档:

- 前端工作台:`2026-06-08-frontend-workbench-design.zh-CN.md`(本设计在其骨架上扩展)
- 后端 fixture 契约:`2026-06-08-backend-fixture-contract-design.zh-CN.md`
- 手动导入管道:`docs/superpowers/import-guide/game-import-prompt.md`

## 2. 范围

### 范围内

- 前端入库流程:JSON 粘贴/上传、本地 zod 校验、结构化预览、提交、结果页。
- 前端图谱探索器:随机焦点入口、搜索/列表选焦点、邻域子图渲染、按需展开、类型着色、关系类型筛选、超限保护、节点/边详情栏。
- 后端新增 3 个薄接口:`GET /games`、`GET /graph/neighbors`、`GET /graph/search`(复用现有 repository)。
- 前端数据访问层从 fixture 切换为真实 `fetch`(仅限本设计涉及的游戏/图谱数据;签名不变)。
- zod schema 镜像后端 `GameImportDocument`,用于入库前本地校验。
- Vitest + RTL 测试覆盖新增视图与关键规则(校验、降级展示、超限提示)。

### 范围外

- 用户登录、账号、权限、多用户。
- 手动 JSON 之外的入库方式(分步表单向导、可编辑预览)。
- 图谱写操作(在画布上编辑/删除节点边)。
- 换用 WebGL/canvas 图库(继续用 React Flow;留作后续扩展)。
- 机会框架 / 概念卡 / 原型简报 / 开发者画像视图的改动(维持现状)。
- SSE/轮询长任务进度真实接入。
- Playwright 端到端冒烟测试。

## 3. 设计原则

沿用工作台 spec 的原则,并强调:

### 3.1 前端不承载图遍历逻辑

图遍历、邻域计算、节点上限截断都在后端。前端只发请求、渲染返回的有界子图。

### 3.2 数据来源单点可替换

仍只有 `lib/data/` 接触数据来源。本次把相关函数体从读 fixture 改为 `fetch(API)`,页面与组件零改动。

### 3.3 大图不一次性渲染

任何时刻画布只渲染一个焦点的有界邻域(默认 1 跳,约 20 节点)。绝不加载全图。超限由后端截断 + 前端提示。

### 3.4 证据/置信度/质量状态全程可见

入库预览与图谱详情都必须一致展示置信度/质量,低置信度材料明显降级(沿用现有 `ConfidenceBadge`/`QualityBadge`/`EvidenceList`/`ClaimRow`)。

## 4. 后端新增接口

均为薄封装,复用 `GameRepository` 与现有 driver provider(`get_repository`)。新增 `app/api/routes_graph.py`(图谱查询)并在 `routes_import.py` 增加 `GET /games`,在 `main.py` 注册。

### 4.1 `GET /games` — 已入库游戏列表

供入库列表页与图谱焦点随机/选择。返回轻量摘要,不返回完整文档。

```
GET /games
→ 200 [
    { "id": "hollow_knight", "title": "Hollow Knight",
      "short_description": "...", "confidence": "high", "quality_status": "reviewed" },
    ...
  ]
```

Cypher:`MATCH (g:Game) RETURN g.id, g.title, g.short_description, g.confidence, g.quality_status ORDER BY g.title`。

### 4.2 `GET /graph/neighbors` — 邻域子图

```
GET /graph/neighbors?node_id=<游戏id 或 属性节点标识>&hops=1&limit=150&rel_types=HAS_MECHANIC,DELIVERS_EXPERIENCE
→ 200 {
    "focus": { "id": "...", "label": "Hollow Knight", "node_type": "Game" },
    "nodes": [ { "id": "...", "label": "...", "node_type": "Mechanic" }, ... ],
    "edges": [ { "id": "...", "source": "...", "target": "...", "relation": "HAS_MECHANIC",
                 "confidence": "high", "quality_status": "reviewed",
                 "claim_id": "...", "evidence": [ ... ] }, ... ],
    "truncated": false
  }
```

- `node_id`:游戏用 `id`,属性节点用 `name`(后端按 `node_type` 区分匹配键)。
- `hops`:默认 1,上限 2。
- `limit`:节点上限(默认 150)。后端用 `LIMIT` 截断;命中上限则 `truncated=true`。
- `rel_types`:可选,按关系类型过滤(对应 `PROFILE_LIST_EDGES` + `TAGGED`/`CLAIM`)。
- `confidence`/`quality_status`/`evidence`/`claim_id` 等从边/关系属性还原(`evidence_json` 反序列化)。
- 节点不存在 → 404。

### 4.3 `GET /graph/search` — 节点搜索

```
GET /graph/search?q=平台跳跃&limit=20
→ 200 [ { "id": "...", "label": "精准平台跳跃", "node_type": "Mechanic" }, ... ]
```

跨 `Game` 与属性节点按名称模糊匹配,返回可作为焦点的候选。

### 4.4 复用

`POST /import/game`、`GET /games/{id}` 不变,直接复用。

## 5. 前端类型与校验

### 5.1 zod schema(新增 `lib/import/schema.ts`)

镜像后端 `GameImportDocument`(`candidate: SeedGame`、`profile: GameDesignProfile`、`claims: DesignClaim[]`),用于粘贴/上传后的本地校验,把后端的字段约束(非空、列表 `min_length`、枚举值)前移到提交前,给出逐字段错误。后端契约校验仍是权威(前端校验只为快速反馈)。

### 5.2 图谱类型(扩展 `lib/data` 与 `lib/types`)

- `GraphNode`:增加 `node_type`(`Game` | `Mechanic` | `Experience` | `Concept` | `ReferenceTag` | `Genre` | …)。
- `NeighborhoodResult`:`{ focus, nodes, edges, truncated }`,镜像 4.2。
- `GameSummary`:镜像 4.1。
- `ImportSummary`:镜像后端返回。

## 6. 前端数据访问层(`lib/data/index.ts`)

新增/改写以下函数,内部改为真实 `fetch(API_BASE + ...)`,沿用现有 `API_BASE` 常量;保留 loading/error 语义:

```
listGames(): Promise<GameSummary[]>                      // GET /games
getNeighbors(params): Promise<NeighborhoodResult>        // GET /graph/neighbors
searchGraphNodes(q): Promise<GraphNode[]>                // GET /graph/search
importGame(doc): Promise<ImportSummary>                  // POST /import/game(含 409 错误透传)
```

`getGame(id)` 复用 `GET /games/{id}` 返回完整 `GameImportDocument`。对应 `lib/queries/` 新增 TanStack Query hooks(`useGames`、`useNeighbors`、`useImportGame` mutation 等)。

> 切换影响:`games/page.tsx` 与 `graph/page.tsx` 改为消费真实数据的新 hooks;原 fixture 驱动的 `getSeedGames`/`getGraph` 在这两个模块停用(机会/概念/原型/画像视图仍可继续用 fixture,不在本次范围)。

## 7. 入库模块视图

路由:在「资料库」组下,`/games` 列表页增加「导入游戏」入口,导入流程置于 `/games/import`。

### 7.1 列表页 `/games`

改为 `useGames()` 读真实 `GET /games`。表格列:标题(链接到 `/games/[id]`)、简述、置信度徽章、质量徽章。空态:"种子库暂无游戏,点此导入"。顶部「导入游戏」按钮 → `/games/import`。

### 7.2 导入页 `/games/import` — 三步

1. **输入**:大文本框粘贴 JSON + 「从剪贴板粘贴」「上传 .json 文件」按钮。输入即用 zod 校验。通过 → 绿色提示 + 进入预览;失败 → 内联逐字段错误(字段路径 + 原因)。
2. **结构化预览**:复用 artifact 组件渲染 `candidate`(标题、简述、选择理由、来源可展开)+ `profile`(一句话总结、核心钩子/循环、各属性列表 chips、参考价值标签带证据/置信度、整体置信度/质量徽章)+ `claims`(每条 `ClaimRow`,低置信度/弱证据降级)。底部「返回修改」「确认入库」。
3. **结果页**:成功显示 `ImportSummary`(机制/体验/标签/概念/论断计数)+ 「🔍 在图谱中查看」(跳 `/graph?focus=<id>`)/「查看游戏档案」/「再导入一个」。失败(后端 409 契约冲突)显示后端返回的具体 `detail`。

## 8. 知识图谱模块视图

路由:`/graph`(全宽)。

### 8.1 冷启动 / 焦点选择

- 进入时调用 `useGames()`,从列表中**随机挑一个游戏**作为初始焦点,加载其邻域。
- 顶部工具栏:当前焦点名 + **🎲 换一个**(重新随机)+ 搜索框(`searchGraphNodes`,选中即设为焦点)。
- 列表为空时:空态引导先去导入。
- 支持 `?focus=<id>` query param(从入库结果页跳入)。

### 8.2 画布(React Flow)

- 焦点节点居中,邻居环绕。节点**按 `node_type` 着色**,带图例。
- 边:沿用置信度降级着色(低置信度/弱证据/冲突 → 琥珀虚线)。
- **交互**:
  - 单击节点 → 选中,右栏显示详情。
  - 节点上「＋ 展开邻居」→ `getNeighbors(该节点)` 取下一跳,合并进画布(顺共享属性可带出关联游戏)。
  - 双击游戏节点 / 搜索选中 → 设为新焦点重新布局。
  - 单击边 → 右栏显示证据路径(沿用现有:关系 + 置信度 + 质量 + 来源论断 + 证据)。
- 顶部**关系类型筛选** chips(机制/体验/标签/概念/…)→ 作为 `rel_types` 传给后端或前端显隐边,控制密度。

### 8.3 超限保护

`getNeighbors` 返回 `truncated=true` 时,画布上方显示「结果过多,已截断;请加筛选或缩小跳数」。绝不渲染超过上限的子图。

### 8.4 详情栏

- 选中**节点**:名称、`node_type`;若为属性节点,显示「出现在 N 款游戏」与「＋展开邻居」。
- 选中**边**:沿用现有证据路径栏。

## 9. 状态处理

- 加载:`isLoading` → `Skeleton`。
- 错误:`isError` → 内联错误卡 + 重试(`refetch`)。后端不可达时图谱/列表显示明确错误态(本设计不为这两个模块做 fixture 回退)。
- 空态:无游戏 / 无邻域 / 搜索无结果 各有明确文案。
- 入库 mutation:pending 禁用提交按钮;成功跳结果态;409/网络错误显示具体原因。

## 10. 测试策略(Vitest + RTL)

- **入库校验**:合法 JSON 通过并进入预览;非法 JSON(空机制、缺证据、错枚举)给出逐字段错误且不进入预览。
- **入库提交**:mock `importGame`,断言成功显示 `ImportSummary` 与跳转入口;mock 409 断言显示后端 detail。
- **降级展示**:预览中低置信度/弱证据论断渲染降级标记。
- **图谱冷启动**:mock `listGames`,断言随机选中一个焦点并请求其邻域;🎲 重新随机。
- **图谱展开**:mock `getNeighbors`,点「＋展开邻居」断言新增节点并入画布。
- **超限提示**:`truncated=true` 时断言提示出现。
- **后端**(pytest):`GET /games`、`/graph/neighbors`(含 `truncated`、`rel_types` 过滤、404)、`/graph/search`,用 `dependency_overrides` 覆盖 repository(沿用现有测试模式)。

## 11. 成功标准

成功,如果:

- 用户能在前端粘贴/上传 `GameImportDocument`,本地校验后提交,真实写入 Neo4j 并看到 `ImportSummary`。
- `/games` 列表与 `/graph` 探索器读真实后端数据。
- 图谱以「聚焦 + 按需展开」工作,200+ 游戏规模下不一次性渲染全图,超限有保护。
- 进入图谱随机选焦点,🎲 可换,搜索/双击可改焦点,展开能顺共享属性发现关联游戏。
- 证据/置信度/质量在入库预览与图谱详情一致呈现,低置信度材料降级。
- 新增视图与关键规则有 Vitest/pytest 守护。

失败,如果:

- 前端把全图一次性加载导致卡顿,或自行承载图遍历/截断逻辑。
- 入库绕过校验直接写入,或低置信度材料被当作高置信度展示。
- 页面直接耦合 fetch 细节,绕过 `lib/data/` 单点。

## 12. 后续扩展方向

1. 图谱规模继续增大时,换 canvas/WebGL 图库(sigma.js / cytoscape)。
2. 入库支持可编辑预览(粘贴后在页面微调再提交)。
3. 图谱聚合概览(属性共现/聚类)作为探索的高层入口。
4. SSE/轮询接入长任务进度。
5. Playwright 端到端覆盖入库→图谱主流程。
