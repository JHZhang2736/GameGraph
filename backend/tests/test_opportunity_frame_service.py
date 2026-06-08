from app.schemas.artifacts import OpportunityFrame


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
