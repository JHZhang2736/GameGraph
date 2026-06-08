from app.schemas.artifacts import DeveloperConstraint, DeveloperProfile, OpportunityFrame
from app.schemas.common import ConstraintType
from app.schemas.opportunity import (
    OpportunityArea,
    OpportunityEvidence,
    RiskPosture,
    Transformation,
    TransformationType,
)
from app.services.opportunity_service import GameDesignFacts, GameDimensions
from app.services import opportunity_frame_service as svc


def _frame_kwargs() -> dict:
    return dict(
        id="frame|opp_1",
        developer_profile_id="profile_1",
        opportunity_area="基于横版割草的机会",
        source_game_ids=["game_vs", "game_fps"],
        related_mechanics=["护符定制"],
        related_player_experiences=["紧张刺激"],
        related_constraints=["低美术成本"],
        related_innovation_patterns=["规则编辑"],
        recommended_transformations=["将 Perspective 从「横版2D」替代为「第一人称」"],
        forbidden_directions=["违反硬约束：不做联网多人"],
        evidence_path=["锚点 game_vs 提供成熟配方"],
        fit_reason="契合短局",
        risk_reason="3D 抬高美术成本",
    )


def test_opportunity_frame_warnings_defaults_to_empty() -> None:
    frame = OpportunityFrame(**_frame_kwargs())
    assert frame.warnings == []


def test_opportunity_frame_accepts_warnings() -> None:
    frame = OpportunityFrame(**_frame_kwargs(), warnings=["未配置 LLM"])
    assert frame.warnings == ["未配置 LLM"]


def _profile(constraints=None, disliked=None) -> DeveloperProfile:
    return DeveloperProfile(
        id="profile_1", team_size="solo", time_budget="三个月",
        programming_ability="强", art_ability="弱", audio_ability="弱",
        content_production_ability="有限", liked_references=["Hades"],
        disliked_references_or_mechanics=disliked if disliked is not None else ["联网多人"],
        desired_player_experiences=["短局"],
        constraints=constraints if constraints is not None else [
            DeveloperConstraint(id="c1", type=ConstraintType.HARD, statement="不做联网多人")
        ],
    )


def _area() -> OpportunityArea:
    return OpportunityArea(
        id="opp|game_vs|sub|Perspective|第一人称",
        anchor_game_id="game_vs", anchor_summary="横版割草",
        transformation=Transformation(
            type=TransformationType.SUBSTITUTE, dimension="Perspective",
            from_value="横版2D", to_value="第一人称",
        ),
        existing_combination_count=0,
        evidence=OpportunityEvidence(
            anchor_game_id="game_vs", target_value_game_ids=["game_fps"], combination_game_ids=[],
        ),
        risk_posture=RiskPosture.CHALLENGING, fit_reason="契合短局", risk_reason="3D 抬高美术成本",
    )


def _games() -> list[GameDimensions]:
    return [
        GameDimensions("game_vs", "横版割草", {"类肉鸽"}, {"横版2D"}, {"像素美术"}, {"护符定制"}),
        GameDimensions("game_fps", "第一人称射击", {"类肉鸽"}, {"第一人称"}, {"低多边形"}, {"能力树"}),
    ]


def _facts() -> list[GameDesignFacts]:
    return [
        GameDesignFacts("game_vs", ["护符定制"], ["紧张刺激"], ["低美术成本"], ["数值滚雪球"]),
        GameDesignFacts("game_fps", ["能力树"], ["爽快射击"], ["低多边形可控"], ["快速重开"]),
    ]


def test_source_game_ids_is_dedup_closure() -> None:
    assert svc._source_game_ids(_area()) == ["game_vs", "game_fps"]


def test_union_related_preserves_order_and_dedups() -> None:
    mechanics, experiences, constraints, innovations = svc._union_related(_facts())
    assert mechanics == ["护符定制", "能力树"]
    assert experiences == ["紧张刺激", "爽快射击"]
    assert constraints == ["低美术成本", "低多边形可控"]
    assert innovations == ["数值滚雪球", "快速重开"]


def test_describe_transformation_substitute_and_combine() -> None:
    sub = Transformation(type=TransformationType.SUBSTITUTE, dimension="Perspective",
                         from_value="横版2D", to_value="第一人称")
    comb = Transformation(type=TransformationType.COMBINE, dimension="Mechanic",
                          from_value=None, to_value="卡牌构筑")
    assert svc._describe_transformation(sub) == "将 Perspective 从「横版2D」替代为「第一人称」"
    assert svc._describe_transformation(comb) == "在 Mechanic 维度组合借入「卡牌构筑」"


def test_evidence_path_starts_with_anchor() -> None:
    path = svc._evidence_path(_area())
    assert path[0].startswith("锚点 game_vs")
    assert any("第一人称" in line for line in path)
    assert any("现存游戏数 = 0" in line for line in path)


def test_forbidden_base_includes_hard_constraint_and_dislikes() -> None:
    base = svc._forbidden_base(_profile())
    assert any("违反硬约束：不做联网多人" in x for x in base)
    assert any("联网多人" in x for x in base)


def test_forbidden_base_never_empty_without_constraints() -> None:
    profile = _profile(
        constraints=[DeveloperConstraint(id="c1", type=ConstraintType.SOFT_PREFERENCE, statement="偏好短局")],
        disliked=[],
    )
    base = svc._forbidden_base(profile)
    assert len(base) >= 1
    assert any("证据范围" in x for x in base)


def test_secondary_pool_excludes_selected_and_is_same_anchor() -> None:
    pool = svc._secondary_pool(_StubRepo(_games(), _facts()), _area())
    assert all(c.anchor_game_id == "game_vs" for c in pool)
    assert all(c.id != _area().id for c in pool)


class _StubRepo:
    def __init__(self, games, facts) -> None:
        self._games = games
        self._facts = facts

    def fetch_game_dimensions(self):
        return self._games

    def fetch_game_design_facts(self, game_ids):
        return [f for f in self._facts if f.game_id in game_ids]
