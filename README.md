# GameGraph

独立游戏创意发现系统：把精选种子游戏当设计样本 → 提取设计知识进知识图谱 → 结合开发者画像 → 找有据可依的机会 → 生成可比较的概念 → 给出原型验证简报。后端 FastAPI + Neo4j，前端 Next.js。核心原则「先有证据，再生成」。

## 核心抽象：功能角色 → 协同规则 → 体验

理解本项目最重要的一层（机会生成的引擎）：

```
机制/题材/手感/类型（受控词表）
   └─分类─▶ 功能角色 FunctionalRole（20 个，元素的内在职责，如 高方差失败源/社交放大器）
              └─配对─▶ 协同规则 SynergyRule（roleA × roleB → 预测体验）
                          └─产出─▶ 体验（欢乐混乱/战斗精通/…）= 开发者可靶向的目标
```

- 角色由**核心四段**（Mechanic / GameFeel / Theme / Genre）推导，**不进图谱**，待在旁路表
  `backend/app/fixtures/element_roles.json`（一词一角色一维度）。
- 机会生成（`opportunity_service.enumerate_opportunities`）从开发者**期望体验**出发 → 反查协同规则得角色配方 → 在图谱里实例化为带 `SynergyRationale` 的候选；**讨厌体验**对应的规则不生成。
- 关键文件：`backend/app/services/synergy.py`、`backend/app/fixtures/{element_roles,synergy_rules}.json`、`backend/app/services/opportunity_service.py`。

## 如何扩展可生成的「体验」

系统只瞄准「我们有配方能造出来」的体验——即**当前协同规则能产出的 distinct experience**（前端「期望/讨厌体验」多选直接来自后端 `GET /synergy/experiences`，**加规则前端自动更新，无需改前端**）。按成本从低到高：

### 1）加一条协同规则（最常用，纯数据）
编辑 `backend/app/fixtures/synergy_rules.json`，加一行：
```json
{"id": "<唯一id>", "role_a": "<已有角色>", "role_b": "<已有角色>", "experience": "<目标体验>",
 "evidence_games": ["game_xxx", "game_yyy"]}
```
- `experience` 取自受控体验词表（`.claude/skills/researching-games-for-import/preferred-terms.md` 的「体验」段）。
- 这同时新增了「一类机会模式」**和**「一个可选体验」。角色通常已存在于 20 个里。
- `role_a × role_b` 这一对在表内须唯一；规则对称（顺序无关）。
- `evidence_games` 填库内印证该配方的代表作（文档/抽查用）。

### 2）加/调功能角色（较少，当现有 20 个角色凑不出某配方时）
- `backend/app/schemas/opportunity.py` 的 `FunctionalRole` 枚举加一项；
- `backend/app/fixtures/element_roles.json` 把承载该角色的受控词（机制/题材/手感/类型）归类进去（一词一角色一维度，load 时有守卫）；
- 再用它写协同规则（步骤 1）。

### 验证（扩展后必做）
- `cd backend && python -m pytest`（`test_synergy.py` 会校验「每个角色都被某规则覆盖」「规则可加载」；新体验自动进 `/synergy/experiences`）。
- 跑 `backend/tests/test_hybrid_validation.py` 的验证 harness（留一法/跨维度/画像靶向）。
- 给规则配 `evidence_games`，让领域人可抽查——这是「先有证据再生成」的要求。

## 开发约定

- 后端测试在 `backend/` 下跑：`cd backend && python -m pytest`。
- 前端测试：`cd frontend && npx vitest run`（本 Windows 环境加 `--pool=threads`）。
- 设计先行：spec（`docs/superpowers/specs/*.zh-CN.md`）→ code-level plan（`docs/superpowers/plans/`）→ 实现；改排序/生成的特性以验证 harness 作验收。
- 运行时从 `app/fixtures/` 读的数据文件须在 `backend/pyproject.toml` 的 `[tool.setuptools.package-data]` 声明（否则 prod wheel 缺文件）。
- Neo4j 架构/schema 变动后用 `backend/scripts/reseed_games.py --wipe` 清空重灌刷新旧数据。
