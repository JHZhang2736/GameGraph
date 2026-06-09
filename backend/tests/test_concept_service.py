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
