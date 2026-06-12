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
        disliked_references_or_mechanics=["联网多人"], desired_player_experiences=["欢乐混乱"],
        constraints=[DeveloperConstraint(id="c1", type=ConstraintType.HARD, statement="不做联网多人")],
    )


def _games() -> list[GameDimensions]:
    # 使用能触发协同规则的真实词汇，确保 enumerate_opportunities 产生 recipe 候选：
    # game_perma 有「永久死亡」(高方差失败源)；game_party 有「共享账户」(社交放大器)。
    # 规则 social_high_variance_comedy (高方差失败源 × 社交放大器 → 欢乐混乱) 被命中。
    return [
        GameDimensions("game_perma", "肉鸽幸存者", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, {"永久死亡"}),
        GameDimensions("game_party", "派对合作", {"派对游戏"}, {"第三人称"}, {"低多边形"}, {"共享账户"}),
    ]


def test_match_keeps_and_rejects_per_judgment() -> None:
    repo = StubRepo(_games())
    # 对全部候选给判断：第一个 reject，其余 keep（避免未判定候选混入断言）
    from app.services.opportunity_service import enumerate_opportunities, rank_candidates
    desired = set(_profile().desired_player_experiences)
    ranked = rank_candidates(enumerate_opportunities(_games(), desired), desired_experiences=desired)
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


def test_match_normalizes_wrapped_candidate_ids() -> None:
    # 复现并防回归：LLM 把 prompt 里 [id] 的方括号/空白一起回显（实测 qwen），
    # 旧逻辑 exact-match 全部对不上 → 全判未判定 + 未知 id。应规范化后正确匹配。
    repo = StubRepo(_games())
    from app.services.opportunity_service import enumerate_opportunities, rank_candidates

    desired = set(_profile().desired_player_experiences)
    ranked = rank_candidates(enumerate_opportunities(_games(), desired), desired_experiences=desired)
    judgments = [
        OpportunityJudgment(
            candidate_id=f"  [{c.id}]  ",  # 方括号 + 前后空白
            decision="keep",
            risk_posture=RiskPosture.BALANCED,
            fit_reason="契合",
            risk_reason="可控",
        )
        for c in ranked
    ]
    batch = OpportunityJudgmentBatch(judgments=judgments, warnings=[])
    result = match_opportunities(_profile(), repo, StubLlm(batch))

    assert sorted(a.id for a in result.areas) == sorted(c.id for c in ranked)
    assert not any("未判定" in w for w in result.warnings)
    assert not any("未知候选 id" in w for w in result.warnings)


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


def test_match_falls_back_with_warning_when_llm_raises() -> None:
    class BrokenLlm:
        def judge(self, profile, candidates):
            raise RuntimeError("boom")

    result = match_opportunities(_profile(), StubRepo(_games()), BrokenLlm())
    assert result.areas
    assert all(a.risk_posture == RiskPosture.BALANCED for a in result.areas)
    assert any("降级" in w for w in result.warnings)
    assert not any("未配置 LLM" in w for w in result.warnings)  # 异常路径不应误报未配置


def test_match_excludes_seen_candidates() -> None:
    from app.services.opportunity_service import enumerate_opportunities, rank_candidates
    desired = set(_profile().desired_player_experiences)
    ranked = rank_candidates(enumerate_opportunities(_games(), desired), desired_experiences=desired)
    assert len(ranked) >= 2  # 夹具应产出多个候选,便于排除其一
    seen = ranked[0].id
    batch = OpportunityJudgmentBatch(judgments=[], warnings=[])
    result = match_opportunities(_profile(), StubRepo(_games()), StubLlm(batch), seen_ids=[seen])
    all_ids = [a.id for a in result.areas] + [r.candidate_id for r in result.rejected]
    assert seen not in all_ids


def test_match_warns_when_all_candidates_seen() -> None:
    from app.services.opportunity_service import enumerate_opportunities
    desired = set(_profile().desired_player_experiences)
    every_id = [c.id for c in enumerate_opportunities(_games(), desired)]
    batch = OpportunityJudgmentBatch(judgments=[], warnings=[])
    result = match_opportunities(_profile(), StubRepo(_games()), StubLlm(batch), seen_ids=every_id)
    assert result.areas == []
    assert any("已无更多新机会" in w for w in result.warnings)


def test_match_empty_seen_ids_is_unchanged() -> None:
    batch = OpportunityJudgmentBatch(judgments=[], warnings=[])
    a = match_opportunities(_profile(), StubRepo(_games()), StubLlm(batch))
    b = match_opportunities(_profile(), StubRepo(_games()), StubLlm(batch), seen_ids=[])
    assert [x.id for x in a.areas] == [x.id for x in b.areas]
