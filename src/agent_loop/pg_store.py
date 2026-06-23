"""pg_store.py — Postgres 幂等键台账 + 审计追加日志 (P3).

设计要点（§六补 Postgres layer）:
- agentloop_idem  : idem_key PRIMARY KEY → ON CONFLICT DO NOTHING → 精确一次语义
- agentloop_audit : append-only 审计，encode_boundary 序列化后存 JSONB
- PgIdempotencyLedger  : get / put_if_absent 两个方法
- PgControlCapability  : 与 FakeControlCapability 镜像语义，ledger 换 PG
- 连接懒建（首次 I/O 时）；schema bootstrap 每实例只运行一次（flag 守卫）
"""
from __future__ import annotations

import json
import os
from typing import Any
from uuid import uuid4

from .codec import encode_boundary
from .conversation import Boundary
from .messages import ToolCallReq
from .pending import PendingAction
from .tools import ToolResult

# ---------------------------------------------------------------------------
# 默认 DSN
# ---------------------------------------------------------------------------

_DEFAULT_DSN = "postgresql://postgres:postgres@localhost:5432/smart_park"


def _resolve_dsn(dsn: str | None) -> str:
    if dsn is not None:
        return dsn
    return os.getenv("SPA_STORAGE__POSTGRES_DSN", _DEFAULT_DSN)


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS agentloop_idem (
    idem_key    text PRIMARY KEY,
    status      text NOT NULL,
    result_json jsonb,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS agentloop_audit (
    id              bigserial PRIMARY KEY,
    thread_id       text NOT NULL,
    seq             int,
    boundary_status text,
    payload         jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
"""


# ---------------------------------------------------------------------------
# PgStore — 共享连接池 + schema bootstrap
# ---------------------------------------------------------------------------

class PgStore:
    """Postgres 连接池封装：懒建池，schema 只 bootstrap 一次。

    参数:
        dsn  : Postgres DSN；None → 读 SPA_STORAGE__POSTGRES_DSN env → 默认 90 节点。
        pool : 可注入的 asyncpg Pool（测试用）；为 None 时第一次 I/O 延迟建池。
    """

    def __init__(self, *, dsn: str | None = None, pool: Any = None) -> None:
        self._dsn = _resolve_dsn(dsn)
        self._pool: Any = pool
        # 注入池 → 不拥有（不应关闭）
        self._pool_owned: bool = pool is None
        self._schema_ready: bool = False

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    async def _get_pool(self) -> Any:
        """延迟建池（第一次 I/O 才真正连接）。"""
        if self._pool is None:
            import asyncpg  # type: ignore[import]
            self._pool = await asyncpg.create_pool(self._dsn)
        return self._pool

    async def _ensure_schema(self) -> None:
        """运行 DDL：CREATE TABLE IF NOT EXISTS（幂等）；flag 守卫只运行一次。"""
        if self._schema_ready:
            return
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(_DDL)
        self._schema_ready = True

    async def aclose(self) -> None:
        """关闭自建池（注入池不关）。"""
        if self._pool is not None and self._pool_owned:
            await self._pool.close()
            self._pool = None


# ---------------------------------------------------------------------------
# PgIdempotencyLedger
# ---------------------------------------------------------------------------

class PgIdempotencyLedger:
    """Postgres 幂等键台账（包装同一个 PgStore）。"""

    def __init__(self, store: PgStore) -> None:
        self._store = store

    async def get(self, idem_key: str) -> dict | None:
        """查询 idem_key → 返回 result_json dict 或 None（不存在）。"""
        await self._store._ensure_schema()
        pool = await self._store._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT result_json FROM agentloop_idem WHERE idem_key=$1",
                idem_key,
            )
        if row is None:
            return None
        # asyncpg 返回 jsonb 字段为 str，需手动 loads
        raw = row["result_json"]
        if isinstance(raw, str):
            return json.loads(raw)
        # asyncpg 某些版本直接返回 dict
        return dict(raw)

    async def put_if_absent(
        self, idem_key: str, status: str, result: dict
    ) -> bool:
        """INSERT … ON CONFLICT (idem_key) DO NOTHING.

        返回 True → 本次成功写入（首次）；False → 已存在（冲突，幂等忽略）。
        """
        await self._store._ensure_schema()
        pool = await self._store._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO agentloop_idem(idem_key, status, result_json)
                VALUES ($1, $2, $3::jsonb)
                ON CONFLICT (idem_key) DO NOTHING
                RETURNING idem_key
                """,
                idem_key,
                status,
                json.dumps(result),
            )
        return row is not None


# ---------------------------------------------------------------------------
# PgControlCapability
# ---------------------------------------------------------------------------

class PgControlCapability:
    """Postgres 幂等键实现的 ControlCapability（P3 生产侧）.

    与 FakeControlCapability 镜像语义：
      - freeze()  : 铸造 PendingAction（idem_key = uuid4().hex）
      - resolve() :
          reject → 直接返回 [rejected] 结果，不写台账
          approve → 检查 ledger，已存在则返回缓存；否则桩执行并写台账
                    写入冲突（并发）→ re-get 返回存储结果（不计 execute_count）
    注意：deviceCtrl 实际调用仍为桩（echo），待后端补充 commandId + 幂等键后替换。
    """

    def __init__(self, store: PgStore) -> None:
        self._store = store
        self._ledger = PgIdempotencyLedger(store)
        # 真实执行计数（幂等重入不增加）
        self.execute_count: int = 0

    def freeze(self, call: ToolCallReq) -> PendingAction:
        """铸造 PendingAction：每次产生全新 idem_key，args 深拷贝。"""
        idem_key = uuid4().hex
        frozen_action = {"name": call.name, "arguments": dict(call.arguments)}
        return PendingAction(
            tool_call_id=call.id,
            idem_key=idem_key,
            frozen_action=frozen_action,
            handle=None,
        )

    async def resolve(self, pending: PendingAction, decision: str) -> ToolResult:
        """执行或拒绝冻结动作。

        approve 路径：
          1. 台账已有 → 返回缓存（不重执行，execute_count 不变）
          2. 台账无   → 桩执行 → 写台账（ON CONFLICT）
             若 ON CONFLICT（并发竞态） → re-get 返回存储结果，不计 execute_count
        reject 路径：不写台账，直接返回 [rejected]。
        """
        name = pending.frozen_action["name"]

        if decision == "reject":
            return ToolResult(ok=True, content=f"[rejected] {name} not executed")

        if decision == "approve":
            # 幂等检查
            cached = await self._ledger.get(pending.idem_key)
            if cached is not None:
                return ToolResult(
                    ok=cached.get("ok", True),
                    content=cached.get("content", ""),
                    error=cached.get("error"),
                )

            # 首次执行：桩实现（echo）
            arguments = pending.frozen_action["arguments"]
            idem_key = pending.idem_key
            result = ToolResult(
                ok=True,
                content=(
                    f"[executed] {name} args={arguments} "
                    f"(idem={idem_key}) readback=ok"
                ),
            )

            result_dict = {
                "ok": result.ok,
                "content": result.content,
                "error": result.error,
            }
            inserted = await self._ledger.put_if_absent(
                idem_key, "executed", result_dict
            )

            if not inserted:
                # 并发写者先到：取存储结果，不增加计数
                stored = await self._ledger.get(idem_key)
                if stored is not None:
                    return ToolResult(
                        ok=stored.get("ok", True),
                        content=stored.get("content", ""),
                        error=stored.get("error"),
                    )
                # 极端情况（几乎不可能）：get 仍拿不到，降级返回本地结果
                return result

            self.execute_count += 1
            return result

        # 防御：未知 decision
        return ToolResult(ok=False, content="", error="unknown decision")


# ---------------------------------------------------------------------------
# 审计日志
# ---------------------------------------------------------------------------

class PgAuditLog:
    """Boundary 审计追加日志（P3）。只写不改，供事后审查。"""

    def __init__(self, store: PgStore) -> None:
        self._store = store

    async def audit_boundary(self, thread_id: str, boundary: Boundary) -> None:
        """追加一条审计记录（append-only，不改历史）。"""
        await self._store._ensure_schema()
        pool = await self._store._get_pool()
        payload = json.dumps(encode_boundary(boundary))
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO agentloop_audit(thread_id, seq, boundary_status, payload)
                VALUES ($1, $2, $3, $4::jsonb)
                """,
                thread_id,
                boundary.seq,
                boundary.status,
                payload,
            )

    async def read_audit(self, thread_id: str) -> list[dict]:
        """返回该 thread 的全部审计 payload 列表（按 id 升序）。"""
        await self._store._ensure_schema()
        pool = await self._store._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT payload FROM agentloop_audit
                WHERE thread_id=$1
                ORDER BY id ASC
                """,
                thread_id,
            )
        result = []
        for row in rows:
            raw = row["payload"]
            if isinstance(raw, str):
                result.append(json.loads(raw))
            else:
                result.append(dict(raw))
        return result
