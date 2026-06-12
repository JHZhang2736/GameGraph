"""
Hybrid opportunity enumeration – validation harness (H-Task 4)

Three scenarios that prove the synergy prior changes / improves enumeration:

  Test 1 – 留一法重新发现 (leave-one-out rediscovery)
    No single library game exemplifies the "社交放大器 × 高方差失败源 → 欢乐混乱"
    pairing, yet the hybrid engine re-discovers the opportunity from the role layer alone.

  Test 2 – 跨维度可达性 (cross-dimension reachability)
    A synergy completable only via a Theme carrier IS produced by the hybrid engine
    (flag ON) but NOT by attribute-only enumeration (flag OFF).

  Test 3 – 消融 (ablation)
    Same games + same desired_experiences, flag ON vs OFF.  The ranked Top-N
    candidate id sets differ, and at least one tier-0 candidate (synergy whose
    predicted_experience ∈ desired_experiences) that is present with flag ON is
    absent / lower-ranked when flag OFF.
"""

from __future__ import annotations

import pytest

from app.services.opportunity_service import (
    GameDimensions,
    enumerate_candidates,
    rank_candidates,
)


# ---------------------------------------------------------------------------
# Test 1: 留一法重新发现
# Neither game has BOTH 永久死亡 (高方差失败源) AND 共享账户 (社交放大器).
# The engine must rediscover the "欢乐混乱" opportunity from the role layer.
# ---------------------------------------------------------------------------


def test_leave_one_out_rediscovery(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Validates that the rule-driven path re-discovers an opportunity region
    even when no single library game exemplifies the full synergy pairing.

    Anchor: 永久死亡 (高方差失败源)  ← no 共享账户
    Other:  共享账户 (社交放大器)    ← no 永久死亡

    Rule social_high_variance_comedy: 高方差失败源 × 社交放大器 → 欢乐混乱
    Expected: a candidate exists with synergy.predicted_experience == "欢乐混乱",
    and with desired_experiences={"欢乐混乱"} it rises to Top-N position 0.
    """
    monkeypatch.setenv("SYNERGY_RANKING", "1")

    games = [
        # Anchor: has 永久死亡 (高方差失败源 via Mechanic); no 共享账户
        GameDimensions(
            game_id="g_permadeath",
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
            game_id="g_party",
            summary="多人派对游戏",
            genres={"派对游戏"},
            perspectives=set(),
            art_styles=set(),
            mechanics={"共享账户"},
            theme=set(),
            game_feel=set(),
        ),
    ]

    candidates = enumerate_candidates(games)

    # At least one candidate from anchor g_permadeath should target 共享账户
    # with synergy predicting 欢乐混乱 (rule social_high_variance_comedy).
    # Note: _combine_candidates (Mechanic path) already annotates with rationale_for(),
    # so this candidate arrives via the standard combine path — confirmed by synergy tag.
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
# Rule-driven generates a Theme-dimension candidate (flag ON);
# attribute-only enumeration (flag OFF) produces no Theme-dimension candidates.
# ---------------------------------------------------------------------------


def test_cross_dimension_reachability(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Validates that the hybrid engine generates cross-dimension Theme candidates
    (flag ON) that are absent under attribute-only enumeration (flag OFF).

    Anchor: 资源管理 (资源张力 via Mechanic)
    Source: Theme 生存恐怖 (恐惧张力)

    Rule dread_scarcity_atmosphere: 恐惧张力 × 资源张力 → 氛围营造
    Flag ON:  Theme-dimension candidate exists with to_value="生存恐怖",
              synergy.predicted_experience == "氛围营造".
    Flag OFF: No Theme-dimension candidate exists.
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
            mechanics={"追猎者"},
            theme={"生存恐怖"},
            game_feel=set(),
        ),
    ]

    # --- flag ON ---
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    candidates_on = enumerate_candidates(games)

    theme_candidates = [
        c
        for c in candidates_on
        if c.anchor_game_id == "g_survival"
        and c.transformation.dimension == "Theme"
        and c.transformation.to_value == "生存恐怖"
    ]
    assert theme_candidates, (
        "Flag ON: expected a Theme-dimension candidate targeting '生存恐怖' "
        "for anchor g_survival, but none found."
    )
    assert theme_candidates[0].synergy is not None, (
        "Flag ON: Theme candidate exists but has no synergy annotation."
    )
    assert theme_candidates[0].synergy.predicted_experience == "氛围营造", (
        f"Flag ON: expected predicted_experience='氛围营造', "
        f"got {theme_candidates[0].synergy.predicted_experience!r}."
    )

    # --- flag OFF ---
    monkeypatch.setenv("SYNERGY_RANKING", "0")
    candidates_off = enumerate_candidates(games)

    theme_candidates_off = [
        c for c in candidates_off if c.transformation.dimension == "Theme"
    ]
    assert not theme_candidates_off, (
        f"Flag OFF: unexpected Theme-dimension candidates: "
        f"{[c.id for c in theme_candidates_off]}"
    )


# ---------------------------------------------------------------------------
# Test 3: 消融 (ablation)
# Same games + same desired_experiences; ranked Top-N ids DIFFER between
# flag ON and OFF; flag ON produces at least one tier-0 candidate absent
# from flag OFF output.
# ---------------------------------------------------------------------------


def test_ablation_synergy_flag_changes_ranked_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Ablation: compares ranked Top-N under flag ON vs flag OFF with the same
    game library and desired_experiences.

    The id sets must differ between the two runs, and at least one tier-0
    candidate (synergy.predicted_experience ∈ desired_experiences) that
    appears in flag-ON top results must be absent from flag-OFF results.

    Fixture: anchor has 永久死亡 (高方差失败源); another game provides
    共享账户 (社交放大器).  desired_experiences={"欢乐混乱"}.
    """
    desired = {"欢乐混乱"}

    # Rich enough fixture: anchor g_anchor has 永久死亡.
    # g_social provides 共享账户 (社交放大器).
    # g_plain provides a plain mechanic (回合制) that creates a non-synergy candidate.
    games = [
        GameDimensions(
            game_id="g_anchor",
            summary="肉鸽闯关，永久死亡",
            genres={"类肉鸽"},
            perspectives=set(),
            art_styles=set(),
            mechanics={"永久死亡"},
            theme=set(),
            game_feel=set(),
        ),
        GameDimensions(
            game_id="g_social",
            summary="多人派对，共享账户",
            genres={"派对游戏"},
            perspectives=set(),
            art_styles=set(),
            mechanics={"共享账户"},
            theme=set(),
            game_feel=set(),
        ),
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

    # --- flag ON ---
    monkeypatch.setenv("SYNERGY_RANKING", "1")
    candidates_on = enumerate_candidates(games)
    ranked_on = rank_candidates(candidates_on, top_n=10, desired_experiences=desired)

    # --- flag OFF ---
    monkeypatch.setenv("SYNERGY_RANKING", "0")
    candidates_off = enumerate_candidates(games)
    ranked_off = rank_candidates(candidates_off, top_n=10, desired_experiences=desired)

    ids_on = {c.id for c in ranked_on}
    ids_off = {c.id for c in ranked_off}

    assert ids_on != ids_off, (
        "Ablation FAILED: ranked Top-N candidate id sets are identical under "
        "flag ON and flag OFF — synergy prior has no observable effect."
    )

    # Collect tier-0 candidates from flag ON (synergy.predicted_experience ∈ desired)
    tier0_on = [
        c
        for c in ranked_on
        if c.synergy is not None and c.synergy.predicted_experience in desired
    ]
    assert tier0_on, (
        "Flag ON: no tier-0 candidate with predicted_experience ∈ desired_experiences "
        "found in ranked output — synergy-aware ranking produced nothing observable."
    )

    # At least one such tier-0 candidate must be absent from flag-OFF ranked output
    tier0_ids_absent_in_off = {c.id for c in tier0_on} - ids_off
    assert tier0_ids_absent_in_off, (
        "Ablation FAILED: all tier-0 (欢乐混乱) candidates from flag-ON ranking are "
        "also present in flag-OFF ranking — synergy prior shows no exclusive uplift."
    )
