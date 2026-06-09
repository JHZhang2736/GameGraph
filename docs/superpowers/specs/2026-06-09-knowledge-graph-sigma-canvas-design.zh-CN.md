# 知识图谱画布迁移到 Sigma.js 设计文档

> 状态:已与用户确认,待写实现计划(writing-plans)。
> 日期:2026-06-09
> 范围:仅前端画布层(`frontend/`),后端不改动。

## 1. 背景与目标

当前知识图谱用 `@xyflow/react`(React Flow v12)渲染:

- React Flow 是流程图/节点编辑器工具,定位由开发者手动指定。
- 现有实现把节点用 `cos/sin` 按下标排成一个**固定圆环**,无物理布局、无空间语义。
- 节点是 160px 宽的**矩形**(带颜色边框),边是直线。
- 结果:可读性差、不像图谱,用户明确反馈"太难看"。

**目标**:换成专业网络图谱渲染,贴近 Neo4j Browser 的观感——力导向自动布局、圆形彩色节点、关系标签、可拖拽缩放——同时**完整保留现有数据流与交互逻辑**。

**已确认的取舍**:选用 **Sigma.js(WebGL)** 作为成熟稳定的渲染框架,接受两点妥协:

1. 节点标签画在**圆外侧旁边**(Sigma 默认行为),而非嵌在圆内。
2. 边的关系标签**仅 hover 时显示**,而非常显。
3. 低置信度/弱证据的"降级边"用**琥珀色 + 更细线**表达,**不使用虚线**(Sigma 原生不支持虚线边,虚线需手写 WebGL edge program,与"用成熟稳定、不手写 WebGL"的原则冲突)。

## 2. 范围

**改动**:

- 移除依赖 `@xyflow/react`。
- 新增 Sigma 技术栈依赖。
- 重写 `frontend/components/graph/graph-canvas.tsx`。
- 新增前端关系类型中文映射模块。
- 新增若干纯函数辅助模块(节点尺寸、边样式)以便单测。
- `frontend/app/(workbench)/graph/page.tsx` 仅做最小改动(动态导入画布)。

**不改动**:

- 后端任何代码、API、Cypher。
- `getNeighbors` / `searchGraphNodes` / `listGames` 等数据层(`frontend/lib/data`)。
- 证据面板、置信度/质量徽章、`focusOn`、`mergeNeighborhood`、🎲 reroll、截断提示等逻辑。
- `GraphCanvas` 对外的 props 契约:`{ graph, onSelectEdge?, onSelectNode? }` 保持不变,因此 `page.tsx` 的调用方式不变。

## 3. 技术栈与依赖

新增依赖(均为 Sigma 官方或其生态稳定包):

| 包 | 用途 |
|---|---|
| `sigma` | WebGL 图谱渲染核心(v3) |
| `graphology` | 图数据模型(节点/边容器) |
| `graphology-layout-forceatlas2` | ForceAtlas2 力导向布局算法 |
| `@react-sigma/core` | React 集成:`SigmaContainer`、`useLoadGraph`、`useRegisterEvents`、`useSigma`、`useSetSettings` |
| `@react-sigma/layout-forceatlas2` | `useWorkerLayoutForceAtlas2`,后台 worker 跑实时物理布局,产生"漂浮"收敛感 |
| `@sigma/edge-curve` | 曲线边 + 箭头渲染程序(贴近 Neo4j 观感、避免重边重叠) |

移除依赖:`@xyflow/react`。

**版本策略**:实现时安装上述包的当前稳定版本,锁定到 `package.json`。`@react-sigma/*` 需与所装 `sigma` 主版本匹配(v3 线)。

## 4. 架构与数据流

```
graph/page.tsx  (已有, 几乎不动)
  ├─ useGames() → 选随机焦点 / reroll
  ├─ focusOn(nodeId) → getNeighbors() → mergeNeighborhood() → setGraph(GraphData)
  ├─ selectedEdge 状态 → 右侧证据面板 (已有)
  └─ <GraphCanvasDynamic graph onSelectNode onSelectEdge />   ← next/dynamic, ssr:false

GraphCanvas (重写, "use client")
  ├─ <SigmaContainer settings>
  │    └─ <GraphController graph onSelectNode onSelectEdge />
  └─ 内部:
       GraphController:
         ├─ useLoadGraph：把 GraphData → graphology Graph
         │     节点：x/y 初始播种、size(按 degree)、color(按 node_type)、label
         │     边：曲线类型、color(降级判定)、size、隐藏的 label(hover 才显)
         ├─ useWorkerLayoutForceAtlas2：启动/停止物理布局
         ├─ useRegisterEvents：clickNode→onSelectNode、clickEdge→onSelectEdge、
         │     拖拽(downNode/mousemovebody/mouseup)、hover 高亮
         └─ useSetSettings + reducer：hover 时高亮焦点+邻居、淡化其余、显示边标签
```

**关键点**:数据来源仍是上层传入的 `GraphData`(`{ nodes: GraphNode[], edges: GraphEdge[] }`)。`GraphNode` 含 `id/label/node_type`,`GraphEdge` 含 `id/source/target/relation/confidence?/quality_status?/claim_id?/evidence`。画布只负责把这份数据渲染出来并回调交互,不发请求、不管理图状态。

## 5. 文件结构

| 文件 | 动作 | 职责 |
|---|---|---|
| `frontend/components/graph/graph-canvas.tsx` | 重写 | Sigma 容器 + 控制器组件;导出 `GraphCanvas`、`nodeColor`(保留供测试) |
| `frontend/components/graph/relation-labels.ts` | 新建 | `relationLabel(relation: string): string` 关系英→中映射,缺失回退原文 |
| `frontend/components/graph/node-style.ts` | 新建 | `nodeColor(nodeType)`(从 canvas 迁出)、`nodeSize(degree, isFocus)` 纯函数 |
| `frontend/components/graph/edge-style.ts` | 新建 | `isDowngraded(edge)`、`edgeColor(edge)`、`edgeSize(edge)` 纯函数 |
| `frontend/components/graph/relation-labels.test.ts` | 新建 | `relationLabel` 单测 |
| `frontend/components/graph/node-style.test.ts` | 新建 | `nodeColor`/`nodeSize` 单测 |
| `frontend/components/graph/edge-style.test.ts` | 新建 | `isDowngraded`/`edgeColor`/`edgeSize` 单测 |
| `frontend/components/graph/graph-canvas.test.tsx` | 改 | 改为从 `node-style` 导入 `nodeColor`(保持既有断言通过) |
| `frontend/app/(workbench)/graph/page.tsx` | 改(最小) | 用 `next/dynamic`(`ssr:false`)引入 `GraphCanvas` |
| `frontend/package.json` | 改 | 增删依赖 |

> 把 `nodeColor` 从 `graph-canvas.tsx` 迁到 `node-style.ts`,是因为 `graph-canvas.tsx` 重写后将依赖 Sigma/WebGL,无法在 jsdom 中 import;纯函数单独成文件才能继续被单测。`graph-canvas.tsx` 仍 re-export `nodeColor` 以兼容现有 import 路径。

## 6. 视觉映射规格

### 6.1 节点

- **形状**:圆形(Sigma 默认 circle 程序)。
- **颜色**:`nodeColor(node_type)`,沿用现有色板:
  - `Game` `#4f46e5`;`Mechanic`/`PlayerAction`/`PlayerDecision` `#818cf8`;`Experience` `#14b8a6`;`Concept` `#f87171`;`ReferenceTag` `#f59e0b`;其余回退 `#94a3b8`。
- **大小**:`nodeSize(degree, isFocus)`。基准 `6`,每条边 `+1.2`,clamp 到 `[6, 18]`;焦点节点额外 `+4`。degree 由 `GraphData.edges` 统计(source/target 命中次数)。
- **标签**:`node.label`(中文游戏名/属性名已是中文),显示在节点圆外侧(Sigma 默认)。焦点节点 label 强制常显。

### 6.2 边

- **类型**:`@sigma/edge-curve` 曲线 + 箭头(`type: "curvedArrow"` 或等价),方向沿用 `edge.source → edge.target`(已是真实方向)。
- **关系标签(中文)**:`relationLabel(edge.relation)`。映射表初版:
  - `HAS_MECHANIC → 具备机制`
  - `DELIVERS_EXPERIENCE → 带来体验`
  - `CLAIM → 论断`
  - `TAGGED → 标签`
  - `HAS_GENRE → 类型`
  - `HAS_ART_STYLE → 美术风格`
  - claim 关系值:`reinforces → 强化`、`enables → 使能`、`tensions_with → 张力`、`requires → 需要`、`contrasts_with → 对比`(以后端实际出现的 relation 值为准,缺失一律回退显示原始英文,不丢失信息)。
- **显示时机**:边标签平时隐藏,**hover 节点/边时**显示相关边的标签(见 6.4)。
- **降级表达**:`isDowngraded(edge)` 为真时(`confidence === "low"` 或 `quality_status ∈ {weak_evidence, conflicting}`),边用**琥珀色 `#d97706` + 更细线**;否则按置信度上色——`high → #16a34a`、`medium → #71717a`、`low`/无 → `#94a3b8`,线宽正常。**不使用虚线。**

### 6.3 布局

- 初始:为每个节点播种坐标(随机或环形种子),焦点节点置于中心 `(0,0)` 附近。
- 物理:`useWorkerLayoutForceAtlas2` 启动 FA2(开 `barnesHut`/`adjustSizes` 一类常用参数让圆不重叠),挂载后跑一小段时间收敛,可持续运行让拖拽后自然回弹。
- 展开:`mergeNeighborhood` 加入新节点后,新节点在焦点附近播种,FA2 重新收敛(由上层 `graph` prop 变化驱动 `useLoadGraph` 重建或增量更新)。

### 6.4 Hover 高亮(Neo4j 同款手感)

- 悬停某节点:高亮该节点 + 直接邻居 + 相连边,其余节点/边降低不透明度;显示相连边的中文关系标签。
- 悬停某边:高亮该边及其两端节点,显示该边标签。
- 离开:恢复默认。
- 用 `useSetSettings` 的 `nodeReducer`/`edgeReducer` 基于一个 `hoveredNode`/`hoveredEdge` 本地状态实现,不改图数据。

## 7. 交互规格

| 交互 | 行为 | 对接 |
|---|---|---|
| 点击节点 | 触发 `onSelectNode(nodeId)` | page 的 `focusOn(id, false)` 展开邻居 |
| 点击边 | 触发 `onSelectEdge(edgeId)` | page 设置 `selectedEdge`,右侧证据面板 |
| 拖拽节点 | `downNode` 记录 → `mousemovebody` 更新坐标(并阻止相机平移)→ `mouseup` 释放 | Sigma 官方拖拽示例模式 |
| 滚轮 | 缩放 | Sigma 内置 |
| 空白拖拽 | 平移相机 | Sigma 内置 |
| 🎲 / 截断 / 证据面板 | 不变 | page 既有逻辑 |

## 8. SSR 约束

- Sigma 在渲染/初始化时访问 `window`/WebGL,不能在服务端执行。
- `GraphCanvas` 标 `"use client"`,并在 `page.tsx` 中用 `next/dynamic` 以 `{ ssr: false }` 引入,避免 SSR 阶段实例化 Sigma。
- ⚠️ 本项目 Next.js 16.2.7 行为偏离常规(见 `frontend/AGENTS.md`)。实现前**必须**先查 `node_modules/next/dist/docs/` 确认该版本 `next/dynamic` 与 `ssr:false` 的正确用法,再写代码。

## 9. 测试策略

- Sigma 依赖 WebGL,jsdom 无法渲染画布——**沿用现有做法,只对纯函数做单测**,不在 jsdom 渲染 Sigma。
- 单测覆盖:
  - `relationLabel`:已知键返回中文;未知键回退原文;空串安全。
  - `nodeColor`:游戏与机制颜色不同;未知类型返回非空回退色(迁移现有断言)。
  - `nodeSize`:degree 越大尺寸越大并被 clamp;焦点节点更大。
  - `isDowngraded` / `edgeColor` / `edgeSize`:低置信度→琥珀且更细;高/中置信度→对应色与正常线宽。
- 画布组件本身不写渲染测试(与现有 `graph-canvas.test.tsx` 只测 `nodeColor` 的策略一致)。
- 验收基线:`npm test` 全绿;`npm run lint` 无错;`npm run build` 通过(确保动态导入与 SSR 配置正确)。

## 10. 风险与缓解

- **`@react-sigma/*` 与 React 19 / Next 16 兼容性**:用 ref/hook 方式集成,遇到峰值问题时退回直接用 `sigma` 本体在 `useEffect` 中初始化(API 同源,风险可控)。
- **曲线边 + 箭头程序注册**:`@sigma/edge-curve` 需在 `SigmaContainer` settings 里注册 `edgeProgramClasses`;若集成困难,降级为直线箭头(`type: "arrow"`),不影响核心可读性目标。
- **构建期 WebGL/window 访问**:由 `ssr:false` 动态导入兜底;`npm run build` 作为门禁验证。

## 11. 非目标(YAGNI)

- 不做时间轴/历史回放、不做节点搜索框增强、不做导出图片、不做 3D。
- 不引入后端图布局或分页。
- 不为大规模(数千节点)做额外优化——当前为有界子图(≤ ~150 节点)。
