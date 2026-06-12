from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

from app.schemas.opportunity import FunctionalRole, SynergyRationale, SynergyRule

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


_DIMENSIONS = ("Mechanic", "GameFeel", "Theme", "Genre")


@lru_cache(maxsize=1)
def load_element_roles() -> dict[str, frozenset[FunctionalRole]]:
    """核心四段元素名 -> 它扮演的功能角色集合（去重并集）。非法角色键响亮失败。"""
    raw = json.loads((_FIXTURES / "element_roles.json").read_text(encoding="utf-8"))
    table: dict[str, set[FunctionalRole]] = defaultdict(set)
    for role_value, buckets in raw["roles"].items():
        role = FunctionalRole(role_value)
        for dim_terms in buckets.values():
            for term in dim_terms:
                table[term].add(role)
    return {term: frozenset(roles) for term, roles in table.items()}


@lru_cache(maxsize=1)
def load_element_dimensions() -> dict[str, frozenset[str]]:
    """核心四段元素名 -> 它出现在哪些维度（Mechanic/GameFeel/Theme/Genre）。"""
    raw = json.loads((_FIXTURES / "element_roles.json").read_text(encoding="utf-8"))
    out: dict[str, set[str]] = defaultdict(set)
    for buckets in raw["roles"].values():
        for dim, terms in buckets.items():
            for term in terms:
                out[term].add(dim)
    return {term: frozenset(dims) for term, dims in out.items()}


@lru_cache(maxsize=1)
def elements_for_role() -> dict[FunctionalRole, frozenset[tuple[str, str]]]:
    """功能角色 -> {(元素, 维度)} 全量映射；调用方用 elements_for_role()[role] 取单角色。"""
    raw = json.loads((_FIXTURES / "element_roles.json").read_text(encoding="utf-8"))
    out: dict[FunctionalRole, set[tuple[str, str]]] = defaultdict(set)
    for role_value, buckets in raw["roles"].items():
        role = FunctionalRole(role_value)
        for dim, terms in buckets.items():
            for term in terms:
                out[role].add((term, dim))
    return {role: frozenset(pairs) for role, pairs in out.items()}


@lru_cache(maxsize=1)
def load_synergy_rules() -> tuple[SynergyRule, ...]:
    raw = json.loads((_FIXTURES / "synergy_rules.json").read_text(encoding="utf-8"))
    return tuple(SynergyRule.model_validate(rule) for rule in raw["rules"])


def roles_for_elements(
    elements: Iterable[str],
    table: dict[str, frozenset[FunctionalRole]] | None = None,
) -> set[FunctionalRole]:
    """一组核心四段元素覆盖的功能角色并集；表里没有的元素不贡献角色。"""
    lookup = load_element_roles() if table is None else table
    out: set[FunctionalRole] = set()
    for element in elements:
        out |= lookup.get(element, frozenset())
    return out


def find_synergy(
    anchor_roles: set[FunctionalRole],
    borrowed_roles: set[FunctionalRole],
    rules: Iterable[SynergyRule] | None = None,
) -> tuple[SynergyRule, FunctionalRole, FunctionalRole] | None:
    """返回第一条被「锚点出一角色、借入出另一角色」点亮的规则及具体角色对
    (rule, anchor_role, borrowed_role)；无则 None。规则对称：任一方向命中即可。"""
    for rule in (load_synergy_rules() if rules is None else rules):
        if rule.role_a in anchor_roles and rule.role_b in borrowed_roles:
            return rule, rule.role_a, rule.role_b
        if rule.role_b in anchor_roles and rule.role_a in borrowed_roles:
            return rule, rule.role_b, rule.role_a
    return None


def rationale_for(
    anchor_elements: Iterable[str],
    borrowed_mechanic: str,
    *,
    table: dict[str, frozenset[FunctionalRole]] | None = None,
    rules: Iterable[SynergyRule] | None = None,
) -> SynergyRationale | None:
    """锚点四段元素 + 一个借入机制 -> 协同理由；不点亮任何规则则 None。"""
    lookup = load_element_roles() if table is None else table
    hit = find_synergy(
        roles_for_elements(anchor_elements, lookup),
        set(lookup.get(borrowed_mechanic, frozenset())),
        rules,
    )
    if hit is None:
        return None
    rule, anchor_role, borrowed_role = hit
    return SynergyRationale(
        rule_id=rule.id,
        anchor_role=anchor_role,
        borrowed_role=borrowed_role,
        predicted_experience=rule.experience,
    )
