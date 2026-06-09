# 6.6 机会框架模块（前端）设计

**目标：** 让用户在 `/match`（6.5 机会匹配）选中的候选机会区域，经后端 `POST /opportunity/frame` 展开为机会框架，并在 `/opportunities` 以「框架历史」列表（最新生成 + 历史保留）呈现。

**架构一句话：** 在 `/match` 候选卡就地生成框架并把结果落 localStorage 历史，`/opportunities` 退化为纯历史读取页（手风琴卡列表）。

**技术栈：** Next.js 16 / React / TanStack Query（`useMutation`）/ localStorage + `useSyncExternalStore` / vitest + Testing Library。

---

## 1. 现状与缺口

- **6.5 前端已完成**：`/match` 页点「匹配机会」→ `POST /opportunity/match` → 渲染候选卡（`OpportunityCandidateCard`）、警告、被拒方向。候选卡当前**没有任何「生成/选中」动作**。
- **6.6 前端仍是 mock**：`/opportunities`（导航名「机会框架」）用 `useOpportunityFrame()` → `getOpportunityFrame()` 返回 `goldenFlow.opportunity_frame` 静态数据，渲染单个框架，无输入、未连后端。
- **后端 6.6 已就绪**：`POST /opportunity/frame`，请求体 `{ profile: DeveloperProfile, area: OpportunityArea }`，返回 `OpportunityFrame`。框架 `id = "frame|" + area.id`（`opportunity_frame_service.py:124`），完全由 area 决定，故确定性、可按 id 去重。

**两个契约缺口（本次修复）：**

1. 后端 `OpportunityFrame` 已含 `warnings: list[str]`，但前端 `OpportunityFrame` 类型缺 `warnings` → 补 `warnings?: string[]` 并渲染。
2. 6.6 设计约定 `recommended_transformations[0]` 恒为「主变形」，前端当前把推荐变形平铺为 `<ul>`，主变形不可辨 → 展开区显式区分「主变形 / 次变形」。

## 2. 数据流（方案 A2）

```
/match 候选卡 ──「生成机会框架」──▶ POST /opportunity/frame {profile, area}
   (按钮 isPending 就地 loading；失败就地报错、不跳转、不写历史)
                                              │ 成功
                                              ▼
        upsertFrame(frame)  ── localStorage，按 frame.id 去重 + move-to-front
        rememberLastFrameId(frame.id)  ── sessionStorage，一次性「刚生成」标记
                                              │
                                              ▼  router.push("/opportunities")
/opportunities ── loadFrames() 纯读历史 ──▶ 手风琴卡列表（最新在上）
                  takeLastFrameId() 决定哪条自动展开 + 高亮（读后清空）
```

- **画像来源**：沿用 `useDeveloperProfile()`（localStorage 已确认画像 → 否则 golden-flow 兜底）。无已确认画像时生成按钮仍可用，与 `/match` 现状一致。
- **去重**：同一 area 重复生成 → 同一 `frame.id` → 原地替换并置顶，不产生重复条目。
- **持久化**：框架历史用 localStorage（跨会话保留，才是真「历史」）；「刚生成」标记用 sessionStorage（仅本次导航有效）。

## 3. 文件清单

### 新增

**`lib/opportunity/frame-history.ts`** — 框架历史 store，仿 `lib/profile/storage.ts` 的 `useSyncExternalStore` 写法。

- `loadFrames(): OpportunityFrame[]` — 读 localStorage（key `gamegraph.opportunity-frames`），最新在前；无 window / 解析失败 → `[]`。按 raw 字符串缓存快照引用，避免 `useSyncExternalStore` 无限重渲染。
- `subscribeFrames(onChange): () => void` — 监听 `storage` 事件（跨标签同步），返回退订函数。
- `upsertFrame(frame: OpportunityFrame): void` — 按 `frame.id` 去重；存在则替换，统一 move-to-front；写回 localStorage。
- `removeFrame(id: string): void` — 删除一条，写回。
- `rememberLastFrameId(id: string): void` / `takeLastFrameId(): string | null` — sessionStorage（key `gamegraph.last-frame-id`），`take` 读后清空。
- 所有写操作 `typeof window === "undefined"` 时 no-op（SSR 安全）。

**`components/opportunity/opportunity-frame-card.tsx`** — 手风琴卡。

- props：`{ frame: OpportunityFrame; defaultOpen?: boolean; highlighted?: boolean; onRemove?: (id: string) => void }`。
- 折叠态：`opportunity_area` 作标题 + 主变形 `recommended_transformations[0]` 徽章；右侧「移除」按钮（有 `onRemove` 时）。
- 展开态：复用现 `opportunities/page.tsx` 的完整框架布局——相关机制 / 玩家体验 / 制作约束 / 创新模式（chips）、来源游戏、推荐变形（`[0]` 标「主变形」徽章、其余「次变形」）、禁止方向（红框）、适配理由、风险理由、证据路径；`warnings` 非空时显示警告条。
- 开合用本地 `useState`，`defaultOpen` 决定初值。

### 改动

**`lib/types/index.ts`** — `OpportunityFrame` 接口补 `warnings?: string[]`（对齐后端，置于 `risk_reason` 之后）。

**`lib/data/index.ts`**
- 新增 `buildOpportunityFrame(profile: DeveloperProfile, area: OpportunityArea): Promise<OpportunityFrame>`，`POST ${apiBase()}/opportunity/frame`，body `{ profile, area }`，非 2xx 抛 `Error("POST /opportunity/frame responded " + status)`。
- 删除 `getOpportunityFrame`（重写后无引用）。

**`lib/queries/index.ts`**
- 新增 `useBuildOpportunityFrame()` → `useMutation({ mutationFn: ({ profile, area }) => buildOpportunityFrame(profile, area) })`。
- 删除 `useOpportunityFrame` 及对 `getOpportunityFrame` 的 import。

**`components/opportunity/opportunity-candidate-card.tsx`**
- 新增 props `{ onGenerate: (area: OpportunityArea) => void; isGenerating?: boolean }`。
- 卡片底部加「生成机会框架」按钮：`onClick={() => onGenerate(area)}`；`isGenerating` 时禁用并显示「生成中…」。

**`app/(workbench)/match/page.tsx`**
- 持有 `useBuildOpportunityFrame` 与 `useRouter()`（`next/navigation`）。
- 记录当前正在生成的 area id（区分多张卡的 pending 态）。
- 给每张候选卡传 `onGenerate`：调 `buildFrame.mutate({ profile, area })`，`onSuccess(frame)` → `upsertFrame(frame)` + `rememberLastFrameId(frame.id)` + `router.push("/opportunities")`；`onError` → 就地错误提示（不跳转）。

**`app/(workbench)/opportunities/page.tsx`** — 重写为历史读取页。
- 用 `useSyncExternalStore(subscribeFrames, loadFrames, () => [])` 读历史。
- 挂载时 `takeLastFrameId()` 得到刚生成 id，用于该条 `defaultOpen + highlighted`。
- 历史为空 → 空态「还没有机会框架，先去机会匹配选一个方向。」（可链接 `/match`）。
- 否则渲染 `OpportunityFrameCard` 列表（最新在上），`onRemove={removeFrame}`。

## 4. 错误处理

- 生成时 LLM / 网络失败：候选卡按钮就地报错（红字或复用 `view-states` 的提示），**不跳转、不写历史**，用户可重试。
- `/opportunities` 直接进入且无历史：空态引导回 `/match`。
- localStorage 解析失败：`loadFrames` 吞错返回 `[]`，等同空历史。

## 5. 测试（TDD）

- **`lib/opportunity/frame-history.test.ts`**：`upsertFrame` 新增 / 同 id 替换置顶 / 多条顺序；`removeFrame`；`takeLastFrameId` 读后清空；SSR 安全（无 window 不抛）。
- **`lib/data`（并入现有 data 测试或新建）**：`buildOpportunityFrame` 发对 URL + body、解析响应、非 2xx 抛错（mock `fetch`）。
- **`components/opportunity/opportunity-candidate-card`（扩充现有测试）**：渲染「生成机会框架」按钮、点击触发 `onGenerate(area)`、`isGenerating` 时禁用。
- **`components/opportunity/opportunity-frame-card.test.tsx`**：折叠摘要含 `opportunity_area` 与主变形；展开后见「禁止方向」；主 / 次变形区分；`warnings` 渲染。
- **`app/(workbench)/match/page.test.tsx`（扩充）**：点生成 → 调 build → 成功后写历史 + `router.push("/opportunities")`（mock router 与 data fn）。
- **`app/(workbench)/opportunities/opportunities-page.test.tsx`（重写）**：空态文案；预置历史时渲染框架卡；`takeLastFrameId` 命中的条目默认展开。

## 6. 非目标（YAGNI）

- 候选卡不另做「选中态」：点「生成机会框架」即生成并跳转。
- 框架不做服务端持久化 / 多设备同步：仅浏览器 localStorage。
- 不做框架编辑、排序、分组、搜索；历史只有 upsert / remove。
- 不接 6.7（概念生成）；框架卡不加「下一步」动作。

## 7. 实现注意

- **Next 16 破坏性变更**：按 `frontend/AGENTS.md`，写代码前读 `node_modules/next/dist/docs/` 对应指南；`useRouter` 来自 `next/navigation`（项目已用 `usePathname` / `redirect`，同源）。
- **vitest 在本环境**：用 `npx vitest run --pool=threads`，默认 `forks` pool 在 Windows 上 teardown 崩溃（基线既有噪声，非真失败）。
