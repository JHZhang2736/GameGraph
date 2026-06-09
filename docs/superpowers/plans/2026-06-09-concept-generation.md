# 6.7 概念生成模块 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把单个 `OpportunityFrame`（6.6 产物）在其边界内具象化成固定 3 张 `ConceptCard`，经 `POST /concept/generate` 暴露，作为 6.8 概念评估的输入。

**Architecture:** 沿用 6.5/6.6 的「确定性 + LLM」两层，但确定性层极薄——`OpportunityFrame` 自包含，6.7 **不查图谱、无 repository、无 profile 入参**。LLM 生成层一次 tool-call 产 3 张概念草稿；确定性装配层只负责给每张草稿赋 `id = concept|{frame.id}|{n}` 与 `opportunity_frame_id = frame.id`。强依赖 LLM：未配置 → 503，调用失败/产物非法 → 502，不降级。

**Tech Stack:** Python 3.12 / FastAPI / Pydantic v2（`StrictBaseModel`）/ httpx（OpenAI 兼容 tool-calling）/ pytest。

**Spec:** `docs/superpowers/specs/2026-06-09-concept-generation-design.zh-CN.md`

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `backend/app/services/concept_llm.py` | `ConceptDraft` / `ConceptGenerationBatch` / `ConceptLlmClient` / `get_concept_llm_client`（仿 `opportunity_frame_llm`） | Create |
| `backend/app/services/concept_service.py` | `generate_concepts(frame, llm_client)` 编排 + id 装配 | Create |
| `backend/app/api/routes_concept.py` | `ConceptGenerateRequest` + `POST /concept/generate` + provider + 503/502 映射 | Create |
| `backend/app/main.py` | 注册 concept router | Modify |
| `backend/tests/test_concept_llm.py` | LLM 客户端 `MockTransport` 行为测试 | Create |
| `backend/tests/test_concept_service.py` | 装配 / id / 数量 / 错误传播 单测（stub llm） | Create |
| `backend/tests/test_concept_api.py` | 契约往返 + 422 + 503 + 502 端到端（stub） | Create |

**关键不变量（实现可依赖）:**
- `ConceptCard` 已在 `app/schemas/artifacts.py`，**本计划不改 schema**。
- `ConceptDraft` = `ConceptCard` 去掉 `id` / `opportunity_frame_id` 的全部创意字段，均 `min_length=1`。`draft.model_dump()` 解包进 `ConceptCard(...)` 字段名一一对应。
- `pydantic.ValidationError` 是 `ValueError` 子类，故「产物非法」抛出的 `ValidationError` 会被路由的 `except ValueError` 接住并映射成 502。

所有命令均在 `backend/` 目录下执行:`cd D:\Files\GameGraph\.claude\worktrees\concept-generation\backend`。

---

## Task 1: LLM 生成层 `concept_llm.py`

**Files:**
- Create: `backend/app/services/concept_llm.py`
- Test: `backend/tests/test_concept_llm.py`

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_concept_llm.py`:

```python
import json

import httpx
import pytest

from app.schemas.artifacts import OpportunityFrame
from app.services.concept_llm import (
    ConceptGenerationBatch,
    ConceptLlmClient,
    build_concept_tool_schema,
    get_concept_llm_client,
)
from app.services.opportunity_llm import LlmSettings


def _settings() -> LlmSettings:
    return LlmSettings(base_url="https://example.test/v1", api_key="secret", model="m", timeout=5.0)


def _frame() -> OpportunityFrame:
    return OpportunityFrame(
        id="frame|opp|game_vs|sub|Perspective|第一人称",
        developer_profile_id="profile_1",
        opportunity_area="第一人称生存割草",
        source_game_ids=["game_vs", "game_fps"],
        related_mechanics=["护符定制", "能力树"],
        related_player_experiences=["紧张刺激"],
        related_constraints=["低美术成本"],
        related_innovation_patterns=["数值滚雪球"],
        recommended_transformations=["将 Perspective 从「横版2D」替代为「第一人称」"],
        forbidden_directions=["违反硬约束：不做联网多人"],
        evidence_path=["锚点 game_vs 提供成熟配方"],
        fit_reason="契合短局",
        risk_reason="3D 抬高美术成本",
    )


def _draft_dict(title: str) -> dict:
    return {
        "title": title,
        "one_sentence_concept": "用护符构筑在第一人称视角下扛过夜晚的兽潮",
        "core_fantasy": "孤身在黑暗中靠 build 滚雪球翻盘",
        "core_loop": "探索→拾取护符→构筑→应对兽潮→升级",
        "main_player_decisions": ["先拿哪枚护符", "何时冒险深入"],
        "main_mechanics": ["护符定制", "能力树"],
        "reference_sources": ["game_vs", "game_fps"],
        "difference_from_references": "把横版割草搬到第一人称的近身紧张视野",
        "fit_reason": "契合 solo 程序强、短局",
        "production_risks": ["第一人称美术成本"],
        "design_risks": ["视角切换削弱割草爽快"],
        "novelty_reason": "第一人称割草在策展库稀缺",
        "suggested_prototype_scope": "单关卡 + 3 枚护符 + 一波兽潮",
    }


def _arguments() -> str:
    return json.dumps({"concepts": [_draft_dict(f"概念{i}") for i in (1, 2, 3)]})


def test_build_concept_tool_schema_exposes_function_name() -> None:
    tools = build_concept_tool_schema()
    assert tools[0]["function"]["name"] == "emit_concept_cards"
    assert tools[0]["function"]["parameters"]["properties"]


def test_generate_posts_request_and_parses() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"tool_calls": [
            {"function": {"name": "emit_concept_cards", "arguments": _arguments()}}
        ]}}]})

    client = ConceptLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    batch = client.generate(_frame())

    assert isinstance(batch, ConceptGenerationBatch)
    assert len(batch.concepts) == 3
    assert batch.concepts[0].title == "概念1"
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["body"]["tool_choice"]["function"]["name"] == "emit_concept_cards"
    assert seen["body"]["messages"][0]["role"] == "system"
    # frame 的禁止方向进了 user prompt（边界靠 prompt 约束）
    assert "不做联网多人" in seen["body"]["messages"][1]["content"]


def test_generate_raises_when_no_tool_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    client = ConceptLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError, match="tool_call"):
        client.generate(_frame())


def test_generate_raises_value_error_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid_api_key"}})

    client = ConceptLlmClient(_settings(), httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError, match="401"):
        client.generate(_frame())


def test_get_client_returns_none_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    assert get_concept_llm_client() is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_concept_llm.py -q`
Expected: FAIL —— `ModuleNotFoundError: No module named 'app.services.concept_llm'`。

- [ ] **Step 3: 写 LLM 模块**

新建 `backend/app/services/concept_llm.py`:

```python
from __future__ import annotations

import httpx
from pydantic import ConfigDict, Field

from app.schemas.artifacts import OpportunityFrame
from app.schemas.common import NonEmptyStr, StrictBaseModel
# 有意复用 6.5 的 LLM 设施（DRY）：LlmSettings 的 env 读取与 is_configured。
from app.services.opportunity_llm import LlmSettings

TOOL_NAME = "emit_concept_cards"

SYSTEM_PROMPT = (
    "你是独立游戏创意系统的概念生成器。"
    "给你一个【机会框架】(自包含创意简报：机会主题、来源游戏、相关机制/体验/约束/创新模式、"
    "推荐变形、禁止方向、证据路径、适配与风险理由)。"
    "请在这个框架划定的设计空间内生成【恰好 3 个】具体、可被评估的游戏概念，要求：\n"
    "1. 三个概念必须在核心玩法(core_loop)与核心幻想(core_fantasy)上各不相同，"
    "不得是同一想法的改写。\n"
    "2. reference_sources 只能引用框架的 source_game_ids；"
    "main_mechanics 取自框架的 related_mechanics / recommended_transformations。\n"
    "3. 不得生成踩 forbidden_directions 的概念；不得引入框架证据之外的机制或参考。\n"
    "4. 每个概念都要给出制作风险与设计风险；证据弱时在 novelty_reason / design_risks 体现"
    "适当不确定性，不得宣称概念一定好玩或成功。"
)


class ConceptDraft(StrictBaseModel):
    # extra="ignore"：LLM 可能多返字段，宽容忽略（与 opportunity_frame_llm.FrameSynthesis 一致）。
    # = ConceptCard 去掉 id / opportunity_frame_id 的全部创意字段，均必填（tool schema 标 required）。
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1)
    one_sentence_concept: str = Field(min_length=1)
    core_fantasy: str = Field(min_length=1)
    core_loop: str = Field(min_length=1)
    main_player_decisions: list[NonEmptyStr] = Field(min_length=1)
    main_mechanics: list[NonEmptyStr] = Field(min_length=1)
    reference_sources: list[NonEmptyStr] = Field(min_length=1)
    difference_from_references: str = Field(min_length=1)
    fit_reason: str = Field(min_length=1)
    production_risks: list[NonEmptyStr] = Field(min_length=1)
    design_risks: list[NonEmptyStr] = Field(min_length=1)
    novelty_reason: str = Field(min_length=1)
    suggested_prototype_scope: str = Field(min_length=1)


class ConceptGenerationBatch(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")

    concepts: list[ConceptDraft] = Field(default_factory=list)


def build_concept_tool_schema() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": "Emit exactly three concept cards within the opportunity frame.",
                "parameters": ConceptGenerationBatch.model_json_schema(),
            },
        }
    ]


def _frame_block(frame: OpportunityFrame) -> str:
    return (
        f"机会主题：{frame.opportunity_area}\n"
        f"来源游戏(reference_sources 只能取这些)：{', '.join(frame.source_game_ids)}\n"
        f"相关机制：{', '.join(frame.related_mechanics)}\n"
        f"相关体验：{', '.join(frame.related_player_experiences)}\n"
        f"相关约束：{', '.join(frame.related_constraints)}\n"
        f"相关创新模式：{', '.join(frame.related_innovation_patterns)}\n"
        f"推荐变形(主变形在首位)：{', '.join(frame.recommended_transformations)}\n"
        f"禁止方向(不得触犯)：{', '.join(frame.forbidden_directions)}\n"
        f"证据路径：{', '.join(frame.evidence_path)}\n"
        f"适配理由：{frame.fit_reason}\n"
        f"风险理由：{frame.risk_reason}"
    )


class ConceptLlmClient:
    def __init__(self, settings: LlmSettings, http_client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout)

    def generate(self, frame: OpportunityFrame) -> ConceptGenerationBatch:
        payload = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _frame_block(frame)},
            ],
            "tools": build_concept_tool_schema(),
            "tool_choice": {"type": "function", "function": {"name": TOOL_NAME}},
        }
        response = self._client.post(
            f"{self._settings.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self._settings.api_key}"},
            json=payload,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise ValueError(
                f"LLM request failed with {error.response.status_code}: {error.response.text}"
            ) from error
        data = response.json()
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError(f"Unexpected LLM response shape: {data}") from error
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            raise ValueError("LLM response missing tool_call")
        return ConceptGenerationBatch.model_validate_json(tool_calls[0]["function"]["arguments"])


def get_concept_llm_client() -> ConceptLlmClient | None:
    settings = LlmSettings.from_env()
    if not settings.is_configured:
        return None
    return ConceptLlmClient(settings)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_concept_llm.py -q`
Expected: PASS（5 passed）

- [ ] **Step 5: 提交**

```bash
git add app/services/concept_llm.py tests/test_concept_llm.py
git commit -m "feat(backend): add concept generation LLM client"
```

---

## Task 2: 确定性装配 `concept_service.py`

**Files:**
- Create: `backend/app/services/concept_service.py`
- Test: `backend/tests/test_concept_service.py`

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_concept_service.py`:

```python
import pytest

from app.schemas.artifacts import ConceptCard, OpportunityFrame
from app.services.concept_llm import ConceptDraft, ConceptGenerationBatch
from app.services import concept_service as svc


def _frame() -> OpportunityFrame:
    return OpportunityFrame(
        id="frame|opp|game_vs|sub|Perspective|第一人称",
        developer_profile_id="profile_1",
        opportunity_area="第一人称生存割草",
        source_game_ids=["game_vs", "game_fps"],
        related_mechanics=["护符定制", "能力树"],
        related_player_experiences=["紧张刺激"],
        related_constraints=["低美术成本"],
        related_innovation_patterns=["数值滚雪球"],
        recommended_transformations=["将 Perspective 从「横版2D」替代为「第一人称」"],
        forbidden_directions=["违反硬约束：不做联网多人"],
        evidence_path=["锚点 game_vs 提供成熟配方"],
        fit_reason="契合短局",
        risk_reason="3D 抬高美术成本",
    )


def _draft(title: str) -> ConceptDraft:
    return ConceptDraft(
        title=title,
        one_sentence_concept="用护符构筑在第一人称视角下扛过夜晚的兽潮",
        core_fantasy="孤身在黑暗中靠 build 滚雪球翻盘",
        core_loop="探索→拾取护符→构筑→应对兽潮→升级",
        main_player_decisions=["先拿哪枚护符", "何时冒险深入"],
        main_mechanics=["护符定制", "能力树"],
        reference_sources=["game_vs", "game_fps"],
        difference_from_references="把横版割草搬到第一人称的近身紧张视野",
        fit_reason="契合 solo 程序强、短局",
        production_risks=["第一人称美术成本"],
        design_risks=["视角切换削弱割草爽快"],
        novelty_reason="第一人称割草在策展库稀缺",
        suggested_prototype_scope="单关卡 + 3 枚护符 + 一波兽潮",
    )


class _StubLlm:
    def __init__(self, batch: ConceptGenerationBatch) -> None:
        self._batch = batch
        self.seen: OpportunityFrame | None = None

    def generate(self, frame: OpportunityFrame) -> ConceptGenerationBatch:
        self.seen = frame
        return self._batch


class _BrokenLlm:
    def generate(self, frame: OpportunityFrame) -> ConceptGenerationBatch:
        raise ValueError("boom")


def _batch(n: int = 3) -> ConceptGenerationBatch:
    return ConceptGenerationBatch(concepts=[_draft(f"概念{i}") for i in range(1, n + 1)])


def test_generate_concepts_assembles_three_cards() -> None:
    cards = svc.generate_concepts(_frame(), _StubLlm(_batch()))
    assert len(cards) == 3
    assert all(isinstance(c, ConceptCard) for c in cards)


def test_generate_concepts_ids_and_frame_link() -> None:
    frame = _frame()
    cards = svc.generate_concepts(frame, _StubLlm(_batch()))
    assert [c.id for c in cards] == [
        f"concept|{frame.id}|1",
        f"concept|{frame.id}|2",
        f"concept|{frame.id}|3",
    ]
    assert all(c.opportunity_frame_id == frame.id for c in cards)


def test_generate_concepts_preserves_draft_fields() -> None:
    cards = svc.generate_concepts(_frame(), _StubLlm(_batch()))
    assert cards[0].title == "概念1"
    assert cards[0].reference_sources == ["game_vs", "game_fps"]
    assert cards[0].production_risks == ["第一人称美术成本"]


def test_generate_concepts_passes_frame_to_llm() -> None:
    frame = _frame()
    stub = _StubLlm(_batch())
    svc.generate_concepts(frame, stub)
    assert stub.seen is frame


def test_generate_concepts_propagates_llm_error() -> None:
    with pytest.raises(ValueError, match="boom"):
        svc.generate_concepts(_frame(), _BrokenLlm())
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_concept_service.py -q`
Expected: FAIL —— `ModuleNotFoundError: No module named 'app.services.concept_service'`。

- [ ] **Step 3: 写 service 实现**

新建 `backend/app/services/concept_service.py`:

```python
from __future__ import annotations

from typing import Protocol

from app.schemas.artifacts import ConceptCard, OpportunityFrame
from app.services.concept_llm import ConceptGenerationBatch


class SupportsConceptGeneration(Protocol):
    def generate(self, frame: OpportunityFrame) -> ConceptGenerationBatch: ...


def generate_concepts(
    frame: OpportunityFrame,
    llm_client: SupportsConceptGeneration,
) -> list[ConceptCard]:
    # llm_client 非 None（None 由路由前置拦成 503）。generate 失败/产物非法抛 ValueError，
    # 由路由映射 502；ConceptCard(...) 对非法草稿抛 ValidationError（ValueError 子类），同样 502。
    batch = llm_client.generate(frame)
    return [
        ConceptCard(
            id=f"concept|{frame.id}|{i}",
            opportunity_frame_id=frame.id,
            **draft.model_dump(),
        )
        for i, draft in enumerate(batch.concepts, start=1)
    ]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_concept_service.py -q`
Expected: PASS（5 passed）

- [ ] **Step 5: 提交**

```bash
git add app/services/concept_service.py tests/test_concept_service.py
git commit -m "feat(backend): assemble concept cards from LLM drafts with deterministic ids"
```

---

## Task 3: API 路由 `POST /concept/generate` + 注册

**Files:**
- Create: `backend/app/api/routes_concept.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_concept_api.py`

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_concept_api.py`:

```python
from fastapi.testclient import TestClient

from app.api.routes_concept import get_concept_llm
from app.main import app
from app.schemas.artifacts import OpportunityFrame
from app.services.concept_llm import ConceptDraft, ConceptGenerationBatch


def _frame_dict() -> dict:
    return {
        "id": "frame|opp|game_vs|sub|Perspective|第一人称",
        "developer_profile_id": "profile_1",
        "opportunity_area": "第一人称生存割草",
        "source_game_ids": ["game_vs", "game_fps"],
        "related_mechanics": ["护符定制", "能力树"],
        "related_player_experiences": ["紧张刺激"],
        "related_constraints": ["低美术成本"],
        "related_innovation_patterns": ["数值滚雪球"],
        "recommended_transformations": ["将 Perspective 从「横版2D」替代为「第一人称」"],
        "forbidden_directions": ["违反硬约束：不做联网多人"],
        "evidence_path": ["锚点 game_vs 提供成熟配方"],
        "fit_reason": "契合短局",
        "risk_reason": "3D 抬高美术成本",
    }


def _draft(title: str) -> ConceptDraft:
    return ConceptDraft(
        title=title,
        one_sentence_concept="用护符构筑在第一人称视角下扛过夜晚的兽潮",
        core_fantasy="孤身在黑暗中靠 build 滚雪球翻盘",
        core_loop="探索→拾取护符→构筑→应对兽潮→升级",
        main_player_decisions=["先拿哪枚护符", "何时冒险深入"],
        main_mechanics=["护符定制", "能力树"],
        reference_sources=["game_vs", "game_fps"],
        difference_from_references="把横版割草搬到第一人称的近身紧张视野",
        fit_reason="契合 solo 程序强、短局",
        production_risks=["第一人称美术成本"],
        design_risks=["视角切换削弱割草爽快"],
        novelty_reason="第一人称割草在策展库稀缺",
        suggested_prototype_scope="单关卡 + 3 枚护符 + 一波兽潮",
    )


class StubLlm:
    def generate(self, frame: OpportunityFrame) -> ConceptGenerationBatch:
        return ConceptGenerationBatch(concepts=[_draft(f"概念{i}") for i in (1, 2, 3)])


class BrokenLlm:
    def generate(self, frame: OpportunityFrame) -> ConceptGenerationBatch:
        raise ValueError("upstream boom")


def test_generate_endpoint_returns_three_cards() -> None:
    app.dependency_overrides[get_concept_llm] = lambda: StubLlm()
    try:
        client = TestClient(app)
        response = client.post("/concept/generate", json={"frame": _frame_dict()})
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 3
        assert body[0]["opportunity_frame_id"] == _frame_dict()["id"]
        assert body[0]["id"] == f"concept|{_frame_dict()['id']}|1"
    finally:
        app.dependency_overrides.clear()


def test_generate_endpoint_503_without_llm() -> None:
    app.dependency_overrides[get_concept_llm] = lambda: None
    try:
        client = TestClient(app)
        response = client.post("/concept/generate", json={"frame": _frame_dict()})
        assert response.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_generate_endpoint_502_on_llm_error() -> None:
    app.dependency_overrides[get_concept_llm] = lambda: BrokenLlm()
    try:
        client = TestClient(app)
        response = client.post("/concept/generate", json={"frame": _frame_dict()})
        assert response.status_code == 502
    finally:
        app.dependency_overrides.clear()


def test_generate_endpoint_rejects_malformed_request() -> None:
    app.dependency_overrides[get_concept_llm] = lambda: StubLlm()
    try:
        client = TestClient(app)
        response = client.post("/concept/generate", json={})  # 缺 frame
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_concept_api.py -q`
Expected: FAIL —— `ModuleNotFoundError: No module named 'app.api.routes_concept'`。

- [ ] **Step 3: 写路由实现**

新建 `backend/app/api/routes_concept.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.artifacts import ConceptCard, OpportunityFrame
from app.schemas.common import StrictBaseModel
from app.services.concept_llm import ConceptLlmClient, get_concept_llm_client
from app.services.concept_service import generate_concepts

router = APIRouter()


class ConceptGenerateRequest(StrictBaseModel):
    frame: OpportunityFrame


def get_concept_llm() -> ConceptLlmClient | None:
    # 默认 provider：返回可选概念生成 LLM 客户端。测试通过 dependency_overrides 覆盖。
    return get_concept_llm_client()


@router.post("/concept/generate", response_model=list[ConceptCard])
def generate_endpoint(
    request: ConceptGenerateRequest,
    llm_client: ConceptLlmClient | None = Depends(get_concept_llm),
) -> list[ConceptCard]:
    # 强依赖 LLM：未配置 → 503；调用失败/产物非法（ValueError，含 ValidationError 子类）→ 502。
    if llm_client is None:
        raise HTTPException(status_code=503, detail="未配置 LLM，概念生成不可用。")
    try:
        return generate_concepts(request.frame, llm_client)
    except ValueError as error:
        raise HTTPException(status_code=502, detail=f"LLM 概念生成失败：{error}") from error
```

- [ ] **Step 4: 注册 router**

在 `backend/app/main.py` 修改:

顶部 import 区，在 `from app.api.routes_opportunity import router as opportunity_router` 下方追加:

```python
from app.api.routes_concept import router as concept_router
```

在 `app.include_router(opportunity_router)` 下方追加:

```python
app.include_router(concept_router)
```

- [ ] **Step 5: 跑测试确认通过**

Run: `python -m pytest tests/test_concept_api.py -q`
Expected: PASS（4 passed）

- [ ] **Step 6: 全量回归**

Run: `python -m pytest -q`
Expected: 全绿,无失败(基线 158 + 本计划新增 14 = 172 passed, 5 deselected;具体数字以实际为准,关键是 0 failed)。

- [ ] **Step 7: 提交**

```bash
git add app/api/routes_concept.py app/main.py tests/test_concept_api.py
git commit -m "feat(backend): add POST /concept/generate endpoint"
```

---

## 前端交接（不在本后端分支改动）

`POST /concept/generate`，body `{ frame: OpportunityFrame }` → `list[ConceptCard]`（恒 3 张）。前端 agent 在 6.7 前端分支自行:
- 把现有 mock 的 `/concepts` 页改成由选中的 `OpportunityFrame` 驱动，调 `POST /concept/generate` 渲染 3 张卡。
- 评估区块（分类 / 评分）保持 mock，等 6.8。
- 503 → 提示「需配置 LLM 才能生成概念」；502 → 提示「概念生成失败，可重试」。

**本后端 worktree 不触碰任何 `frontend/` 文件**，以免与前端 agent 并发冲突。

---

## Self-Review

**1. Spec coverage（逐节核对）:**
- §2 粒度 1 frame → 3 cards、一次调用 → Task 1 `_arguments` 3 张 + Task 2 装配 ✓
- §3 薄确定性 + LLM 两层 → Task 2 装配（id）+ Task 1 生成 ✓；无 repository/profile → 两模块签名均不含 ✓
- §4 数据流（503 前置、ValueError→502）→ Task 3 路由 ✓
- §5 schema：`ConceptDraft` = ConceptCard 去 id/frame_id、`ConceptGenerationBatch` → Task 1 ✓；不改 `artifacts.py` ✓
- §6 id 装配 `concept|{frame.id}|{n}` + `model_dump()` 解包 → Task 2 ✓
- §7 LLM 层 + 错误语义（503/502/422）→ Task 1（ValueError）+ Task 3（映射）✓；prompt 含禁止方向/差异/弱证据要点 → Task 1 SYSTEM_PROMPT ✓
- §8 API `{frame}` → list[ConceptCard]、独立 router、main 注册 → Task 3 ✓
- §10 测试映射（frame_id 回指 / id 前缀 / 参考来源差异 / 风险 / 503 / 502 / 无 tool_call）→ 三个测试文件覆盖 ✓
- §11 范围外（6.8/可配数量/per-card 容错/语义后校验/前端/持久化）→ 计划均未触碰 ✓

**2. Placeholder scan:** 无 TBD/TODO；每个 code step 含完整代码。✓

**3. Type consistency:**
- `ConceptDraft` 字段名 = `ConceptCard` 去 `id`/`opportunity_frame_id`，`model_dump()` 解包对应（Task 1 定义、Task 2 使用）✓
- `ConceptGenerationBatch.concepts: list[ConceptDraft]`（Task 1 定义，Task 2/3 构造一致）✓
- `ConceptLlmClient.generate(frame) -> ConceptGenerationBatch`（Task 1 定义，Task 2 Protocol / Task 3 调用一致）✓
- `generate_concepts(frame, llm_client) -> list[ConceptCard]`（Task 2 定义，Task 3 调用一致）✓
- provider 名 `get_concept_llm`（Task 3 定义，测试 `dependency_overrides` 覆盖一致）✓
- 工具名 `emit_concept_cards`（Task 1 `TOOL_NAME`，测试断言一致）✓
- frame id 格式 `frame|...` 与 concept id `concept|{frame.id}|{n}`（Task 2 实现与三处测试断言一致）✓

**执行顺序:** Task 1 → Task 2 → Task 3（Task 2 import Task 1 的 `ConceptGenerationBatch`；Task 3 import Task 1/2）。每个任务测试集独立，可分别验证。
