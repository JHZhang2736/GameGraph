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
