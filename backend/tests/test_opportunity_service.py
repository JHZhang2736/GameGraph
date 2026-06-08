from app.schemas.artifacts import DeveloperConstraint, DeveloperProfile
from app.schemas.common import ConstraintType
from app.schemas.opportunity import CandidateOpportunityArea, RiskPosture
from app.services.opportunity_llm import OpportunityJudgment, OpportunityJudgmentBatch
from app.services.opportunity_service import GameDimensions, match_opportunities


class StubRepo:
    def __init__(self, games: list[GameDimensions]) -> None:
        self._games = games

    def fetch_game_dimensions(self) -> list[GameDimensions]:
        return self._games


class StubLlm:
    def __init__(self, batch: OpportunityJudgmentBatch) -> None:
        self._batch = batch
        self.seen: list[CandidateOpportunityArea] = []

    def judge(self, profile, candidates):
        self.seen = candidates
        return self._batch


def _profile() -> DeveloperProfile:
    return DeveloperProfile(
        id="profile_1", team_size="solo", time_budget="三个月",
        programming_ability="强", art_ability="弱", audio_ability="弱",
        content_production_ability="有限", liked_references=["Hades"],
        disliked_references_or_mechanics=["联网多人"], desired_player_experiences=["短局"],
        constraints=[DeveloperConstraint(id="c1", type=ConstraintType.HARD, statement="不做联网多人")],
    )


def _games() -> list[GameDimensions]:
    return [
        GameDimensions("game_vs", "横版割草", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, {"护符定制"}),
        GameDimensions("game_fps", "第一人称射击", {"射击"}, {"第一人称"}, {"低多边形"}, {"能力树"}),
    ]


def test_match_keeps_and_rejects_per_judgment() -> None:
    repo = StubRepo(_games())
    # 对全部候选给判断：第一个 reject，其余 keep（避免未判定候选混入断言）
    from app.services.opportunity_service import enumerate_candidates, rank_candidates
    ranked = rank_candidates(enumerate_candidates(_games()))
    reject_id = ranked[0].id
    judgments = [
        OpportunityJudgment(candidate_id=reject_id, decision="reject",
                            rejection_reason="违反硬约束：不做联网多人")
    ]
    for c in ranked[1:]:
        judgments.append(
            OpportunityJudgment(candidate_id=c.id, decision="keep",
                                risk_posture=RiskPosture.BALANCED,
                                fit_reason="契合", risk_reason="可控")
        )
    batch = OpportunityJudgmentBatch(judgments=judgments, warnings=[])
    result = match_opportunities(_profile(), repo, StubLlm(batch))
    assert result.profile_id == "profile_1"
    assert [r.candidate_id for r in result.rejected] == [reject_id]
    area_ids = [a.id for a in result.areas]
    assert reject_id not in area_ids
    assert all(a.risk_posture == RiskPosture.BALANCED for a in result.areas)
    assert area_ids  # 其余候选都保留为机会区域


def test_match_without_llm_returns_balanced_areas_with_warning() -> None:
    result = match_opportunities(_profile(), StubRepo(_games()), None)
    assert result.areas
    assert all(a.risk_posture == RiskPosture.BALANCED for a in result.areas)
    assert any("未配置 LLM" in w for w in result.warnings)
    assert result.rejected == []


def test_match_warns_on_sparse_result() -> None:
    repo = StubRepo([GameDimensions("g1", "s", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, set())])
    result = match_opportunities(_profile(), repo, None)
    assert any("稀疏" in w for w in result.warnings)


def test_unjudged_candidate_is_kept_balanced_with_warning() -> None:
    repo = StubRepo(_games())
    batch = OpportunityJudgmentBatch(judgments=[], warnings=[])  # LLM 什么都没判
    result = match_opportunities(_profile(), repo, StubLlm(batch))
    assert result.areas  # 候选未被静默丢弃
    assert all(a.risk_posture == RiskPosture.BALANCED for a in result.areas)
    assert any("未判定" in w for w in result.warnings)
