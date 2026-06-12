"""
Recipe opportunity enumeration – validation harness

Five scenarios that prove the recipe/role-driven generator produces the expected results:

  Test 1 – 留一法重新发现 (leave-one-out rediscovery)
    No single library game exemplifies the "社交放大器 × 高方差失败源 → 欢乐混乱"
    pairing, yet the recipe engine re-discovers the opportunity from the role layer alone.

  Test 2 – 跨维度可达性 (cross-dimension reachability)
    A synergy completable only via a Theme carrier IS produced by the recipe engine.

  Test 3 – 协同优先 (synergy-first ranking)
    Same games + desired_experiences; tier-0 candidate (predicted_experience ∈ desired)
    ranks at position 0 and has higher rank than a non-synergy candidate with lower
    existing_combination_count.
"""

from app.services.opportunity_service import (
    GameDimensions,
    enumerate_opportunities,
    rank_candidates,
)


# ---------------------------------------------------------------------------
# Shared fixture helper
# ---------------------------------------------------------------------------


def _permadeath_party_games(
    anchor_id: str = "g_permadeath",
    social_id: str = "g_party",
) -> list[GameDimensions]:
    """Return the two-game 永久死亡 + 共享账户 fixture used by Test 1 and Test 3."""
    return [
        # Anchor: has 永久死亡 (高方差失败源 via Mechanic); no 共享账户
        GameDimensions(
            game_id=anchor_id,
            summary="高难度肉鸽——一死到底",
            genres={"类肉鸽"},
            perspectives=set(),
            art_styles=set(),
            mechanics={"永久死亡"},
            theme=set(),
            game_feel=set(),
        ),
        # Source: has 共享账户 (社交放大器 via Mechanic); no 永久死亡
        GameDimensions(
            game_id=social_id,
            summary="多人派对游戏",
            genres={"派对游戏"},
            perspectives=set(),
            art_styles=set(),
            mechanics={"共享账户"},
            theme=set(),
            game_feel=set(),
        ),
    ]


# ---------------------------------------------------------------------------
# Test 1: 留一法重新发现
# Neither game has BOTH 永久死亡 (高方差失败源) AND 共享账户 (社交放大器).
# The engine must rediscover the "欢乐混乱" opportunity from the role layer.
# ---------------------------------------------------------------------------


def test_leave_one_out_rediscovery() -> None:
    """
    Validates that the recipe path re-discovers an opportunity region
    even when no single library game exemplifies the full synergy pairing.

    Anchor: 永久死亡 (高方差失败源)  ← no 共享账户
    Other:  共享账户 (社交放大器)    ← no 永久死亡

    Rule social_high_variance_comedy: 高方差失败源 × 社交放大器 → 欢乐混乱
    Expected: a candidate exists with synergy.predicted_experience == "欢乐混乱",
    and with desired_experiences={"欢乐混乱"} it rises to Top-N position 0.
    """
    games = _permadeath_party_games()
    candidates = enumerate_opportunities(games, {"欢乐混乱"})

    # At least one candidate from anchor g_permadeath should target 共享账户
    # with synergy predicting 欢乐混乱 (rule social_high_variance_comedy).
    comedy_candidates = [
        c
        for c in candidates
        if c.anchor_game_id == "g_permadeath"
        and c.synergy is not None
        and c.synergy.predicted_experience == "欢乐混乱"
    ]
    assert comedy_candidates, (
        "Expected at least one candidate with synergy.predicted_experience == '欢乐混乱' "
        "for anchor g_permadeath, but none were found — leave-one-out rediscovery FAILED."
    )

    # The target element 共享账户 must be present in a candidate
    target_element_candidates = [
        c for c in comedy_candidates if c.transformation.to_value == "共享账户"
    ]
    assert target_element_candidates, (
        "Expected a candidate targeting 共享账户 with synergy '欢乐混乱', none found."
    )

    # With desired_experiences={"欢乐混乱"}, the synergy candidate should rank at top
    ranked = rank_candidates(
        candidates,
        top_n=10,
        desired_experiences={"欢乐混乱"},
    )
    assert ranked, "rank_candidates returned empty list."
    assert ranked[0].synergy is not None, "Top-ranked candidate has no synergy."
    assert ranked[0].synergy.predicted_experience == "欢乐混乱", (
        f"Top-ranked candidate has predicted_experience={ranked[0].synergy.predicted_experience!r}, "
        "expected '欢乐混乱'."
    )


# ---------------------------------------------------------------------------
# Test 2: 跨维度可达性
# Recipe engine generates a Theme-dimension candidate via rule dread_scarcity_atmosphere.
# ---------------------------------------------------------------------------


def test_cross_dimension_reachability() -> None:
    """
    Validates that the recipe engine generates cross-dimension Theme candidates.

    Anchor: 资源管理 (资源张力 via Mechanic)
    Source: Theme 生存恐怖 (恐惧张力)

    Rule dread_scarcity_atmosphere: 恐惧张力 × 资源张力 → 氛围营造
    Expected: Theme-dimension candidate exists with to_value="生存恐怖",
              synergy.predicted_experience == "氛围营造".
    """
    games = [
        # Anchor: 资源管理 (资源张力 via Mechanic)
        GameDimensions(
            game_id="g_survival",
            summary="资源管理生存策略",
            genres={"生存"},
            perspectives=set(),
            art_styles=set(),
            mechanics={"资源管理"},
            theme=set(),
            game_feel=set(),
        ),
        # Source: Theme 生存恐怖 (恐惧张力 via Theme)
        GameDimensions(
            game_id="g_horror",
            summary="生存恐怖游戏",
            genres={"生存恐怖"},
            perspectives=set(),
            art_styles=set(),
            mechanics=set(),
            theme={"生存恐怖"},
            game_feel=set(),
        ),
    ]

    candidates = enumerate_opportunities(games, set())

    theme_candidates = [
        c
        for c in candidates
        if c.anchor_game_id == "g_survival"
        and c.transformation.dimension == "Theme"
        and c.transformation.to_value == "生存恐怖"
    ]
    assert theme_candidates, (
        "Expected a Theme-dimension candidate targeting '生存恐怖' "
        "for anchor g_survival, but none found."
    )
    assert theme_candidates[0].synergy is not None, (
        "Theme candidate exists but has no synergy annotation."
    )
    assert theme_candidates[0].synergy.predicted_experience == "氛围营造", (
        f"Expected predicted_experience='氛围营造', "
        f"got {theme_candidates[0].synergy.predicted_experience!r}."
    )


# ---------------------------------------------------------------------------
# Test 3: 协同优先 (synergy-first ranking)
# With desired_experiences, tier-0 synergy candidates rank above wildcards
# even when wildcards have lower existing_combination_count.
# ---------------------------------------------------------------------------


def test_synergy_first_ranking_with_desired_experiences() -> None:
    """
    Validates synergy-first ranking: tier-0 candidate (synergy.predicted_experience ∈
    desired_experiences) ranks at top even when a wildcard candidate has lower
    existing_combination_count.

    Fixture: anchor has 永久死亡 (高方差失败源); g_social provides 共享账户 (社交放大器).
    g_plain provides 回合制 (no synergy rule match) creating a wildcard candidate.
    desired_experiences={"欢乐混乱"}.
    """
    desired = {"欢乐混乱"}

    games = _permadeath_party_games(anchor_id="g_anchor", social_id="g_social") + [
        GameDimensions(
            game_id="g_plain",
            summary="回合制卡牌",
            genres={"卡牌"},
            perspectives=set(),
            art_styles=set(),
            mechanics={"回合制"},
            theme=set(),
            game_feel=set(),
        ),
    ]

    candidates = enumerate_opportunities(games, desired)
    ranked = rank_candidates(candidates, top_n=10, desired_experiences=desired)

    assert ranked, "rank_candidates returned empty list."

    # Collect tier-0 candidates (synergy.predicted_experience ∈ desired)
    tier0 = [
        c
        for c in ranked
        if c.synergy is not None and c.synergy.predicted_experience in desired
    ]
    assert tier0, (
        "No tier-0 candidate with predicted_experience ∈ desired_experiences "
        "found in ranked output — synergy-aware ranking produced nothing observable."
    )

    # The top-ranked candidate should be from tier-0
    assert ranked[0].synergy is not None, "Top-ranked candidate has no synergy."
    assert ranked[0].synergy.predicted_experience in desired, (
        f"Top-ranked candidate predicted_experience={ranked[0].synergy.predicted_experience!r} "
        f"not in desired={desired}."
    )


# ---------------------------------------------------------------------------
# Test 4: 哑候选占比 (dumb-candidate ratio) — Spec §6.1
# Wildcard (synergy=None) candidates must never exceed OPP_MAX_WILDCARD even
# when the library can produce far more non-rule-matching borrows.
# ---------------------------------------------------------------------------


def test_dumb_candidate_ratio_bounded_by_wildcard_cap(monkeypatch) -> None:
    """
    Validates that 'dumb' (no predicted_experience / synergy=None) candidates
    are strictly bounded by the OPP_MAX_WILDCARD quota, not by the raw count
    of non-rule-matching mechanics in the library.

    Fixture: anchor has 永久死亡 (高方差失败源) — a single recipe role.
    Five source games each carry a unique mechanic that maps to no role in the
    element_roles fixture (ad-hoc test-only terms), guaranteeing they never
    trigger a synergy rule and must land in the wildcard channel.
    OPP_MAX_WILDCARD is patched to 2 so the assertion is tight.
    """
    monkeypatch.setenv("OPP_MAX_WILDCARD", "2")

    # Five source games, each providing one mechanic unknown to element_roles
    # (novel test-only names) → guaranteed wildcards, no synergy rule can fire.
    games = [
        GameDimensions(
            game_id="g_anchor",
            summary="高难度肉鸽",
            genres={"类肉鸽"},
            perspectives=set(),
            art_styles=set(),
            mechanics={"永久死亡"},
            theme=set(),
            game_feel=set(),
        ),
    ] + [
        GameDimensions(
            game_id=f"g_src{i}",
            summary=f"测试源游戏{i}",
            genres={"解谜"},
            perspectives=set(),
            art_styles=set(),
            mechanics={f"测试专用机制_{i}"},
            theme=set(),
            game_feel=set(),
        )
        for i in range(5)
    ]

    candidates = enumerate_opportunities(games, set())

    wildcard_count = sum(1 for c in candidates if c.synergy is None)

    # Pre-condition: the fixture must have produced at least one wildcard so the
    # cap test is not vacuous.  If all test mechanics somehow triggered rules the
    # fixture design is broken.
    assert wildcard_count >= 1, (
        "Fixture produced zero wildcard candidates; check that test-only mechanic "
        "names are truly absent from element_roles.json."
    )

    # Core assertion: wildcard channel is capped at OPP_MAX_WILDCARD (= 2).
    assert wildcard_count <= 2, (
        f"Expected ≤ 2 wildcard (synergy=None) candidates (OPP_MAX_WILDCARD=2), "
        f"got {wildcard_count}. Wildcard quota is not being enforced."
    )


# ---------------------------------------------------------------------------
# Test 5: 画像靶向 (profile-targeting) — Spec §6.2
# When desired_experiences is specified, the top-ranked candidate's
# predicted_experience must match the requested experience.
# ---------------------------------------------------------------------------


def test_profile_targeting_surfaces_desired_experience_at_top() -> None:
    """
    Validates profile-targeting: rank_candidates with a specific desired set
    surfaces a tier-0 candidate (predicted_experience ∈ desired) at position 0,
    while without desired the ranking still produces synergy candidates but does
    not guarantee the specific experience at the top.

    Fixture: anchor carries both 永久死亡 (高方差失败源) and 共享账户 (社交放大器).
    Two source games provide complementary mechanics:
      - 连招 (掌握曲线): fires mastery_under_permadeath → 战斗精通
      - 老虎机 (高方差失败源 → via the social_high_variance_comedy rule seen from
        the 社交放大器 anchor side): fires social_high_variance_comedy → 欢乐混乱
    With desired={"欢乐混乱"}, rank_candidates must put 欢乐混乱 at position 0.
    """
    games = [
        # Anchor: has both 永久死亡 (高方差失败源) and 共享账户 (社交放大器)
        GameDimensions(
            game_id="g_anchor",
            summary="多人肉鸽派对",
            genres={"类肉鸽", "派对游戏"},
            perspectives=set(),
            art_styles=set(),
            mechanics={"永久死亡", "共享账户"},
            theme=set(),
            game_feel=set(),
        ),
        # Source A: 连招 → 掌握曲线; fires mastery_under_permadeath → 战斗精通
        GameDimensions(
            game_id="g_mastery",
            summary="动作格斗",
            genres={"类魂"},
            perspectives=set(),
            art_styles=set(),
            mechanics={"连招"},
            theme=set(),
            game_feel=set(),
        ),
        # Source B: 老虎机 → 高方差失败源; fires social_high_variance_comedy → 欢乐混乱
        GameDimensions(
            game_id="g_slot",
            summary="派对赌场",
            genres={"派对游戏"},
            perspectives=set(),
            art_styles=set(),
            mechanics={"老虎机"},
            theme=set(),
            game_feel=set(),
        ),
    ]

    candidates = enumerate_opportunities(games, set())

    # Confirm the fixture produces at least one candidate for each target experience.
    comedy = [
        c for c in candidates
        if c.synergy is not None and c.synergy.predicted_experience == "欢乐混乱"
    ]
    mastery = [
        c for c in candidates
        if c.synergy is not None and c.synergy.predicted_experience == "战斗精通"
    ]
    assert comedy, "Fixture produced no 欢乐混乱 candidate; profile-targeting test is vacuous."
    assert mastery, "Fixture produced no 战斗精通 candidate; profile-targeting test is vacuous."

    # With desired={"欢乐混乱"}, tier-0 candidates for 欢乐混乱 must rank first.
    ranked_targeted = rank_candidates(
        candidates,
        top_n=10,
        desired_experiences={"欢乐混乱"},
    )
    assert ranked_targeted, "rank_candidates returned empty list for targeted run."
    assert ranked_targeted[0].synergy is not None, (
        "Top-ranked candidate in targeted run has no synergy."
    )
    assert ranked_targeted[0].synergy.predicted_experience == "欢乐混乱", (
        f"Profile-targeting FAILED: top candidate has "
        f"predicted_experience={ranked_targeted[0].synergy.predicted_experience!r}, "
        f"expected '欢乐混乱' with desired={{'欢乐混乱'}}."
    )

    # Without desired, synergy candidates still rank above wildcards but the
    # specific ordering between 欢乐混乱 and 战斗精通 is not prescribed — just
    # confirm the top is still a synergy candidate (tier ≤ 1).
    ranked_open = rank_candidates(candidates, top_n=10, desired_experiences=set())
    assert ranked_open, "rank_candidates returned empty list for open run."
    assert ranked_open[0].synergy is not None, (
        "Top-ranked candidate in open run has no synergy (expected synergy-first ordering)."
    )
