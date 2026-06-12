from app.schemas.opportunity import (
    CandidateOpportunityArea,
    FunctionalRole,
    OpportunityEvidence,
    SynergyRationale,
    Transformation,
    TransformationType,
)
from app.services.opportunity_service import (
    GameDimensions,
    enumerate_opportunities,
    rank_candidates,
    role_combination_count,
)


def _games() -> list[GameDimensions]:
    return [
        GameDimensions(
            game_id="game_vs",
            summary="横版割草幸存者",
            genres={"类肉鸽"},
            perspectives={"横版2D"},
            art_styles={"像素美术"},
            mechanics={"护符定制"},
        ),
        GameDimensions(
            game_id="game_fps",
            summary="第一人称射击",
            genres={"射击"},
            perspectives={"第一人称"},
            art_styles={"低多边形"},
            mechanics={"能力树"},
        ),
    ]


def test_combine_borrows_mechanic_anchor_lacks() -> None:
    # enumerate_opportunities only generates COMBINE candidates (no substitute);
    # anchor game_vs lacks 能力树 → should appear as a COMBINE candidate if rules apply
    # or as a wildcard candidate.
    opps = enumerate_opportunities(_games(), set())
    combines = [
        c
        for c in opps
        if c.anchor_game_id == "game_vs"
        and c.transformation.type == TransformationType.COMBINE
    ]
    assert any(c.transformation.to_value == "能力树" for c in combines)
    picked = next(c for c in combines if c.transformation.to_value == "能力树")
    assert picked.transformation.from_value is None
    assert picked.transformation.dimension == "Mechanic"
    assert picked.evidence.target_value_game_ids == ["game_fps"]


def test_no_candidate_for_value_anchor_already_has() -> None:
    opps = enumerate_opportunities(_games(), set())
    # game_vs already has 护符定制 in mechanics → should not appear as a candidate for game_vs
    assert not any(
        c.anchor_game_id == "game_vs"
        and c.transformation.to_value == "护符定制"
        for c in opps
    )


def test_existing_combination_count_for_wildcard_candidate() -> None:
    # existing_combination_count for a Mechanic-dimension wildcard borrow uses
    # genre-sharing intersection: combination_game_ids are games that share the
    # anchor's genre AND carry the target mechanic.
    # g2 and g3 both share 类肉鸽 with g1 and have 连击系统 →
    # existing_combination_count should be 2.
    games = [
        GameDimensions("g1", "s1", {"类肉鸽"}, set(), set(), {"独门技能"}, set(), set()),
        GameDimensions("g2", "s2", {"类肉鸽"}, set(), set(), {"连击系统"}, set(), set()),
        GameDimensions("g3", "s3", {"类肉鸽"}, set(), set(), {"连击系统"}, set(), set()),
    ]
    opps = enumerate_opportunities(games, set())
    picks = [
        c for c in opps
        if c.anchor_game_id == "g1" and c.transformation.to_value == "连击系统"
    ]
    assert picks, "Expected a candidate for 连击系统 from g1"
    picked = picks[0]
    # g2 and g3 both share genre 类肉鸽 with g1 and have 连击系统
    assert picked.existing_combination_count == 2
    assert set(picked.evidence.combination_game_ids) == {"g2", "g3"}


# ---------------------------------------------------------------------------
# rank_candidates tests
# ---------------------------------------------------------------------------


def _cand(cid: str, existing: int, target_count: int) -> CandidateOpportunityArea:
    return CandidateOpportunityArea(
        id=cid,
        anchor_game_id="a",
        anchor_summary="s",
        transformation=Transformation(
            type=TransformationType.COMBINE,
            dimension="Mechanic",
            from_value=None,
            to_value=cid,
        ),
        existing_combination_count=existing,
        evidence=OpportunityEvidence(
            anchor_game_id="a",
            target_value_game_ids=[f"g{i}" for i in range(target_count)],
            combination_game_ids=[f"c{i}" for i in range(existing)],
        ),
    )


def test_rank_filters_out_candidates_above_ceiling() -> None:
    ranked = rank_candidates(
        [_cand("keep", 1, 2), _cand("drop", 5, 2)], max_existing=2, top_n=10
    )
    ids = [c.id for c in ranked]
    assert "keep" in ids
    assert "drop" not in ids


def test_rank_sorts_by_scarcity_then_target_attestation() -> None:
    ranked = rank_candidates(
        [
            _cand("novel_weak", 0, 1),
            _cand("novel_strong", 0, 3),
            _cand("less_novel", 1, 5),
        ],
        max_existing=2,
        top_n=10,
    )
    assert [c.id for c in ranked] == ["novel_strong", "novel_weak", "less_novel"]


def test_rank_truncates_to_top_n() -> None:
    ranked = rank_candidates(
        [_cand(f"c{i}", 0, 1) for i in range(40)], max_existing=2, top_n=30
    )
    assert len(ranked) == 30


def _dcand(
    cid: str,
    existing: int,
    target: int,
    anchor: str,
    dimension: str,
    to_value: str | None = None,
) -> CandidateOpportunityArea:
    # 替代类维度必须带 from_value(schema 校验);组合类(Mechanic)from_value 为 None
    is_combine = dimension == "Mechanic"
    return CandidateOpportunityArea(
        id=cid,
        anchor_game_id=anchor,
        anchor_summary="s",
        transformation=Transformation(
            type=(
                TransformationType.COMBINE
                if is_combine
                else TransformationType.SUBSTITUTE
            ),
            dimension=dimension,
            from_value=None if is_combine else "x",
            to_value=to_value or cid,
        ),
        existing_combination_count=existing,
        evidence=OpportunityEvidence(
            anchor_game_id=anchor,
            target_value_game_ids=[f"g{i}" for i in range(target)],
            combination_game_ids=[f"c{i}" for i in range(existing)],
        ),
    )


def test_rank_caps_candidates_per_anchor() -> None:
    cands = (
        [_dcand(f"a{i}", 0, 1, "a", "Mechanic") for i in range(5)]
        + [_dcand(f"b{i}", 0, 1, "b", "Genre") for i in range(2)]
        + [_dcand(f"c{i}", 0, 1, "c", "ArtStyle") for i in range(2)]
    )
    ranked = rank_candidates(
        cands, max_existing=2, top_n=6, max_per_anchor=2, max_per_dimension=5
    )
    anchors = [c.anchor_game_id for c in ranked]
    assert anchors.count("a") == 2
    assert anchors.count("b") == 2
    assert anchors.count("c") == 2


def test_rank_caps_candidates_per_dimension() -> None:
    # 6 条 Perspective(各自不同锚点,锚点配额不触发)更新颖,排在前;另有 3 条 Genre
    # 兜底。top_n=8 > 维度上限 5,且 Genre 足以把剩余槽填满 —— 所以第 6 条 Perspective
    # 是被「维度配额」挡掉的(既非 top_n 截断,也没被放宽兜底补回),这才真正测到次轴。
    cands = [
        _dcand(f"p{i}", 0, 2, f"panchor{i}", "Perspective", to_value=f"v{i}")
        for i in range(6)
    ] + [
        _dcand(f"q{i}", 0, 1, f"qanchor{i}", "Genre", to_value=f"w{i}")
        for i in range(3)
    ]
    ranked = rank_candidates(
        cands, max_existing=2, top_n=8, max_per_anchor=2, max_per_dimension=5
    )
    ids = {c.id for c in ranked}
    persp = [c for c in ranked if c.transformation.dimension == "Perspective"]
    assert len(ranked) == 8  # 填满到 top_n
    assert len(persp) == 5  # 维度配额生效(不是 6)
    assert "p5" not in ids  # 被配额挡掉的那条确实没入选


def test_rank_relaxes_caps_when_underfilled() -> None:
    cands = [_dcand(f"a{i}", 0, 1, "a", "Mechanic") for i in range(5)]
    ranked = rank_candidates(
        cands, max_existing=2, top_n=5, max_per_anchor=2, max_per_dimension=5
    )
    assert len(ranked) == 5
    assert {c.id for c in ranked} == {"a0", "a1", "a2", "a3", "a4"}


def test_rank_keeps_global_most_novel_first() -> None:
    cands = [
        _dcand("most_novel", 0, 5, "b", "Genre"),
        _dcand("mid", 0, 1, "c", "ArtStyle"),
        _dcand("less_novel", 1, 9, "a", "Mechanic"),
    ]
    ranked = rank_candidates(
        cands, max_existing=2, top_n=10, max_per_anchor=2, max_per_dimension=5
    )
    assert ranked[0].id == "most_novel"


def test_rank_diversity_is_deterministic() -> None:
    cands = (
        [_dcand(f"a{i}", 0, 1, "a", "Mechanic") for i in range(4)]
        + [_dcand(f"b{i}", 0, 2, "b", "Genre") for i in range(4)]
        + [_dcand(f"c{i}", 1, 1, "c", "ArtStyle") for i in range(4)]
    )
    r1 = [c.id for c in rank_candidates(cands, max_existing=2, top_n=8)]
    r2 = [c.id for c in rank_candidates(list(reversed(cands)), max_existing=2, top_n=8)]
    assert r1 == r2


# ---------------------------------------------------------------------------
# Synergy annotation + synergy-first ranking tests
# ---------------------------------------------------------------------------


def test_combine_candidate_annotated_with_synergy() -> None:
    # 锚点有「共享账户」(社交放大器)，借入「老虎机」(高方差失败源)
    # → 命中规则 social_high_variance_comedy → predicted_experience="欢乐混乱"
    games = [
        GameDimensions(
            "g_party", "派对", {"派对游戏"}, set(), set(), {"共享账户"}, set(), set()
        ),
        GameDimensions(
            "g_slot", "赌场", {"派对游戏"}, set(), set(), {"老虎机"}, set(), set()
        ),
    ]
    opps = enumerate_opportunities(games, set())
    borrow = next(
        c
        for c in opps
        if c.anchor_game_id == "g_party" and c.transformation.to_value == "老虎机"
    )
    assert borrow.synergy is not None
    assert borrow.synergy.predicted_experience == "欢乐混乱"


def test_combine_candidate_without_complement_has_no_synergy() -> None:
    # 借入「回合制」不构成任何规则的互补角色对 → synergy=None (wildcard)
    games = [
        GameDimensions("g1", "s1", {"解谜"}, set(), set(), {"分支叙事"}, set(), set()),
        GameDimensions("g2", "s2", {"解谜"}, set(), set(), {"回合制"}, set(), set()),
    ]
    opps = enumerate_opportunities(games, set())
    borrow = next(
        (
            c
            for c in opps
            if c.anchor_game_id == "g1" and c.transformation.to_value == "回合制"
        ),
        None,
    )
    # wildcard cap may filter it out; if present it must have no synergy
    if borrow is not None:
        assert borrow.synergy is None


def _synergy_cand(
    cid: str,
    existing: int,
    target_count: int,
    has_synergy: bool = True,
    predicted: str = "欢乐混乱",
) -> CandidateOpportunityArea:
    """构造带/不带 synergy 的 COMBINE 候选，用于 rank_candidates 排序测试。"""
    syn = (
        SynergyRationale(
            rule_id="social_high_variance_comedy",
            anchor_role=FunctionalRole.SOCIAL_AMPLIFIER,
            borrowed_role=FunctionalRole.HIGH_VARIANCE_FAILURE,
            predicted_experience=predicted,
        )
        if has_synergy
        else None
    )
    return CandidateOpportunityArea(
        id=cid,
        anchor_game_id="a",
        anchor_summary="s",
        transformation=Transformation(
            type=TransformationType.COMBINE,
            dimension="Mechanic",
            from_value=None,
            to_value=cid,
        ),
        existing_combination_count=existing,
        evidence=OpportunityEvidence(
            anchor_game_id="a",
            target_value_game_ids=[f"g{i}" for i in range(target_count)],
            combination_game_ids=[f"c{i}" for i in range(existing)],
        ),
        synergy=syn,
    )


def test_synergy_candidate_ranks_before_scarcity_candidate() -> None:
    # 有 synergy 但 existing=1 的候选应排在无 synergy 且 existing=0 的候选前面
    # （三档优先级：profile-match > synergy > wildcard）
    with_synergy = _synergy_cand("syn", existing=1, target_count=2, has_synergy=True)
    without_synergy = _synergy_cand(
        "no_syn", existing=0, target_count=2, has_synergy=False
    )
    ranked = rank_candidates([with_synergy, without_synergy], max_existing=2, top_n=10)
    assert ranked[0].id == "syn"


# ---------------------------------------------------------------------------
# Cross-dimension recipe candidates via enumerate_opportunities
# ---------------------------------------------------------------------------


def test_rule_driven_generates_cross_dimension_candidate() -> None:
    # g_survival 有「资源管理」(资源张力)；g_horror 在 Theme 有「生存恐怖」(恐惧张力)。
    # 规则 dread_scarcity_atmosphere: 恐惧张力 × 资源张力 → 应生成跨维度 Theme 候选。
    games = [
        GameDimensions("g_survival", "生存策略", {"生存"}, set(), set(), {"资源管理"}, set(), set()),
        GameDimensions("g_horror", "生存恐怖游戏", {"生存恐怖"}, set(), set(), {"追猎者"}, {"生存恐怖"}, set()),
    ]
    opps = enumerate_opportunities(games, set())
    borrow_theme = [
        c for c in opps
        if c.anchor_game_id == "g_survival"
        and c.transformation.dimension == "Theme"
        and c.transformation.to_value == "生存恐怖"
    ]
    assert borrow_theme and borrow_theme[0].synergy is not None


def test_mechanic_recipe_dedups_no_duplicate_ids() -> None:
    # enumerate_opportunities must not produce duplicate candidate ids
    games = [
        GameDimensions("g_party", "派对", {"派对游戏"}, set(), set(), {"共享账户"}, set(), set()),
        GameDimensions("g_slot", "赌场", {"派对游戏"}, set(), set(), {"老虎机"}, set(), set()),
    ]
    opps = enumerate_opportunities(games, set())
    ids = [c.id for c in opps]
    assert len(ids) == len(set(ids))   # 无重复 id
    borrow = [
        c for c in opps
        if c.anchor_game_id == "g_party" and c.transformation.to_value == "老虎机"
    ]
    assert len(borrow) == 1 and borrow[0].synergy is not None


def test_pure_scarcity_combine_still_present() -> None:
    # Wildcard channel: a mechanic that matches no rules but exists in the library
    # should still appear (up to wildcard cap) with synergy=None.
    games = [
        GameDimensions("g1", "s1", {"解谜"}, set(), set(), {"分支叙事"}, set(), set()),
        GameDimensions("g2", "s2", {"解谜"}, set(), set(), {"回合制"}, set(), set()),
    ]
    opps = enumerate_opportunities(games, set())
    # 「回合制」borrows from g2 → if present it should have synergy=None
    borrow = next(
        (c for c in opps if c.anchor_game_id == "g1" and c.transformation.to_value == "回合制"),
        None,
    )
    # wildcard cap (default 3) may include it; confirm synergy=None if present
    if borrow is not None:
        assert borrow.synergy is None
    # Also confirm at least one wildcard (synergy=None) candidate exists overall
    assert any(c.synergy is None for c in opps), (
        "Expected at least one wildcard (synergy=None) candidate from enumerate_opportunities"
    )


# ---------------------------------------------------------------------------
# Profile-aware synergy weighting tests
# ---------------------------------------------------------------------------


def test_rank_profile_match_outranks_non_desired_synergy() -> None:
    # profile-match tier (0) 胜出：命中期望体验但更不稀缺的候选排在前面
    a = _synergy_cand("A", existing=1, target_count=1, predicted="欢乐混乱")   # 命中开发者期望，但更不稀缺
    b = _synergy_cand("B", existing=0, target_count=1, predicted="战斗精通")   # 命中协同但非开发者期望
    ranked = rank_candidates([a, b], desired_experiences={"欢乐混乱"})
    assert ranked[0].id == "A"


def test_rank_without_desired_preserves_synergy_first_order() -> None:
    # desired=None：协同候选优先于非协同，相对序与现状一致（按稀缺）
    syn = _synergy_cand("S", existing=2, target_count=1, predicted="欢乐混乱")
    plain = _cand("P", existing=0, target_count=1)   # 无 synergy 但更稀缺
    ranked = rank_candidates([syn, plain], desired_experiences=None)
    assert ranked[0].id == "S"   # 协同仍优先于纯稀缺


# ---------------------------------------------------------------------------
# E-Task 1: role_combination_count + enumerate_opportunities
# ---------------------------------------------------------------------------


def test_role_combination_count() -> None:
    games = [
        # g_both 同时持有「老虎机」(高方差失败源) 和「共享账户」(社交放大器)
        GameDimensions("g_both", "s", {"派对游戏"}, set(), set(), {"老虎机", "共享账户"}, set(), set()),
        # g_one 只有「老虎机」(高方差失败源; 兼 认知降负载)
        GameDimensions("g_one", "s", set(), set(), set(), {"老虎机"}, set(), set()),
    ]
    assert role_combination_count(games, FunctionalRole.HIGH_VARIANCE_FAILURE, FunctionalRole.SOCIAL_AMPLIFIER) == 1
    assert role_combination_count(games, FunctionalRole.HIGH_VARIANCE_FAILURE, FunctionalRole.COMPETITION) == 0


def test_enumerate_opportunities_recipe() -> None:
    games = [
        # g_perma 有「永久死亡」(高方差失败源)
        GameDimensions("g_perma", "肉鸽", {"类肉鸽"}, set(), set(), {"永久死亡"}, set(), set()),
        # g_party 有「共享账户」(社交放大器)
        GameDimensions("g_party", "派对", {"派对游戏"}, set(), set(), {"共享账户"}, set(), set()),
    ]
    opps = enumerate_opportunities(games, {"欢乐混乱"})
    c = next(o for o in opps if o.synergy and o.synergy.predicted_experience == "欢乐混乱")
    assert c.transformation.type == TransformationType.COMBINE
    assert c.existing_combination_count == role_combination_count(
        games, c.synergy.anchor_role, c.synergy.borrowed_role
    )


def test_enumerate_opportunities_default_all_rules() -> None:
    games = [
        GameDimensions("g_perma", "肉鸽", {"类肉鸽"}, set(), set(), {"永久死亡"}, set(), set()),
        GameDimensions("g_party", "派对", {"派对游戏"}, set(), set(), {"共享账户"}, set(), set()),
    ]
    assert enumerate_opportunities(games, set())  # desired 空 → 全规则 → 非空


def test_enumerate_opportunities_no_substitute() -> None:
    games = [
        GameDimensions("g_perma", "肉鸽", {"类肉鸽"}, set(), set(), {"永久死亡"}, set(), set()),
        GameDimensions("g_party", "派对", {"派对游戏"}, set(), set(), {"共享账户"}, set(), set()),
    ]
    assert all(
        o.transformation.type == TransformationType.COMBINE
        for o in enumerate_opportunities(games, set())
    )


def test_enumerate_opportunities_wildcard_capped(monkeypatch) -> None:
    monkeypatch.setenv("OPP_MAX_WILDCARD", "1")
    # 锚点 g_anchor 有「老虎机」(高方差失败源 + 认知降负载)。
    # 借入「物理模拟」(涌现源) 和「非线性探索」(探索驱动) 均不与 高方差失败源/认知降负载 构成任何规则。
    # g_source1 和 g_source2 分别提供这两个可借入机制，确保 target_games 非空。
    # wildcard 通道应被上限截断至 1。
    games = [
        GameDimensions("g_anchor", "测试", {"解谜"}, set(), set(), {"老虎机"}, set(), set()),
        GameDimensions("g_source1", "物理", {"物理沙盒"}, set(), set(), {"物理模拟"}, set(), set()),
        GameDimensions("g_source2", "探索", {"开放世界"}, set(), set(), {"非线性探索"}, set(), set()),
    ]
    opps = enumerate_opportunities(games, set())
    wildcard_count = sum(1 for o in opps if o.synergy is None)
    # 前置断言：确认 fixture 确实产生了至少 1 条 wildcard，
    # 防止 fixture/规则变化后 wildcard 被消除时测试悄悄空转
    assert wildcard_count >= 1, (
        "Fixture 未产生任何 wildcard 候选，cap 断言将空转；"
        "请检查 _source_elements/规则是否将所有借入都分配了协同规则。"
    )
    assert wildcard_count <= 1
