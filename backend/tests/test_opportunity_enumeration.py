from app.schemas.opportunity import TransformationType
from app.services.opportunity_service import GameDimensions, enumerate_candidates


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
        c for c in candidates
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
        c for c in candidates
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
        GameDimensions("g1", "s1", {"类肉鸽"}, set(), {"像素美术"}, set()),  # 无 perspective
        GameDimensions("g2", "s2", {"类肉鸽"}, {"第一人称"}, {"低多边形"}, set()),
    ]
    candidates = enumerate_candidates(games)
    # g1 在 Perspective 上无值 → 不应为它生成任何 Perspective 替代候选
    assert not any(
        c.anchor_game_id == "g1" and c.transformation.dimension == "Perspective"
        for c in candidates
    )


def test_substitute_from_value_is_lexicographically_smallest_for_multi_value_anchor() -> None:
    games = [
        GameDimensions("g1", "s1", {"类肉鸽", "动作"}, {"横版2D"}, {"像素美术"}, set()),
        GameDimensions("g2", "s2", {"射击"}, {"横版2D"}, {"像素美术"}, set()),
    ]
    candidates = enumerate_candidates(games)
    sub = next(
        c for c in candidates
        if c.anchor_game_id == "g1" and c.transformation.dimension == "Genre"
        and c.transformation.to_value == "射击"
    )
    # anchor genres {"动作","类肉鸽"} → 词典序最小者为「动作」
    assert sub.transformation.from_value == "动作"


def test_novelty_count_counts_genre_sharing_games_with_target_value() -> None:
    games = [
        GameDimensions("g1", "s1", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, set()),
        GameDimensions("g2", "s2", {"类肉鸽"}, {"第一人称"}, {"低多边形"}, set()),
        GameDimensions("g3", "s3", {"类肉鸽"}, {"第一人称"}, {"低多边形"}, set()),
    ]
    candidates = enumerate_candidates(games)
    picked = next(
        c for c in candidates
        if c.anchor_game_id == "g1"
        and c.transformation.dimension == "Perspective"
        and c.transformation.to_value == "第一人称"
    )
    assert picked.existing_combination_count == 2
    assert set(picked.evidence.combination_game_ids) == {"g2", "g3"}
