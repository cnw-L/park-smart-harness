"""ToolLoader(设计 §三 登录链末段)—— 按有效能力集过滤主 toolset。

登录确权后,主模型**只看见有权的工具**(可见性 = 减选择 + 第一道安全;deny 闸是纵深兜底)。
组织与权限解耦:`top_names` 是顶层 toolset 名单(组织),`catalog` 提供每名的 `capability_code`。
"""
from __future__ import annotations

from collections.abc import Iterable

from .catalog import ToolCatalog


def select_toolset(catalog: ToolCatalog, top_names: Iterable[str],
                   permissions: Iterable[str]) -> list[str]:
    """有效能力集 ∩ 顶层 toolset → 加载的工具名。未登记的名跳过(deny-first 同理)。"""
    perms = set(permissions or ())
    out: list[str] = []
    for name in top_names:
        spec = catalog.find(name)
        if spec is not None and spec.capability_code in perms:
            out.append(name)
    return out
