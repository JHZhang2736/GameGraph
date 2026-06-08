# 知识图谱画布迁移到 Sigma.js Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把前端知识图谱画布从 React Flow 换成 Sigma.js(WebGL),实现贴近 Neo4j Browser 的力导向、圆形节点、可拖拽缩放的图谱,同时完整保留现有数据流与交互。

**Architecture:** 视觉逻辑拆成可单测的纯函数模块(`relation-labels` / `node-style` / `edge-style`);`graph-canvas.tsx` 重写为 Sigma 容器 + 控制器组件,只消费上层传入的 `GraphData` 并通过 `onSelectNode/onSelectEdge` 回调;`page.tsx` 用 `next/dynamic`(`ssr:false`)引入画布以避开 SSR/构建预渲染阶段的 WebGL/window 访问。后端零改动。

**Tech Stack:** Next.js 16.2.7 (App Router, Turbopack) · React 19 · Sigma.js v3 · graphology · `@react-sigma/core` · `@react-sigma/layout-forceatlas2` · `@sigma/edge-curve` · Vitest + RTL。

**工作目录:** 所有命令在 `D:/Files/GameGraph/.claude/worktrees/sigma-graph/frontend` 下执行(分支 `feat/graph-sigma-canvas`)。

**关键约束(实现前必读):**
- 本项目 Next.js 行为偏离常规(见 `frontend/AGENTS.md`)。已核实:`next/dynamic` 的 `ssr:false` **只能用在 Client Component 内**;`graph/page.tsx` 已是 `"use client"`,满足条件。
- Sigma 依赖 WebGL,jsdom 跑不了——**只对纯函数写单测,不在 jsdom 渲染 Sigma 画布**。画布正确性由 `npm run build` + 手动 `npm run dev` 验证。
- `GraphCanvas` 对外 props 契约保持 `{ graph, onSelectEdge?, onSelectNode? }` 不变。

**任务顺序的用意(保证每步中间态可编译/测试通过):** 先**只新增** Sigma 依赖、保留 React Flow;先把页面改成**动态导入**(此时画布仍是旧 React Flow,能正常 build/test);最后才**重写画布**为 Sigma 并卸载 `@xyflow/react`。`@xyflow/react` 的卸载推迟到画布不再 import 它的那一步,避免中间态构建失败。

**与 spec 的有意偏差(2 处):**
1. spec 6.1 提"焦点节点额外 +4"。`GraphData` 不带焦点标记,为保持 props 契约不变,节点尺寸**仅按 degree**——焦点天然连接最多故自然更大,不单独传 `focusId`。
2. spec 5 提到把 `graph-canvas.test.tsx` 改为从 `node-style` 导入;本计划改为**删除** `graph-canvas.test.tsx`(其唯一用途是测 `nodeColor`,已迁到 `node-style.test.ts`),并给 `graph-page.test.tsx` 增加画布 mock 以隔离 Sigma。

---

### Task 1: 新增 Sigma 技术栈依赖(暂不卸载 React Flow)

**Files:**
- Modify: `frontend/package.json`(由 npm 命令自动改写)

- [ ] **Step 1: 安装 Sigma 技术栈**

Run:
```bash
npm install sigma graphology graphology-layout-forceatlas2 @react-sigma/core @react-sigma/layout-forceatlas2 @sigma/edge-curve
```
Expected: 安装成功,`package.json` dependencies 出现上述 6 个包;`@xyflow/react` **仍保留**(画布重写后才卸载)。

- [ ] **Step 2: 记录实际导出名(供 Task 7 校准)**

Sigma 生态不同小版本的导出名/CSS 路径偶有差异。运行并记下结果:
```bash
node -e "console.log('edge-curve:', Object.keys(require('@sigma/edge-curve')))"
node -e "console.log('layout-fa2:', Object.keys(require('@react-sigma/layout-forceatlas2')))"
ls node_modules/@react-sigma/core/lib/style.css && echo "css-ok"
```
Expected: `edge-curve` 含曲线箭头程序(常见 `EdgeCurvedArrowProgram`,或 `EdgeCurveProgram`);`layout-fa2` 含 `useWorkerLayoutForceAtlas2`;`css-ok`。

- [ ] **Step 3: 确认现有测试全绿(尚未触碰源码)**

Run: `npm test`
Expected: 68 passed（React Flow 仍在,画布与页面测试照常)。

- [ ] **Step 4: Commit**

```bash
git add package.json package-lock.json
git commit -m "build: add Sigma.js graph stack (React Flow still present)"
```

---

### Task 2: 关系类型中文映射(`relation-labels.ts`)

**Files:**
- Create: `frontend/components/graph/relation-labels.ts`
- Test: `frontend/components/graph/relation-labels.test.ts`

- [ ] **Step 1: 写失败测试**

`frontend/components/graph/relation-labels.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { relationLabel } from "@/components/graph/relation-labels";

describe("relationLabel", () => {
  it("maps known structural relations to Chinese", () => {
    expect(relationLabel("HAS_MECHANIC")).toBe("具备机制");
    expect(relationLabel("DELIVERS_EXPERIENCE")).toBe("带来体验");
  });
  it("maps known claim relations to Chinese", () => {
    expect(relationLabel("reinforces")).toBe("强化");
  });
  it("falls back to the original string for unknown relations", () => {
    expect(relationLabel("MYSTERY_REL")).toBe("MYSTERY_REL");
  });
  it("is safe for empty input", () => {
    expect(relationLabel("")).toBe("");
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx vitest run components/graph/relation-labels.test.ts`
Expected: FAIL（无法解析 `relation-labels`）。

- [ ] **Step 3: 写最小实现**

`frontend/components/graph/relation-labels.ts`:
```ts
// 关系类型英→中映射(仅前端展示用,后端不变)。缺失键回退显示原始英文,不丢信息。
const RELATION_LABELS: Record<string, string> = {
  // 结构边类型
  HAS_MECHANIC: "具备机制",
  DELIVERS_EXPERIENCE: "带来体验",
  CLAIM: "论断",
  TAGGED: "标签",
  HAS_GENRE: "类型",
  HAS_ART_STYLE: "美术风格",
  // claim 的 relation 值
  reinforces: "强化",
  enables: "使能",
  tensions_with: "张力",
  requires: "需要",
  contrasts_with: "对比",
};

export function relationLabel(relation: string): string {
  return RELATION_LABELS[relation] ?? relation;
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `npx vitest run components/graph/relation-labels.test.ts`
Expected: PASS（4 tests）。

- [ ] **Step 5: Commit**

```bash
git add components/graph/relation-labels.ts components/graph/relation-labels.test.ts
git commit -m "feat(graph): Chinese relation-type labels with passthrough fallback"
```

---

### Task 3: 节点样式纯函数(`node-style.ts`),迁移 `nodeColor`

**Files:**
- Create: `frontend/components/graph/node-style.ts`
- Test: `frontend/components/graph/node-style.test.ts`
- Delete: `frontend/components/graph/graph-canvas.test.tsx`

- [ ] **Step 1: 写失败测试**

`frontend/components/graph/node-style.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { nodeColor, nodeSize } from "@/components/graph/node-style";

describe("nodeColor", () => {
  it("colors games and mechanics differently", () => {
    expect(nodeColor("Game")).not.toBe(nodeColor("Mechanic"));
  });
  it("falls back to a non-empty neutral color for unknown types", () => {
    expect(nodeColor("Genre")).toBeTruthy();
    expect(nodeColor("SomethingElse")).toBeTruthy();
  });
});

describe("nodeSize", () => {
  it("grows with degree", () => {
    expect(nodeSize(5)).toBeGreaterThan(nodeSize(1));
  });
  it("clamps to a minimum", () => {
    expect(nodeSize(0)).toBe(6);
  });
  it("clamps to a maximum", () => {
    expect(nodeSize(1000)).toBe(20);
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx vitest run components/graph/node-style.test.ts`
Expected: FAIL（无法解析 `node-style`）。

- [ ] **Step 3: 写最小实现**

`frontend/components/graph/node-style.ts`:
```ts
// 节点按类型上色,沿用迁移前的色板。
const NODE_COLORS: Record<string, string> = {
  Game: "#4f46e5",
  Mechanic: "#818cf8",
  PlayerAction: "#818cf8",
  PlayerDecision: "#818cf8",
  Experience: "#14b8a6",
  Concept: "#f87171",
  ReferenceTag: "#f59e0b",
};

const DEFAULT_NODE_COLOR = "#94a3b8";

export function nodeColor(nodeType: string): string {
  return NODE_COLORS[nodeType] ?? DEFAULT_NODE_COLOR;
}

// 节点半径按连接数(degree)增长并 clamp;焦点节点连接最多故自然最大。
export function nodeSize(degree: number): number {
  const raw = 6 + degree * 1.2;
  return Math.min(Math.max(raw, 6), 20);
}
```

- [ ] **Step 4: 删除旧的 canvas 测试文件**

Run:
```bash
git rm components/graph/graph-canvas.test.tsx
```
Expected: 文件删除（`nodeColor` 覆盖已迁到 node-style.test.ts;旧 `graph-canvas.tsx` 仍在、仍 import React Flow,本步不动它）。

- [ ] **Step 5: 运行测试确认通过**

Run: `npx vitest run components/graph/node-style.test.ts`
Expected: PASS（5 tests）。

- [ ] **Step 6: Commit**

```bash
git add components/graph/node-style.ts components/graph/node-style.test.ts components/graph/graph-canvas.test.tsx
git commit -m "feat(graph): node-style helpers (color + degree-based size)"
```

---

### Task 4: 边样式纯函数(`edge-style.ts`)

**Files:**
- Create: `frontend/components/graph/edge-style.ts`
- Test: `frontend/components/graph/edge-style.test.ts`

- [ ] **Step 1: 写失败测试**

`frontend/components/graph/edge-style.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { isDowngraded, edgeColor, edgeSize } from "@/components/graph/edge-style";
import type { GraphEdge } from "@/lib/data";

function edge(partial: Partial<GraphEdge>): GraphEdge {
  return {
    id: "e",
    source: "a",
    target: "b",
    relation: "HAS_MECHANIC",
    evidence: [],
    ...partial,
  };
}

describe("isDowngraded", () => {
  it("is true for low confidence", () => {
    expect(isDowngraded(edge({ confidence: "low" }))).toBe(true);
  });
  it("is true for weak or conflicting evidence", () => {
    expect(isDowngraded(edge({ quality_status: "weak_evidence" }))).toBe(true);
    expect(isDowngraded(edge({ quality_status: "conflicting" }))).toBe(true);
  });
  it("is false for high confidence with no quality issues", () => {
    expect(isDowngraded(edge({ confidence: "high" }))).toBe(false);
  });
});

describe("edgeColor", () => {
  it("uses amber for downgraded edges", () => {
    expect(edgeColor(edge({ confidence: "low" }))).toBe("#d97706");
  });
  it("uses green for high confidence", () => {
    expect(edgeColor(edge({ confidence: "high" }))).toBe("#16a34a");
  });
  it("differs between downgraded and high confidence", () => {
    expect(edgeColor(edge({ confidence: "low" }))).not.toBe(
      edgeColor(edge({ confidence: "high" })),
    );
  });
});

describe("edgeSize", () => {
  it("makes downgraded edges thinner than normal edges", () => {
    expect(edgeSize(edge({ confidence: "low" }))).toBeLessThan(
      edgeSize(edge({ confidence: "high" })),
    );
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx vitest run components/graph/edge-style.test.ts`
Expected: FAIL（无法解析 `edge-style`）。

- [ ] **Step 3: 写最小实现**

`frontend/components/graph/edge-style.ts`:
```ts
import type { GraphEdge } from "@/lib/data";

// 低置信度或弱/冲突证据 → 降级展示(琥珀 + 更细线,不用虚线)。
export function isDowngraded(edge: GraphEdge): boolean {
  return (
    edge.confidence === "low" ||
    edge.quality_status === "weak_evidence" ||
    edge.quality_status === "conflicting"
  );
}

const DOWNGRADED_COLOR = "#d97706"; // amber
const CONFIDENCE_COLOR: Record<string, string> = {
  high: "#16a34a",
  medium: "#71717a",
};
const DEFAULT_EDGE_COLOR = "#94a3b8";

export function edgeColor(edge: GraphEdge): string {
  if (isDowngraded(edge)) return DOWNGRADED_COLOR;
  if (edge.confidence && CONFIDENCE_COLOR[edge.confidence]) {
    return CONFIDENCE_COLOR[edge.confidence];
  }
  return DEFAULT_EDGE_COLOR;
}

export function edgeSize(edge: GraphEdge): number {
  return isDowngraded(edge) ? 1 : 2.5;
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `npx vitest run components/graph/edge-style.test.ts`
Expected: PASS（7 tests）。

- [ ] **Step 5: Commit**

```bash
git add components/graph/edge-style.ts components/graph/edge-style.test.ts
git commit -m "feat(graph): edge-style helpers (downgrade detection, color, width)"
```

---

### Task 5: 隔离页面测试与画布(给 `graph-page.test.tsx` 加 mock)

为什么:`graph-page.test.tsx` 会在 jsdom 里渲染 `GraphPage`,而 `GraphPage` 引用 `GraphCanvas`。画布换成 Sigma 后在 jsdom 会触碰 WebGL 崩溃。提前 mock 掉画布,让页面测试只验证页面逻辑(随机焦点、截断提示),与渲染引擎解耦。此步在画布仍是 React Flow 时进行,测试应保持通过。

**Files:**
- Modify: `frontend/app/(workbench)/graph/graph-page.test.tsx`(在两个已有 `vi.mock` 之后、`import GraphPage` 之前加一段)

- [ ] **Step 1: 加入画布 mock**

在 `frontend/app/(workbench)/graph/graph-page.test.tsx` 的现有 `vi.mock("@/lib/data", ...)` 块之后、`import GraphPage from ...` 之前,插入:
```ts
// 画布依赖 WebGL,在 jsdom 不可渲染;页面测试只关心页面逻辑,故 stub 掉画布。
vi.mock("@/components/graph/graph-canvas", () => ({
  GraphCanvas: () => null,
}));
```

- [ ] **Step 2: 运行页面测试确认仍通过**

Run: `npx vitest run "app/(workbench)/graph/graph-page.test.tsx"`
Expected: PASS（2 tests:随机焦点 + 截断提示）。

- [ ] **Step 3: Commit**

```bash
git add "app/(workbench)/graph/graph-page.test.tsx"
git commit -m "test(graph): stub graph canvas in page test to decouple from renderer"
```

---

### Task 6: 页面改用动态导入引入画布(此时画布仍是 React Flow)

**Files:**
- Modify: `frontend/app/(workbench)/graph/page.tsx:6`(import 行)

- [ ] **Step 1: 替换静态 import 为 next/dynamic**

把 `frontend/app/(workbench)/graph/page.tsx` 第 6 行:
```tsx
import { GraphCanvas } from "@/components/graph/graph-canvas";
```
替换为(放在文件顶部 import 区,`"use client"` 之下):
```tsx
import dynamic from "next/dynamic";

// 画布(后续将换成 Sigma)依赖 WebGL/window,禁用 SSR/构建预渲染。
// page 已是 Client Component,故 next/dynamic 的 ssr:false 在此合法
// (见 node_modules/next/dist/docs 的 lazy-loading 指南)。
const GraphCanvas = dynamic(
  () => import("@/components/graph/graph-canvas").then((m) => m.GraphCanvas),
  {
    ssr: false,
    loading: () => (
      <div className="h-[560px] animate-pulse rounded-lg border bg-muted/30" />
    ),
  },
);
```

- [ ] **Step 2: 构建 / lint / 测试确认全绿**

Run: `npm run build && npm run lint && npm test`
Expected: build 成功、lint 无 error、测试全绿(画布此刻仍是 React Flow,动态导入对其无副作用)。

- [ ] **Step 3: Commit**

```bash
git add "app/(workbench)/graph/page.tsx"
git commit -m "refactor(graph): dynamically import canvas with ssr disabled"
```

---

### Task 7: 用 Sigma 重写 `graph-canvas.tsx` 并卸载 React Flow

**Files:**
- Modify(重写): `frontend/components/graph/graph-canvas.tsx`
- Modify: `frontend/package.json`(卸载 `@xyflow/react`)

**实现说明:** 下面是完整组件代码。先按 Task 1 Step 2 记录的实际导出名核对三处:`@sigma/edge-curve` 的曲线箭头程序名、`@react-sigma/core` 的 CSS 路径、`useWorkerLayoutForceAtlas2`;若与代码中的名字不一致,按记录改对应 import 行,其余逻辑不变。

- [ ] **Step 1: 重写组件**

`frontend/components/graph/graph-canvas.tsx`（整文件替换）:
```tsx
"use client";

import { useEffect, useState } from "react";
import Graph from "graphology";
import {
  SigmaContainer,
  useLoadGraph,
  useRegisterEvents,
  useSetSettings,
  useSigma,
} from "@react-sigma/core";
import { useWorkerLayoutForceAtlas2 } from "@react-sigma/layout-forceatlas2";
import { EdgeCurvedArrowProgram } from "@sigma/edge-curve";
import "@react-sigma/core/lib/style.css";
import type { GraphData } from "@/lib/data";
import { nodeColor, nodeSize } from "@/components/graph/node-style";
import { edgeColor, edgeSize } from "@/components/graph/edge-style";
import { relationLabel } from "@/components/graph/relation-labels";

const DIMMED_NODE = "#e2e8f0";
const DIMMED_EDGE = "#eef2f7";

// 由边列表统计每个节点的连接数,用于节点尺寸。
function degreeMap(graph: GraphData): Map<string, number> {
  const m = new Map<string, number>();
  for (const e of graph.edges) {
    m.set(e.source, (m.get(e.source) ?? 0) + 1);
    m.set(e.target, (m.get(e.target) ?? 0) + 1);
  }
  return m;
}

const SIGMA_SETTINGS = {
  renderEdgeLabels: true,
  defaultEdgeType: "curved",
  edgeProgramClasses: { curved: EdgeCurvedArrowProgram },
  labelDensity: 0.07,
  labelGridCellSize: 60,
  zIndex: true,
};

function GraphController({
  graph,
  onSelectNode,
  onSelectEdge,
}: {
  graph: GraphData;
  onSelectNode?: (id: string) => void;
  onSelectEdge?: (id: string) => void;
}) {
  const sigma = useSigma();
  const loadGraph = useLoadGraph();
  const registerEvents = useRegisterEvents();
  const setSettings = useSetSettings();
  const { start, kill } = useWorkerLayoutForceAtlas2({
    settings: { slowDown: 10 },
  });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // 数据变化时(挂载 / 展开邻居)重建 graphology 图并重跑布局。
  useEffect(() => {
    const g = new Graph({ multi: true, type: "directed" });
    const degrees = degreeMap(graph);
    const count = Math.max(graph.nodes.length, 1);
    graph.nodes.forEach((n, i) => {
      g.addNode(n.id, {
        label: n.label,
        size: nodeSize(degrees.get(n.id) ?? 0),
        color: nodeColor(n.node_type),
        // 环形播种初始坐标,交给 FA2 收敛。
        x: Math.cos((i / count) * 2 * Math.PI),
        y: Math.sin((i / count) * 2 * Math.PI),
      });
    });
    graph.edges.forEach((e) => {
      if (!g.hasNode(e.source) || !g.hasNode(e.target)) return;
      if (g.hasEdge(e.id)) return;
      g.addEdgeWithKey(e.id, e.source, e.target, {
        label: relationLabel(e.relation),
        type: "curved",
        color: edgeColor(e),
        size: edgeSize(e),
      });
    });
    loadGraph(g);
    start();
    return () => kill();
  }, [graph, loadGraph, start, kill]);

  // 注册交互:点击展开 / 看证据,hover 记录,拖拽。
  useEffect(() => {
    let dragged: string | null = null;
    registerEvents({
      clickNode: (e) => onSelectNode?.(e.node),
      clickEdge: (e) => onSelectEdge?.(e.edge),
      enterNode: (e) => setHoveredNode(e.node),
      leaveNode: () => setHoveredNode(null),
      downNode: (e) => {
        dragged = e.node;
        sigma.getGraph().setNodeAttribute(dragged, "highlighted", true);
      },
      mousemovebody: (e) => {
        if (!dragged) return;
        const pos = sigma.viewportToGraph(e);
        sigma.getGraph().setNodeAttribute(dragged, "x", pos.x);
        sigma.getGraph().setNodeAttribute(dragged, "y", pos.y);
        e.preventSigmaDefault();
        e.original.preventDefault();
        e.original.stopPropagation();
      },
      mouseup: () => {
        if (dragged) sigma.getGraph().removeNodeAttribute(dragged, "highlighted");
        dragged = null;
      },
    });
  }, [registerEvents, sigma, onSelectNode, onSelectEdge]);

  // hover 高亮:淡化非邻居节点;默认隐藏边标签,仅在 hover 焦点的相连边上显示。
  useEffect(() => {
    setSettings({
      nodeReducer: (node: string, data: Record<string, unknown>) => {
        if (!hoveredNode) return data;
        const g = sigma.getGraph();
        if (node === hoveredNode || g.areNeighbors(hoveredNode, node)) return data;
        return { ...data, color: DIMMED_NODE, label: "" };
      },
      edgeReducer: (edge: string, data: Record<string, unknown>) => {
        const g = sigma.getGraph();
        if (!hoveredNode) return { ...data, label: "" };
        const [s, t] = g.extremities(edge);
        if (s === hoveredNode || t === hoveredNode) return data;
        return { ...data, color: DIMMED_EDGE, label: "" };
      },
    });
  }, [hoveredNode, setSettings, sigma]);

  return null;
}

export function GraphCanvas({
  graph,
  onSelectEdge,
  onSelectNode,
}: {
  graph: GraphData;
  onSelectEdge?: (edgeId: string) => void;
  onSelectNode?: (nodeId: string) => void;
}) {
  return (
    <div className="h-[560px] rounded-lg border">
      <SigmaContainer
        style={{ height: "100%", width: "100%" }}
        settings={SIGMA_SETTINGS}
      >
        <GraphController
          graph={graph}
          onSelectNode={onSelectNode}
          onSelectEdge={onSelectEdge}
        />
      </SigmaContainer>
    </div>
  );
}
```

- [ ] **Step 2: 卸载 React Flow(画布已不再 import 它)**

Run:
```bash
npm uninstall @xyflow/react
```
Expected: `package.json` 不再含 `@xyflow/react`。

- [ ] **Step 3: 构建确认**

Run: `npm run build`
Expected: 构建成功。若报 `EdgeCurvedArrowProgram` 等导出名不存在,按 Task 1 Step 2 记录改 import 名后重跑;若报 reducer 类型不符,以 `@react-sigma/core` 的 `Settings` 类型为准微调签名(逻辑不变)。

- [ ] **Step 4: 运行全部单测**

Run: `npm test`
Expected: 全绿(画布无单测;页面测试已 mock 画布;纯函数测试不受影响)。

- [ ] **Step 5: Commit**

```bash
git add components/graph/graph-canvas.tsx package.json package-lock.json
git commit -m "feat(graph): render knowledge graph with Sigma.js (force layout, curved labeled edges, drag, hover highlight)"
```

---

### Task 8: 验收门禁 + 手动验证

**Files:** 无（仅运行与人工核对)

- [ ] **Step 1: 全套自动门禁**

Run:
```bash
npm test && npm run lint && npm run build
```
Expected: 测试全绿;lint 无 error;build 成功。

- [ ] **Step 2: 手动验证(连本地后端)**

确认后端在 `:8000` 可达(F5 或 docker),然后:
```bash
npm run dev
```
浏览器开 http://localhost:3000 进入"知识图谱",逐项核对:
- 进入时随机焦点已加载,节点呈圆形、按类型上色、力导向散开(不再是死板圆环)。
- 🎲 换一个能切换焦点。
- 点节点 → 展开其邻居(新节点加入并重新收敛)。
- hover 节点 → 邻居高亮、其余淡化,相连边上显示中文关系标签(如"具备机制")。
- 点边 → 右侧证据面板出现,置信度/质量徽章正常。
- 低置信度/弱证据边为琥珀色细线(非虚线)。
- 可拖动单个节点、滚轮缩放、空白处平移。
- 截断时顶部琥珀提示仍出现。

- [ ] **Step 3: 收尾**

确认无未提交改动:
```bash
git status --short
```
Expected: 干净。若 dev 期间产生本地改动,审阅后再决定是否提交。

---

## 完成后

全部任务完成并通过验收后,使用 **superpowers:finishing-a-development-branch** 收尾(合并 / 开 PR / 保留 / 丢弃)。注意 CLAUDE.local.md 要求:开 PR 前先确认 `main` 进度是否同步,以免冲突。
