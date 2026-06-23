"""登录链接缝(设计 §三/§六)—— 把后端权限结果编译成 harness 有效能力集。

组件化、不被后端格式卡住:
- `PermissionMapper`:后端 RuoYi 码 → harness 能力码。`IdentityMapper` 默认直通(后端样例未到先兜);
  `TableMapper` 可配映射表(真码到了填规则,主链路不改)。
- `OrgPolicy`:harness 自持的 org 策略,按 roleKey **强制禁用**某些能力码(叠在角色权限上,
  个人越不过)。后端不提供此层=AI 治理范畴。
- `resolve_capabilities`:登录时确权一次 → 有效能力集(冻进 `principal.permissions`)。

**只吃能力级**(permissions+apiPermissions);资源级(devicePermission/dataScope)不进这里,留后端 token。
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol


class PermissionMapper(Protocol):
    def map(self, raw_codes: Iterable[str]) -> set[str]: ...


class IdentityMapper:
    """直通:后端码即 harness 码(真码样例未到时的安全占位)。"""

    def map(self, raw_codes: Iterable[str]) -> set[str]:
        return {c for c in raw_codes if c}


@dataclass
class TableMapper:
    """可配映射:后端码 → harness 能力码。未在表中的码**丢弃**(strict,deny-first 一致)。"""

    table: dict[str, str]

    def map(self, raw_codes: Iterable[str]) -> set[str]:
        return {self.table[c] for c in raw_codes if c in self.table}


@dataclass(frozen=True)
class OrgPolicy:
    """org 策略(harness 自持):按 roleKey 强制禁用能力码。`deny_by_role['*']` = 对所有角色生效。"""

    deny_by_role: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def apply(self, role_key: str, codes: set[str]) -> set[str]:
        denied = set(self.deny_by_role.get("*", ())) | set(self.deny_by_role.get(role_key, ()))
        return codes - denied


def resolve_capabilities(raw_codes: Iterable[str], role_key: str = "", *,
                         mapper: PermissionMapper | None = None,
                         org_policy: OrgPolicy | None = None) -> tuple[str, ...]:
    """登录确权:后端能力码 → 映射 → 叠 org 策略 → 有效能力集(排序去重,冻进 session)。"""
    codes = (mapper or IdentityMapper()).map(raw_codes)
    if org_policy is not None:
        codes = org_policy.apply(role_key, codes)
    return tuple(sorted(codes))
