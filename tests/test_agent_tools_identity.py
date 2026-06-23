"""V5:登录链接缝 —— PermissionMapper(直通/映射)+ OrgPolicy + resolve_capabilities。"""
from __future__ import annotations

from agent_tools.identity import (IdentityMapper, OrgPolicy, TableMapper,
                                  resolve_capabilities)


def test_identity_mapper_passthrough():
    assert IdentityMapper().map(["a", "b", ""]) == {"a", "b"}     # 直通(空丢)


def test_table_mapper_strict_drops_unmapped():
    """真码映射:表内翻译,表外丢弃(deny-first 一致)。"""
    m = TableMapper({"system:device:list": "device:read", "system:device:ctrl": "device:control"})
    assert m.map(["system:device:list", "system:device:ctrl", "system:unknown"]) == {
        "device:read", "device:control"}


def test_resolve_passthrough_default():
    assert resolve_capabilities(["device:read", "device:control"]) == ("device:control", "device:read")


def test_org_policy_force_denies_by_role():
    """org 策略:访客角色禁任何 device:control,个人权限再大也越不过。"""
    pol = OrgPolicy(deny_by_role={"guest": ("device:control",)})
    out = resolve_capabilities(["device:read", "device:control"], "guest", org_policy=pol)
    assert out == ("device:read",)                               # control 被 org 强制收紧


def test_org_policy_wildcard_applies_to_all_roles():
    pol = OrgPolicy(deny_by_role={"*": ("device:control",)})
    assert "device:control" not in resolve_capabilities(["device:control"], "admin", org_policy=pol)


def test_resolve_with_mapper_and_policy():
    """端到端:后端真码 → 映射 → 叠 org 策略 → 有效能力集。"""
    m = TableMapper({"sys:dev:list": "device:read", "sys:dev:ctrl": "device:control"})
    pol = OrgPolicy(deny_by_role={"运维员": ("device:control",)})
    out = resolve_capabilities(["sys:dev:list", "sys:dev:ctrl"], "运维员", mapper=m, org_policy=pol)
    assert out == ("device:read",)
