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
    enumerate_candidates,
    rank_candidates,
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


def test_substitute_borrows_target_value_from_other_game() -> None:
    candidates = enumerate_candidates(_games())
    subs = [
        c
        for c in candidates
        if c.anchor_game_id == "game_vs"
        and c.transformation.type == TransformationType.SUBSTITUTE
        and c.transformation.dimension == "Perspective"
    ]
    assert any(c.transformation.to_value == "第一人称" for c in subs)
    picked = next(c for c in subs if c.transformation.to_value == "第一人称")
    assert picked.transformation.from_value == "横版2D"
    assert picked.evidence.target_value_game_ids == ["game_fps"]
    assert picked.existing_combination_count == 0
    assert picked.evidence.combination_game_ids == []


def test_combine_borrows_mechanic_anchor_lacks() -> None:
    candidates = enumerate_candidates(_games())
    combines = [
        c
        for c in candidates
        if c.anchor_game_id == "game_vs"
        and c.transformation.type == TransformationType.COMBINE
    ]
    assert any(c.transformation.to_value == "能力树" for c in combines)
    picked = next(c for c in combines if c.transformation.to_value == "能力树")
    assert picked.transformation.from_value is None
    assert picked.transformation.dimension == "Mechanic"
    assert picked.evidence.target_value_game_ids == ["game_fps"]


def test_no_candidate_for_value_anchor_already_has() -> None:
    candidates = enumerate_candidates(_games())
    assert not any(
        c.anchor_game_id == "game_vs"
        and c.transformation.dimension == "ArtStyle"
        and c.transformation.to_value == "像素美术"
        for c in candidates
    )


def test_substitute_skipped_when_anchor_has_no_value_in_dimension() -> None:
    games = [
        GameDimensions(
            "g1", "s1", {"类肉鸽"}, set(), {"像素美术"}, set()
        ),  # 无 perspective
        GameDimensions("g2", "s2", {"类肉鸽"}, {"第一人称"}, {"低多边形"}, set()),
    ]
    candidates = enumerate_candidates(games)
    # g1 在 Perspective 上无值 → 不应为它生成任何 Perspective 替代候选
    assert not any(
        c.anchor_game_id == "g1" and c.transformation.dimension == "Perspective"
        for c in candidates
    )


def test_substitute_from_value_is_lexicographically_smallest_for_multi_value_anchor() -> (
    None
):
    games = [
        GameDimensions("g1", "s1", {"类肉鸽", "动作"}, {"横版2D"}, {"像素美术"}, set()),
        GameDimensions("g2", "s2", {"射击"}, {"横版2D"}, {"像素美术"}, set()),
    ]
    candidates = enumerate_candidates(games)
    sub = next(
        c
        for c in candidates
        if c.anchor_game_id == "g1"
        and c.transformation.dimension == "Genre"
        and c.transformation.to_value == "射击"
    )
    # anchor genres {"动作","类肉鸽"} → 词典序最小者为「动作」
    assert sub.transformation.from_value == "动作"


def test_existing_combination_count_counts_genre_sharing_games_with_target_value() -> (
    None
):
    games = [
        GameDimensions("g1", "s1", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, set()),
        GameDimensions("g2", "s2", {"类肉鸽"}, {"第一人称"}, {"低多边形"}, set()),
        GameDimensions("g3", "s3", {"类肉鸽"}, {"第一人称"}, {"低多边形"}, set()),
    ]
    candidates = enumerate_candidates(games)
    picked = next(
        c
        for c in candidates
        if c.anchor_game_id == "g1"
        and c.transformation.dimension == "Perspective"
        and c.transformation.to_value == "第一人称"
    )
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
# Task 4: synergy annotation + synergy-first ranking tests
# ---------------------------------------------------------------------------


def test_combine_candidate_annotated_with_synergy(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "1")
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
    cands = enumerate_candidates(games)
    borrow = next(
        c
        for c in cands
        if c.anchor_game_id == "g_party" and c.transformation.to_value == "老虎机"
    )
    assert borrow.synergy is not None
    assert borrow.synergy.predicted_experience == "欢乐混乱"


def test_combine_candidate_without_complement_has_no_synergy(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    # 借入「回合制」不构成任何规则的互补角色对 → synergy=None
    games = [
        GameDimensions("g1", "s1", {"解谜"}, set(), set(), {"分支叙事"}, set(), set()),
        GameDimensions("g2", "s2", {"解谜"}, set(), set(), {"回合制"}, set(), set()),
    ]
    cands = enumerate_candidates(games)
    borrow = next(
        c
        for c in cands
        if c.anchor_game_id == "g1" and c.transformation.to_value == "回合制"
    )
    assert borrow.synergy is None


def _synergy_cand(
    cid: str, existing: int, target_count: int, has_synergy: bool
) -> CandidateOpportunityArea:
    """构造带/不带 synergy 的 COMBINE 候选，用于 rank_candidates 排序测试。"""
    syn = (
        SynergyRationale(
            rule_id="social_high_variance_comedy",
            anchor_role=FunctionalRole.SOCIAL_AMPLIFIER,
            borrowed_role=FunctionalRole.HIGH_VARIANCE_FAILURE,
            predicted_experience="欢乐混乱",
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


def test_synergy_candidate_ranks_before_scarcity_candidate(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    # 有 synergy 但 existing=1 的候选应排在无 synergy 且 existing=0 的候选前面
    with_synergy = _synergy_cand("syn", existing=1, target_count=2, has_synergy=True)
    without_synergy = _synergy_cand(
        "no_syn", existing=0, target_count=2, has_synergy=False
    )
    ranked = rank_candidates([with_synergy, without_synergy], max_existing=2, top_n=10)
    assert ranked[0].id == "syn"


def test_synergy_ranking_disabled_falls_back_to_scarcity_first(monkeypatch) -> None:
    # SYNERGY_RANKING=0 → 回退到纯稀缺性排序：existing=0 的排在 existing=1 前
    monkeypatch.setenv("SYNERGY_RANKING", "0")
    with_synergy = _synergy_cand("syn", existing=1, target_count=2, has_synergy=True)
    without_synergy = _synergy_cand(
        "no_syn", existing=0, target_count=2, has_synergy=False
    )
    ranked = rank_candidates([with_synergy, without_synergy], max_existing=2, top_n=10)
    assert ranked[0].id == "no_syn"


# ---------------------------------------------------------------------------
# H-Task 2: rule-driven cross-dimension candidate generator + union dedup
# ---------------------------------------------------------------------------


def test_rule_driven_generates_cross_dimension_candidate(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    # g_survival 有「资源管理」(资源张力)；g_horror 在 Theme 有「生存恐怖」(恐惧张力)。
    # 规则 dread_scarcity_atmosphere: 恐惧张力 × 资源张力 → 应生成跨维度 Theme 候选。
    games = [
        GameDimensions("g_survival", "生存策略", {"生存"}, set(), set(), {"资源管理"}, set(), set()),
        GameDimensions("g_horror", "生存恐怖游戏", {"生存恐怖"}, set(), set(), {"追猎者"}, {"生存恐怖"}, set()),
    ]
    cands = enumerate_candidates(games)
    borrow_theme = [c for c in cands if c.anchor_game_id == "g_survival"
                    and c.transformation.dimension == "Theme"
                    and c.transformation.to_value == "生存恐怖"]
    assert borrow_theme and borrow_theme[0].synergy is not None


def test_rule_driven_absent_when_flag_off(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "0")
    games = [
        GameDimensions("g_survival", "生存策略", {"生存"}, set(), set(), {"资源管理"}, set(), set()),
        GameDimensions("g_horror", "生存恐怖游戏", {"生存恐怖"}, set(), set(), {"追猎者"}, {"生存恐怖"}, set()),
    ]
    cands = enumerate_candidates(games)
    assert not any(c.transformation.dimension in ("Theme", "GameFeel") for c in cands)
    assert all(c.synergy is None for c in cands)  # flag off → 无任何候选携带 synergy


def test_mechanic_rule_driven_dedups_with_attribute_combine(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    games = [
        GameDimensions("g_party", "派对", {"派对游戏"}, set(), set(), {"共享账户"}, set(), set()),
        GameDimensions("g_slot", "赌场", {"派对游戏"}, set(), set(), {"老虎机"}, set(), set()),
    ]
    cands = enumerate_candidates(games)
    ids = [c.id for c in cands]
    assert len(ids) == len(set(ids))   # 无重复 id
    borrow = [c for c in cands if c.anchor_game_id == "g_party" and c.transformation.to_value == "老虎机"]
    assert len(borrow) == 1 and borrow[0].synergy is not None


def test_pure_scarcity_combine_still_present(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    games = [
        GameDimensions("g1", "s1", {"解谜"}, set(), set(), {"分支叙事"}, set(), set()),
        GameDimensions("g2", "s2", {"解谜"}, set(), set(), {"回合制"}, set(), set()),
    ]
    cands = enumerate_candidates(games)
    borrow = next(c for c in cands if c.anchor_game_id == "g1" and c.transformation.to_value == "回合制")
    assert borrow.synergy is None


# ---------------------------------------------------------------------------
# H-Task 3: profile-aware synergy weighting tests
# ---------------------------------------------------------------------------


def _syn_cand(cid: str, predicted: str, existing: int) -> CandidateOpportunityArea:
    """构造带指定 predicted_experience 的协同候选。"""
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
            target_value_game_ids=["g0"],
            combination_game_ids=[f"c{i}" for i in range(existing)],
        ),
        synergy=SynergyRationale(
            rule_id="social_high_variance_comedy",
            anchor_role=FunctionalRole.SOCIAL_AMPLIFIER,
            borrowed_role=FunctionalRole.HIGH_VARIANCE_FAILURE,
            predicted_experience=predicted,
        ),
    )


def _plain_cand(cid: str, existing: int) -> CandidateOpportunityArea:
    """构造无 synergy 的普通候选。"""
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
            target_value_game_ids=["g0"],
            combination_game_ids=[f"c{i}" for i in range(existing)],
        ),
    )


def test_rank_profile_match_outranks_plain_synergy(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    a = _syn_cand("A", predicted="欢乐混乱", existing=1)   # 命中开发者期望，但更不稀缺
    b = _syn_cand("B", predicted="战斗精通", existing=0)   # 命中协同但非开发者期望
    ranked = rank_candidates([a, b], desired_experiences={"欢乐混乱"})
    assert ranked[0].id == "A"


def test_rank_without_desired_preserves_synergy_first_order(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    # desired=None：协同候选优先于非协同，相对序与现状一致（按稀缺）
    syn = _syn_cand("S", predicted="欢乐混乱", existing=2)
    plain = _plain_cand("P", existing=0)   # 无 synergy 但更稀缺
    ranked = rank_candidates([syn, plain], desired_experiences=None)
    assert ranked[0].id == "S"   # 协同仍优先于纯稀缺


def test_rank_flag_off_ignores_desired(monkeypatch) -> None:
    monkeypatch.setenv("SYNERGY_RANKING", "0")
    syn = _syn_cand("S", predicted="欢乐混乱", existing=2)
    plain = _plain_cand("P", existing=0)
    ranked = rank_candidates([syn, plain], desired_experiences={"欢乐混乱"})
    assert ranked[0].id == "P"   # flag 关：回退稀缺优先，synergy/画像被忽略
