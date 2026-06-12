import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.schemas.opportunity import FunctionalRole, SynergyRule
from app.services import synergy


def test_element_roles_classify_known_terms() -> None:
    table = synergy.load_element_roles()
    assert FunctionalRole.HIGH_VARIANCE_FAILURE in table["老虎机"]
    assert FunctionalRole.COGNITIVE_OFFLOAD in table["老虎机"]
    assert FunctionalRole.SOCIAL_AMPLIFIER in table["共享账户"]
    assert FunctionalRole.DREAD_SOURCE in table["生存恐怖"]
    assert FunctionalRole.VISCERAL_EXECUTION in table["爽快射击"]


def test_roles_for_elements_unions_four_dims() -> None:
    roles = synergy.roles_for_elements(["老虎机", "共享账户", "轻松休闲", "生存恐怖"])
    assert {
        FunctionalRole.HIGH_VARIANCE_FAILURE, FunctionalRole.SOCIAL_AMPLIFIER,
        FunctionalRole.COZY_COMFORT, FunctionalRole.DREAD_SOURCE,
    } <= roles
    assert synergy.roles_for_elements(["不存在的词"]) == set()


def test_synergy_rules_load_and_cover_all_roles() -> None:
    rules = synergy.load_synergy_rules()
    assert all(isinstance(r, SynergyRule) for r in rules)
    covered = {r.role_a for r in rules} | {r.role_b for r in rules}
    assert covered == set(FunctionalRole)   # 每个角色至少被一条规则覆盖


def test_find_synergy_symmetric_hit() -> None:
    hit = synergy.find_synergy({FunctionalRole.HIGH_VARIANCE_FAILURE},
                               {FunctionalRole.SOCIAL_AMPLIFIER})
    assert hit is not None
    rule, anchor_role, borrowed_role = hit
    assert anchor_role == FunctionalRole.HIGH_VARIANCE_FAILURE
    assert borrowed_role == FunctionalRole.SOCIAL_AMPLIFIER
    rev = synergy.find_synergy({FunctionalRole.SOCIAL_AMPLIFIER},
                               {FunctionalRole.HIGH_VARIANCE_FAILURE})
    assert rev is not None and rev[1] == FunctionalRole.SOCIAL_AMPLIFIER


def test_find_synergy_miss() -> None:
    assert synergy.find_synergy({FunctionalRole.NARRATIVE_HOOK},
                                {FunctionalRole.COGNITIVE_OFFLOAD}) is None


def test_rationale_for_combine() -> None:
    r = synergy.rationale_for(["共享账户"], "老虎机")
    assert r is not None and r.predicted_experience == "欢乐混乱"
    assert synergy.rationale_for(["分支叙事"], "回合制") is None


def test_element_dimensions_lookup() -> None:
    dims = synergy.load_element_dimensions()
    assert "Mechanic" in dims["老虎机"]
    assert "GameFeel" in dims["爽快射击"]
    assert dims["生存恐怖"] == frozenset({"Theme"})   # 单归一维：Theme（题材）
    assert dims.get("不存在的词") in (None, frozenset(), set())


def test_load_elements_by_role_returns_element_dim_pairs() -> None:
    pairs = synergy.load_elements_by_role()[FunctionalRole.DREAD_SOURCE]
    assert ("生存恐怖", "Theme") in pairs
    assert ("紧张节奏", "GameFeel") in pairs
    assert ("理智系统", "Mechanic") in pairs


def test_flatten_unchanged_after_regroup() -> None:
    table = synergy.load_element_roles()
    assert FunctionalRole.HIGH_VARIANCE_FAILURE in table["老虎机"]
    assert FunctionalRole.COGNITIVE_OFFLOAD in table["老虎机"]
    assert FunctionalRole.SOCIAL_AMPLIFIER in table["共享账户"]
    assert FunctionalRole.VISCERAL_EXECUTION in table["爽快射击"]
    assert FunctionalRole.COZY_COMFORT in table["轻松休闲"]


def test_load_elements_by_role_real_data_has_no_double_homed_terms() -> None:
    """真实 fixture 加载时守卫不应触发（所有词在各自角色内单归一维）。"""
    # 确保 lru_cache 不遮蔽测试：直接构造新调用路径，使用实际文件
    synergy.load_elements_by_role.cache_clear()
    result = synergy.load_elements_by_role()
    # 只要没有抛出 ValueError，守卫通过
    assert result  # 结果非空


def test_load_elements_by_role_guard_rejects_double_homed_term(
    tmp_path: Path,
) -> None:
    """构造含跨维度双归属词的 fixture，验证守卫以 ValueError 响亮失败。"""
    bad_fixture = {
        "version": 2,
        "description": "test",
        "roles": {
            "高方差失败源": {
                "Mechanic": ["双归属词"],
                "Genre": ["双归属词"],   # 同一角色内重复出现
            }
        },
    }
    fixture_path = tmp_path / "element_roles.json"
    fixture_path.write_text(json.dumps(bad_fixture), encoding="utf-8")

    # 清除缓存并 monkeypatch _FIXTURES 指向 tmp_path
    synergy.load_elements_by_role.cache_clear()
    with patch.object(synergy, "_FIXTURES", tmp_path):
        with pytest.raises(ValueError, match="双归属词"):
            synergy.load_elements_by_role()

    # 测试后还原缓存，确保其他测试不受影响
    synergy.load_elements_by_role.cache_clear()
