# 6.5 机会匹配模块设计 Spec

## 1. 目的

在「开发者画像」(6.4) 与「设计知识图谱」(入库产物) 之间架一座桥：从图谱里找出**有证据支撑、又契合开发者**的创新机会，作为 6.6 机会框架模块的输入。

本模块是整个「点子生成器」把「证据」转成「创意起点」的第一步。它必须满足一条产品直觉：**很多好点子 = 一个成熟配方 + 一个明确的创新点**（例：把吸血鬼幸存者从横版 2D 改为 3D 视角），而不是凭空发明。

## 2. 核心模型：机会区域 = 锚点 × 变形 + 新颖度

一个**机会区域 (OpportunityArea)** 由三部分构成：

1. **锚点 (anchor)**：图谱里一款已被验证可行的种子游戏（及其设计维度向量）。回答「站在哪个成熟的肩膀上」。
2. **变形 (transformation)**：对锚点某一个维度做一个明确改动。变形类型沿用规格 6.6 的词汇，本期只实现两种：
   - **替代 (substitute)**：把某维度的值换成另一个值（2D 视角 → 等距/第一人称）。
   - **组合 (combine)**：从另一款游戏借入一个机制节点。
   这就是「创新点」本身。
3. **新颖度 (novelty)**：用图谱验证「锚点 + 这个变形」得到的维度组合在现有游戏里是否稀缺/空白。稀缺 = 新颖度高；遍地都是 = 退化成安全选项。

> **为什么是「锚点×变形」而非「静态配方聚类」**：静态聚类描述的是**已存在**的东西；锚点×变形主动**指向一个还不存在、但有证据支撑可行**的格子。它天然产出「为什么新颖」和「借鉴自谁」，直接喂给 6.6。

## 3. 设计哲学边界：确定性引擎 + LLM 判断层

整份系统设计的核心原则是「不让 LLM 基于宽泛提示自由发明，而是先从证据组装受约束的框架，再用生成能力具象化」。6.5 在生成 (6.7) 的**上游**，因此**候选机会必须由证据驱动产出，不能靠 LLM 拍脑袋**。

据此切分职责：

| 层 | 负责 | 为什么由它负责 |
|---|---|---|
| **确定性图谱引擎** | 枚举「锚点×变形」候选；计算**稀缺度**（组合在图谱里的客观出现次数） | 客观、可追溯、不幻想 |
| **LLM 判断层** | 硬约束过滤、风险分档、可行性判定、写理由 | 需要自然语言理解与设计常识 |

关键边界：**LLM 永不决定「有多稀缺」（那是图谱的客观事实），也不发明候选；它只在确定性引擎给出的有界候选集上做判断。**

### 3.1 为什么放弃「能力—成本表」

早期方案设想维护一份「维度值 → 能力成本向量」的成本表来确定性地处理约束。**本期放弃**，原因：

- 它是模块里最重、最易欠债的部分（词表随入库持续生长，成本表要持续回填）。
- 开发者约束本身就是自然语言、带主观权衡，交给 LLM 判断更自然，也正好对应规格里「适配理由 / 约束取舍 / 为什么拒绝」三条。

成本表留作后续：当图谱足够大时，可从图谱证据（`ProductionConstraint` / `Risk` 标签共现）反推成本做自动校准，平滑升级、不返工。

### 3.2 新颖度的两层判断（关键）

确定性的稀缺度计数只能告诉你「这个组合没出现过」，但**无法区分「为什么没出现」**：

- **空白区 (white space)**：没人做过、但完全自洽可行 → **真机会**。
- **死区 (dead zone)**：没人做过、是因为根本说不通/做不出来 → **陷阱**（看似新颖、实则行不通）。

计数对两者一视同仁。因此新颖度是**两层协作**：

- 确定性引擎给出**稀缺度**（客观事实）。
- LLM 判断这份稀缺是**空白区还是死区**（自洽性/可行性）。判为死区的候选 → 路由到 `rejected[]`，理由写明为什么行不通。

最终新颖信号 = `稀缺度（确定性）× 可行性判定（LLM 闸）`，**不做不透明的数值加权**，保持可解释、可测。

> 这条恰好补全规格 6.5 验收「模块能解释为什么某个有吸引力的区域被拒绝」——一个看着新颖却因不可行被拒的区域，正是该验收的标准案例。

## 4. 数据流

```
DeveloperProfile (6.4 确认产物) ─┐
                                ├─→ [确定性引擎]  枚举候选 → CandidateOpportunityArea[]
图谱 (Neo4j, 入库产物) ──────────┘    锚点×变形 + 稀缺度计数 + 证据
                                            │  按稀缺度排序取 top-N（限定 LLM 负载）
                                            ▼
                              [LLM 判断层]  硬约束过滤 / 可行性闸 / 风险分档 / 写理由
                                            │  (未配置 LLM → 降级:不过滤 + 警告)
                                            ▼
                          OpportunityMatchResult { areas[], rejected[], warnings[] }
```

LLM **只加判断字段**（风险姿态/理由/是否剔除）；锚点·变形·稀缺度·证据全部由确定性引擎产出、原样透传。

## 5. 数据结构 (schema)

新增 `app/schemas/opportunity.py`：

```python
class TransformationType(str, Enum):
    SUBSTITUTE = "substitute"   # 替代:换一个维度值
    COMBINE    = "combine"      # 组合:借入一个机制

class Transformation(StrictBaseModel):
    type: TransformationType
    dimension: str            # "Perspective" / "ArtStyle" / "Genre" / "Mechanic"
    from_value: str | None    # 替代=锚点原值; 组合=None
    to_value: str             # 替代=新值; 组合=借入的机制名

class OpportunityEvidence(StrictBaseModel):
    anchor_game_id: str                 # 锚点有据
    target_value_game_ids: list[str]    # 目标值在别处有据(证明可行)
    combination_game_ids: list[str]     # 当前已有此组合的游戏(理想为空=空白)

class CandidateOpportunityArea(StrictBaseModel):  # 确定性引擎产出
    id: str
    anchor_game_id: str
    anchor_summary: str        # 取自 Game.one_sentence_summary
    transformation: Transformation
    existing_combination_count: int         # 组合现存游戏数,越小越新颖
    evidence: OpportunityEvidence

class RiskPosture(str, Enum):
    SAFE = "safe"            # 稳妥
    BALANCED = "balanced"    # 平衡
    CHALLENGING = "challenging"  # 挑战

class OpportunityArea(CandidateOpportunityArea):  # + LLM 判断字段
    risk_posture: RiskPosture
    fit_reason: str            # 适配理由
    risk_reason: str           # 风险/约束取舍说明

class RejectedOpportunity(StrictBaseModel):
    candidate_id: str
    rejection_reason: str      # 违反硬约束 或 新颖但不可行(死区)

class OpportunityMatchResult(StrictBaseModel):
    profile_id: str
    areas: list[OpportunityArea]
    rejected: list[RejectedOpportunity]
    warnings: list[str]        # 如稀疏匹配的解释
```

## 6. 确定性引擎（枚举 + 稀缺度）

`app/graph/opportunity_repository.py`（只读图查询）+ `app/services/opportunity_service.py`（枚举、排序、编排）。

对每款游戏 G 作为锚点：

- **替代**（维度 D ∈ {`Perspective`, `ArtStyle`, `Genre`}）：取 G 在 D 上的值 v；候选新值 v′ = 别的游戏在 D 上用过、且 ≠ v 的值。
- **组合**（维度 `Mechanic`）：候选借入机制 m = 别的游戏有、而 G 没有的机制。
- **稀缺度计数** `existing_combination_count` = 图谱里同时具备「**锚点主类型 (Genre)** + **目标值 v′/m**」的游戏数。`existing_combination_count = 0` ⇒ 空白机会候选。
- **有效性门槛**（应对小库）：仅当 `target_value_game_ids` 非空（新值有据）且 `combination_game_ids` 很小（组合稀缺）才保留——保证变形两端都站在真实证据上。
- 全部候选按 `existing_combination_count` 升序、`len(target_value_game_ids)` 降序排序，取 **top-N（默认 30）** 送 LLM 判断层。

**锚点签名（唯一主要可调旋钮）**：v1 用**主类型 Genre** 作为「锚点核心」来算共现，简单可解释。将来可加入 main_mechanics 重叠度以收紧签名。

> 图谱关系参考 `import_service.PROFILE_LIST_EDGES`：`HAS_PERSPECTIVE→Perspective`、`HAS_ART_STYLE→ArtStyle`、`HAS_GENRE→Genre`、`HAS_MECHANIC→Mechanic`。

## 7. LLM 判断层

`app/services/opportunity_llm.py`，仿 `profile_llm.py`：OpenAI 兼容 tool-calling、env 配置、可选依赖（未配置返回 `None`）。

一次 tool-call，输入 = 开发者画像 + top-N 候选（每个含变形与证据），输出 per-candidate：

- `keep` / `reject`
- keep 时：`risk_posture` + `fit_reason` + `risk_reason`
- reject 时：`rejection_reason`（硬约束违反 **或** 新颖但不可行）

外加整体 `warnings`。

System prompt 要点：
- **尊重硬约束**：违反者剔除到 `rejected[]`。
- **强偏好可保留**：但降级为 `challenging`，并在 `risk_reason` 写明警告。
- **可行性闸**：看似新颖但不自洽/做不出的候选，剔除到 `rejected[]` 并说明为何行不通。
- **跨风险姿态**：尽量让 `areas` 同时覆盖稳妥/平衡/挑战，避免全部退化成最安全模式。

**降级**：未配置 LLM → 返回全部候选、`risk_posture=balanced`、不做约束过滤，并加 `warnings`：「未配置 LLM，未做约束过滤与可行性判定」。（与 `profile_parse_service` 的降级策略一致。）

## 8. API

`app/api/routes_opportunity.py`：

```
POST /opportunity/match
  body:  DeveloperProfile        # 前端持有的已确认画像,直接传(无需服务端按 id 存查)
  deps:  repository(driver) + llm client(可选)
  resp:  OpportunityMatchResult
```

路由薄、委托 service；driver 经 `Depends` 注入、测试用 `dependency_overrides` 覆盖（仿 `routes_import.get_repository`）。在 `app/main.py` 注册 router。

## 9. 测试（对应规格独立测试用例）

| 规格测试用例 | 测试方式 |
|---|---|
| 给定严格硬约束，排除不兼容区域 | LLM stub：断言对应候选进 `rejected[]` 且带理由 |
| 给定强但非硬偏好，仍返回带警告的挑战型 | LLM stub：断言该候选 `risk_posture=challenging` 且 `risk_reason` 含警告 |
| 给定稀疏匹配，解释哪些约束压窄结果 | 断言候选过少时 `warnings` 被填充 |
| 每个区域含适配理由和约束取舍 | schema 必填 `fit_reason`/`risk_reason` + 契约往返测试 |
| 能解释为什么拒绝某个有吸引力的区域 | LLM stub：可行性闸把「新颖但不可行」候选送 `rejected[]` 并附理由 |

- **引擎**：Neo4j 集成测试（`@pytest.mark.integration`，仿 `test_game_repository_integration`）—— 给定 fixture 集断言候选与 `existing_combination_count`；纯排序/门槛逻辑用 stub repository 单测。
- **LLM 层**：stub 客户端（仿 `test_profile_llm`）。

## 10. 范围

### 范围内
- 上述 5 个新文件 + `main.py` 注册。
- 变形：替代（Perspective/ArtStyle/Genre）+ 组合（Mechanic）。
- 新颖度：朴素共现计数，锚点签名用 Genre。
- LLM 判断层 + 未配置降级。

### 范围外（留后续，平滑升级）
- 反转 / 迁移 / 压缩 三类变形。
- 能力—成本表（§3.1）。
- 锚点签名引入 mechanics 重叠度。
- 机会区域的服务端持久化（本期前端持有画像直接传）。

## 11. 已知局限

- **小库下新颖度偏粗**：种子库现约 8 款时，几乎任何组合都「不存在」，`existing_combination_count` 信号粗，更像「灵感触发器」而非「稀缺性证明」。用户计划持续入库至上百款，届时信号自动变锐（spec 本就规划「随图谱生长」）。本期不为此做特殊处理，只摆正语义：稀缺度 = 「在我们策展的库里是空白」。
- **LLM 行为非确定**：约束与可行性判断从「确定性可精确测试」变为「LLM 行为测试」（stub 断言），与既有 `test_profile_llm` 同策略。
