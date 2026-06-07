# 前端工作台设计 Spec

## 1. 目的

本文档定义独立游戏创意图谱系统的第一版前端:一个基于 Next.js App Router 的**工作台**应用,按系统的功能与数据模型呈现各核心产物。

第一版只搭前端框架与基础页面设计。它不接入真实后端 API、不连接 Neo4j、不调用 LLM、不做用户登录或多用户。它的目标是先把工作台的结构、导航、数据契约和各产物视图立起来,用本地确定性 mock 数据驱动,使后端 API 就绪后能以最小改动接入。

本文档与以下文档配套:

- 产品设计:`2026-06-07-indie-game-idea-graph-design.zh-CN.md`
- 技术栈:`2026-06-07-technical-stack-design.zh-CN.md`
- 后端 fixture 契约:`2026-06-08-backend-fixture-contract-design.zh-CN.md`

## 2. 范围

### 范围内

- 建立 `frontend/` 目录作为前端代码根目录。
- Next.js App Router + React + TypeScript 项目骨架。
- Tailwind CSS + shadcn/ui + Radix + lucide-react 的主题与基础组件。
- 工作台外壳:侧边栏分组导航 + 顶栏 + 主内容区(布局 B,master-detail)。
- 七个核心产物的**只读**视图,外加一个总览页。
- 镜像后端产物 schema 的 TypeScript 类型。
- 本地 typed fixture(镜像后端 `golden_flow.json`)。
- 数据访问层 + TanStack Query hooks,带真实的加载/错误/空状态。
- 用 Vitest + React Testing Library 验证关键视图与降级展示规则。

### 范围外

- 用户登录、账号、权限、多用户。
- 真实后端 API、SSE/轮询真实接入(只预留接入点)。
- 交互式表单提交(画像录入、游戏入库的写操作);第一版表单字段以只读展示为主。
- Neo4j、LLM、服务端数据获取(SSR/RSC 取数)。
- 大型全局状态库(Redux 等)。
- Playwright 端到端冒烟测试(留到 UI 稳定后)。
- 概念评估的完整评分算法(前端仅展示 mock 评分)。

## 3. 设计原则

### 3.1 工作台,而非营销页

界面应像高效的专业工具(参考 Linear / shadcn 后台),信息密度优先,视觉规则保持局部、克制。

### 3.2 数据来源单点可替换

只有 `lib/data/` 接触"数据从哪来"。页面只消费 `lib/queries/` 的 hooks。将来把数据访问层内部从读 fixture 改为 `fetch(API)`,页面与组件零改动。

### 3.3 前端不承载推理逻辑

按技术栈 spec,前端不做图谱遍历、prompt 逻辑、概念评分、证据路径组装或产物权威校验。这些都属于后端。前端只负责呈现、浏览、解释与对比。

### 3.4 证据/置信度/质量状态全程可见

证据、置信度和质量状态必须在任何呈现它们的视图中一致展示。低置信度/弱证据材料必须明显降级,不得被呈现为高置信度事实。

## 4. 技术栈

遵循技术栈 spec §3:

- 框架:Next.js App Router、React、TypeScript
- UI:Tailwind CSS、shadcn/ui、Radix UI primitives、lucide-react
- 服务端状态:TanStack Query
- 选择/筛选状态:URL 状态(query params / 路由段)
- 图谱可视化:React Flow
- 测试:Vitest + React Testing Library

## 5. 目录结构

```text
frontend/
  app/
    layout.tsx                  # 根布局:字体、globals、Providers(TanStack Query)
    globals.css
    page.tsx                    # 重定向到 /overview
    (workbench)/
      layout.tsx                # 工作台外壳:侧边栏 + 顶栏
      overview/page.tsx         # 总览
      games/page.tsx            # 游戏入库:种子游戏列表
      games/[id]/page.tsx       # 游戏设计档案 + 设计论断
      graph/page.tsx            # 知识图谱(React Flow)
      profile/page.tsx          # 开发者画像
      opportunities/page.tsx    # 机会框架
      concepts/page.tsx         # 概念卡对比 + 评估
      prototype/page.tsx        # 原型验证简报
  components/
    ui/                         # shadcn/ui primitives
    shell/                      # AppSidebar、TopBar、NavGroup、TaskProgress
    artifacts/                  # ConfidenceBadge、QualityBadge、EvidenceList、ClaimRow、ConstraintTag、ArtifactCard
    graph/                      # GraphCanvas 及 React Flow 节点/边/详情侧栏
  lib/
    types/                      # 镜像后端产物的 TS 类型
    fixtures/                   # golden-flow.ts(typed)
    data/                       # 数据访问层:getXxx() 异步函数
    queries/                    # TanStack Query hooks:useXxx()
    utils.ts
  components.json
  next.config.ts
  tailwind / postcss 配置
  tsconfig.json
  vitest.config.ts
```

说明:

- 路由直接对应 spec 的 7 个产物视图,外加 `overview` 总览页。
- 不含任何登录/账号/权限路由。
- 图谱视图与概念对比为可占满主区域的全宽视图。

## 6. 数据模型与类型

`lib/types/` 严格镜像后端 fixture 契约的产物 schema,字段名与 `golden_flow.json` 一致。

### 6.1 共享类型

- `ConfidenceLevel`:`low` | `medium` | `high`
- `QualityStatus`:`draft` | `reviewed` | `weak_evidence` | `conflicting`
- `ConstraintType`:`hard` | `strong_preference` | `soft_preference`
- `EvidenceRef`:`title`、可选 `url`、可选 `quote_or_summary`、`notes`

### 6.2 核心产物类型(镜像后端)

- `SeedGame`
- `DesignClaim`
- `GraphRelation`
- `DeveloperConstraint`
- `DeveloperProfile`
- `OpportunityFrame`
- `ConceptCard`
- `PrototypeBrief`
- `GoldenFlow`:整体形状,等价于后端 `FixturePipelineResult`,含 `graph_relations`

### 6.3 前端补充类型

后端 fixture 契约第一版未实现完整 `GameDesignProfile` 与 `ConceptEvaluation`,但产品 spec(§5.2、§5.7)定义了它们,且"游戏设计档案"与"概念评估/对比"视图需要它们。因此前端先定义轻量 mock 形状,并在类型注释中明确标注"待后端落地后对齐":

- `GameDesignProfile`:一句话总结、核心循环、玩家主要行动/决策、主要体验、主要机制、参考价值标签、不可复制风险、证据说明、置信度、质量状态。
- `ConceptEvaluation`:适配度、可行性、新颖度、风险、证据质量评分,以及分类(`safe` 稳妥 | `balanced` 平衡 | `challenging` 挑战)。

## 7. 数据访问层与数据获取

### 7.1 Fixtures

`lib/fixtures/golden-flow.ts` 把后端 `golden_flow.json` 的内容做成 typed 常量(Balatro / Into the Breach / Baba Is You → Ruleforge Tactics 的完整流程),并补充若干 `GameDesignProfile` 与 `ConceptEvaluation` mock。

fixture 有意保留:

- 至少一条高置信度论断。
- 至少一条低置信度 / 弱证据论断,用于验证 UI 降级展示。

### 7.2 数据访问层

`lib/data/` 中每类数据一个异步函数,内部 `await` 一个极短延迟再返回 fixture,模拟网络往返:

```text
getGoldenFlow(): Promise<GoldenFlow>
getSeedGames(): Promise<SeedGame[]>
getGameProfile(id): Promise<{ game, profile, claims }>
getGraph(): Promise<{ nodes, edges }>     // 由 graph_relations 派生
getDeveloperProfile(): Promise<DeveloperProfile>
getOpportunityFrame(): Promise<OpportunityFrame>
getConcepts(): Promise<{ cards, evaluations }>
getPrototypeBrief(): Promise<PrototypeBrief>
```

将来只需把这些函数体改为 `fetch(...)`,签名保持不变。

### 7.3 Query hooks

`lib/queries/` 对每个 data 函数封装一个 TanStack Query hook(如 `useGoldenFlow()`、`useGameProfile(id)`)。页面只用 hooks,天然获得 loading / error / empty 状态。

## 8. 工作台外壳与导航

`components/shell/`:

- **侧边栏**:两组导航。
  - 资料库:游戏入库 / 设计档案 / 知识图谱
  - 创意流程:开发者画像 / 机会框架 / 概念卡 / 原型简报
  - 底部:总览
- **顶栏**:面包屑 + 全局 `TaskProgress` 组件。`TaskProgress` 读 mock 进度,并预留 SSE/轮询接入点;第一版显示"已完成"。
- **主题**:中性配色(shadcn neutral)+ 靛蓝点缀,默认浅色,预留深色。信息密度偏紧凑。

## 9. 视图设计

全部为只读视图,数据来自第 7 节的 query hooks。

1. **总览** `overview`:核心流程进度 + 各产物计数概览,作为进入各视图的入口。
2. **游戏入库** `games`:种子游戏表格(标题 / 简述 / 选择理由 / 来源数),来源引用可展开。
3. **游戏设计档案** `games/[id]`:档案字段 + 参考价值标签 + 设计论断列表(每条带证据、`ConfidenceBadge`、`QualityBadge`)。
4. **知识图谱** `graph`:React Flow 画布,节点为主体/客体,边为关系;边按置信度降级着色;点击边在右侧详情栏显示来源论断与证据路径。
5. **开发者画像** `profile`:能力/预算字段 + 约束分区(硬性约束高亮、强偏好、软偏好)+ 喜欢/讨厌的参考。
6. **机会框架** `opportunities`:机会区域、来源游戏、推荐变形、禁止方向(醒目展示)、证据路径(可点回图谱/论断)、适配理由与风险理由。
7. **概念卡对比** `concepts`:概念卡并排,展示与参考作品的差异、制作风险、设计风险;`ConceptEvaluation` 评分与分类(稳妥/平衡/挑战)。
8. **原型验证简报** `prototype`:最大风险假设、最小原型范围、目标试玩时长、成功信号、失败信号、暂时不要做什么。

## 10. 可复用产物组件

`components/artifacts/` 提供跨视图复用的组件,确保证据/置信度/质量状态在任何位置呈现一致:

- `ConfidenceBadge`:按 `ConfidenceLevel` 着色(高=绿、中=中性、低=琥珀)。
- `QualityBadge`:展示 `QualityStatus`,弱证据/冲突态明显降级。
- `EvidenceList`:渲染 `EvidenceRef[]`,区分 URL 来源与引用/摘要。
- `ClaimRow`:一条设计论断,组合上述徽章与证据。
- `ConstraintTag`:按 `ConstraintType` 区分硬性约束/强偏好/软偏好。
- `ArtifactCard`:统一的产物卡片容器。

## 11. 状态处理

- **加载**:`isLoading` → 各视图用 shadcn `Skeleton` 占位。
- **错误**:`isError` → 内联错误卡片 + 「重试」按钮(调用 `refetch`)。
- **空状态**:产物无数据时显示明确空态文案。
- **任务进度**:`TaskProgress` 读 mock 进度,预留 SSE/轮询接入点。

## 12. 测试策略

遵循技术栈 spec §7.1,使用 Vitest + React Testing Library。

- **组件测试**:覆盖优先视图 —— 开发者画像、游戏设计档案、图谱解释、机会框架、概念对比。
- **集成测试**:mock `lib/data/` 层,断言 query hook 驱动的视图正确渲染数据以及 loading/error 态。
- **降级展示断言**(把业务规则变成测试):
  - 低置信度论断渲染出弱证据/降级标记,不被当成高置信度。
  - 机会框架的禁止方向可见。
  - 概念卡显示与参考作品的差异 + 制作/设计风险。
  - 原型简报同时包含成功信号与失败信号。
- **冒烟**:最小测试确认各路由页面能渲染不报错。
- Playwright 端到端按 spec 留到 UI 稳定后,不在本次范围。

## 13. 成功标准

这一步成功,如果:

- `frontend/` 有清晰的 Next.js App Router 工作台骨架。
- 七个产物视图 + 总览页均可由本地 mock 数据渲染,并可在工作台内自由导航。
- 数据访问层是数据来源的唯一接触点,页面只依赖 query hooks。
- 证据、置信度、质量状态在各视图一致呈现,低置信度材料明显降级。
- 机会框架的禁止方向、概念与参考的差异、原型简报的成功/失败信号都被清晰展示。
- 关键视图与降级展示规则有 Vitest 测试守护。

这一步失败,如果:

- 前端开始承载图谱遍历、评分或证据路径组装等后端逻辑。
- 页面直接耦合 fixture,导致将来接真 API 需逐页重写取数。
- 低置信度论断被呈现为高置信度事实。
- 第一版提前引入登录、真实 LLM/Neo4j 或大型全局状态库,导致骨架变重。

## 14. 后续扩展方向

1. 把数据访问层内部从 fixture 切换为真实后端 REST API(签名不变)。
2. 接入 SSE/轮询,让 `TaskProgress` 展示真实长任务进度。
3. 为画像录入、游戏入库等加入交互式表单与写操作。
4. 加入 Playwright 端到端冒烟测试覆盖主流程。
5. 随后端 `GameDesignProfile` / `ConceptEvaluation` 落地,用真实 schema 替换前端 mock 形状。
