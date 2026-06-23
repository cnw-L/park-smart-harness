"""audited_store.py — ConversationStore 装饰器:热 store + per-boundary PG 审计 (§六补 A1).

设计要点:
- AuditedConversationStore 满足 ConversationStore 协议(load/commit/latest_boundary/
  resolve_pending),可无缝替换进 run_loop(store=...) 而无需改动 loop.py。
- 读不审计:load / latest_boundary 直接委托给 inner store,不写审计行。
- 写才审计:commit / resolve_pending 先委托 inner,成功后调 _audit_safe。
- **审计是 best-effort,非阻断**:
    inner.commit 成功后再 audit_boundary;audit 写失败 → log warning + 继续。
    理由:边界已落热 store;把 audit 做成硬阻断只会给已提交的边界造假保证,
    同时让一个 PG 抖动拖垮整个会话。审计作为崩溃重建真相源 + 跨后端原子性
    是另一回事(后续韧性方向),不在此实现范围内。
- audit 参数宽松类型:接受任意 `audit_boundary(thread_id, boundary)` 的对象
    (PgAuditLog 实例即可;若 PgAuditLog 被 PgStore 持有,直接传 PgAuditLog 即可)。
- aclose():若 inner / audit 对象有 aclose 则调用(自持资源管理)。
"""
from __future__ import annotations

import logging
from typing import Any

from .conversation import Boundary, Conversation, ConversationStore
from .messages import Message

_log = logging.getLogger(__name__)


class AuditedConversationStore:
    """ConversationStore 装饰器:委托热 store + 每边界 append-only 审计到 PG(§六补)。

    审计是 best-effort:inner.commit 成功后再审计;审计写失败 → log warning、不阻断
    (边界已落热 store,硬阻断只会给假保证还拖垮会话)。审计作为崩溃重建真相源 +
    跨后端原子是另一回事(后续韧性),不在此。

    参数:
        inner : 实现 ConversationStore 协议的热 store(如 RedisConversationStore
                或 InMemoryConversationStore)。
        audit : 任意拥有 `async audit_boundary(thread_id, boundary)` 方法的对象
                (生产侧传 PgAuditLog 实例;测试侧传 FakeAudit)。
    """

    def __init__(self, inner: ConversationStore, audit: Any) -> None:
        self._inner = inner
        self._audit = audit

    # ------------------------------------------------------------------
    # ConversationStore 协议 — 读不审计
    # ------------------------------------------------------------------

    async def load(self, thread_id: str) -> Conversation:
        """委托热 store;读不产生审计行。"""
        return await self._inner.load(thread_id)

    async def latest_boundary(self, thread_id: str) -> Boundary | None:
        """委托热 store;读不产生审计行。"""
        return await self._inner.latest_boundary(thread_id)

    # ------------------------------------------------------------------
    # ConversationStore 协议 — 写:先内层,再 best-effort 审计
    # ------------------------------------------------------------------

    async def commit(
        self,
        thread_id: str,
        new_messages: list[Message],
        boundary: Boundary,
    ) -> None:
        """原子提交到热 store,再审计到 PG。

        **B/C 分流(§九 缺口①,经行业评估)**:含控制动作的边界(`pending_batch` 非空,
        即挂起冻结了不可逆控制)→ 审计**必须成功否则上抛**(loop 的 _safe_commit 转 _PersistError);
        纯对话边界 → best-effort。
        作用域说明:这保证的是**控制边界的 PG durability**(联动驱逐安全 + 审计齐全)——
        否则 PG 静默写失败 + 驱逐 = 永久丢控制边界。它**不是**"执行前留痕"那种 fail-closed
        (那是控制能力子系统里"先写台账 pending→executing 再调 deviceCtrl"的顺序,另一层)。
        """
        await self._inner.commit(thread_id, new_messages, boundary)
        if boundary.pending_batch:
            await self._audit.audit_boundary(thread_id, boundary)   # C:强制,失败上抛
        else:
            await self._audit_safe(thread_id, boundary)             # B:best-effort

    async def resolve_pending(
        self,
        thread_id: str,
        resolved: dict[str, Message],
        boundary: Boundary,
    ) -> None:
        """解析 pending 并提交到热 store,再**强制**审计到 PG。

        resolve_pending = 控制已被解析(执行/拒绝),是 C 路径核心 → 审计必达否则上抛(fail-closed)。
        """
        await self._inner.resolve_pending(thread_id, resolved, boundary)
        await self._audit.audit_boundary(thread_id, boundary)       # C:强制,失败上抛

    # ------------------------------------------------------------------
    # 内部:best-effort 审计
    # ------------------------------------------------------------------

    async def _audit_safe(self, thread_id: str, boundary: Boundary) -> None:
        """调 audit_boundary;失败只记 warning,绝不上抛。"""
        try:
            await self._audit.audit_boundary(thread_id, boundary)
        except Exception as exc:
            _log.warning(
                "审计失败 thread=%s seq=%s: %s",
                thread_id,
                boundary.seq,
                exc,
            )

    # ------------------------------------------------------------------
    # 资源管理
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        """关掉我们拥有的资源(若 inner/audit 有 aclose 就调)。"""
        inner_close = getattr(self._inner, "aclose", None)
        if callable(inner_close):
            await inner_close()
        audit_close = getattr(self._audit, "aclose", None)
        if callable(audit_close):
            await audit_close()
