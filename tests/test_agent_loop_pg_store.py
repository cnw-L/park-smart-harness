"""Tests for agent_loop.pg_store — PgIdempotencyLedger + PgControlCapability + PgAuditLog (P3).

实时测试（live tests）：需要 Postgres @ localhost:5432/smart_park。
运行方式：AGENT_LOOP_LIVE_INFRA=1 python -m pytest tests/test_agent_loop_pg_store.py -v

离线测试（offline，零 I/O）：在 test_agent_loop_pg_store_offline.py（不受本文件 pytestmark 影响）。
"""
from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest

from agent_loop.codec import decode_boundary
from agent_loop.conversation import Boundary
from agent_loop.messages import ToolCallReq
from agent_loop.pending import PendingAction
from agent_loop.pg_store import (
    PgAuditLog,
    PgControlCapability,
    PgIdempotencyLedger,
    PgStore,
)

# ---------------------------------------------------------------------------
# 实时测试门控：无 AGENT_LOOP_LIVE_INFRA=1 时全部跳过
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    os.getenv("AGENT_LOOP_LIVE_INFRA") != "1",
    reason="set AGENT_LOOP_LIVE_INFRA=1 for live postgres @ localhost:5432",
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def run(coro):
    """同步运行协程（无 pytest-asyncio 依赖）。"""
    return asyncio.run(coro)


def _unique_key(prefix: str = "test") -> str:
    """每个测试用唯一 key，避免冲突，便于清理。"""
    return f"{prefix}_{uuid4().hex}"


def _call(name: str = "open_gate", args: dict | None = None, cid: str = "tc-001") -> ToolCallReq:
    return ToolCallReq(id=cid, name=name, arguments=args or {"gate_id": "G1"})


def _make_store() -> PgStore:
    """每个测试用新 PgStore（独立连接池）。"""
    return PgStore()


async def _cleanup_idem(store: PgStore, *keys: str) -> None:
    """删除测试产生的 idem_key 行（按精确 key，不 LIKE 通配）。"""
    pool = await store._get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM agentloop_idem WHERE idem_key = ANY($1::text[])",
            list(keys),
        )


async def _cleanup_audit(store: PgStore, thread_id: str) -> None:
    """删除该 thread_id 的全部审计行。"""
    pool = await store._get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM agentloop_audit WHERE thread_id=$1",
            thread_id,
        )


# ---------------------------------------------------------------------------
# T1: PgIdempotencyLedger — put_if_absent / get 基本语义
# ---------------------------------------------------------------------------

def test_ledger_put_if_absent_first_call_returns_true():
    """首次写入返回 True（插入成功）。"""
    store = _make_store()
    ledger = PgIdempotencyLedger(store)
    idem_key = _unique_key("test_idem_put")

    async def _run():
        try:
            result = {"ok": True, "content": "hello", "error": None}
            inserted = await ledger.put_if_absent(idem_key, "executed", result)
            return inserted
        finally:
            await _cleanup_idem(store, idem_key)
            await store.aclose()

    assert run(_run()) is True


def test_ledger_put_if_absent_duplicate_returns_false():
    """相同 idem_key 二次写入返回 False（ON CONFLICT，幂等忽略）。"""
    store = _make_store()
    ledger = PgIdempotencyLedger(store)
    idem_key = _unique_key("test_idem_dup")

    async def _run():
        try:
            result = {"ok": True, "content": "first", "error": None}
            first = await ledger.put_if_absent(idem_key, "executed", result)
            second_result = {"ok": True, "content": "second", "error": None}
            second = await ledger.put_if_absent(idem_key, "executed", second_result)
            return first, second
        finally:
            await _cleanup_idem(store, idem_key)
            await store.aclose()

    first, second = run(_run())
    assert first is True
    assert second is False


def test_ledger_get_returns_first_stored_result_unchanged():
    """get 返回首次写入的 result；第二次同 key 写入被忽略，get 仍返回首次内容。"""
    store = _make_store()
    ledger = PgIdempotencyLedger(store)
    idem_key = _unique_key("test_idem_get")

    async def _run():
        try:
            first_result = {"ok": True, "content": "original_content", "error": None}
            await ledger.put_if_absent(idem_key, "executed", first_result)
            # 尝试覆盖（应被忽略）
            second_result = {"ok": True, "content": "should_not_appear", "error": None}
            await ledger.put_if_absent(idem_key, "executed", second_result)
            stored = await ledger.get(idem_key)
            return stored
        finally:
            await _cleanup_idem(store, idem_key)
            await store.aclose()

    stored = run(_run())
    assert stored is not None
    assert stored["content"] == "original_content"


def test_ledger_get_missing_key_returns_none():
    """不存在的 idem_key → get 返回 None。"""
    store = _make_store()
    ledger = PgIdempotencyLedger(store)
    idem_key = _unique_key("test_idem_miss")

    async def _run():
        try:
            return await ledger.get(idem_key)
        finally:
            await store.aclose()

    assert run(_run()) is None


# ---------------------------------------------------------------------------
# T2: PgControlCapability — freeze + approve（首次执行）
# ---------------------------------------------------------------------------

def test_pg_control_approve_executes_and_increments_count():
    """approve → 首次执行：execute_count==1，结果含 [executed] + readback=ok。"""
    store = _make_store()
    cap = PgControlCapability(store)

    async def _run():
        pending = cap.freeze(_call())
        try:
            result = await cap.resolve(pending, "approve")
            return result, cap.execute_count, pending.idem_key
        finally:
            await _cleanup_idem(store, pending.idem_key)
            await store.aclose()

    result, count, idem_key = run(_run())
    assert result.ok
    assert "[executed]" in result.content
    assert "readback=ok" in result.content
    assert count == 1


# ---------------------------------------------------------------------------
# T3: PgControlCapability — 幂等测试（核心：同一 pending 二次 approve）
# ---------------------------------------------------------------------------

def test_pg_control_idempotency_second_approve_no_reexecution():
    """核心幂等测试：同一 PendingAction resolve(approve) 两次。

    - execute_count 仍为 1（不重发）
    - 两次返回内容完全相同（返回台账缓存）
    """
    store = _make_store()
    cap = PgControlCapability(store)

    async def _run():
        pending = cap.freeze(_call())
        try:
            result1 = await cap.resolve(pending, "approve")
            result2 = await cap.resolve(pending, "approve")  # 幂等重入
            return result1, result2, cap.execute_count
        finally:
            await _cleanup_idem(store, pending.idem_key)
            await store.aclose()

    result1, result2, count = run(_run())
    assert result1.content == result2.content, "第二次应返回与第一次相同内容（缓存）"
    assert result2.ok
    assert count == 1, f"幂等重入不应再次执行，execute_count={count}"


# ---------------------------------------------------------------------------
# T4: PgControlCapability — reject 路径
# ---------------------------------------------------------------------------

def test_pg_control_reject_returns_rejected_result():
    """reject → 结果含 [rejected]，execute_count=0，台账无该行。"""
    store = _make_store()
    cap = PgControlCapability(store)
    ledger = PgIdempotencyLedger(store)

    async def _run():
        pending = cap.freeze(_call(name="close_barrier"))
        try:
            result = await cap.resolve(pending, "reject")
            stored = await ledger.get(pending.idem_key)
            return result, cap.execute_count, stored
        finally:
            # reject 不写台账，但防御性清理
            await _cleanup_idem(store, pending.idem_key)
            await store.aclose()

    result, count, stored = run(_run())
    assert result.ok
    assert "[rejected]" in result.content
    assert "not executed" in result.content
    assert count == 0
    assert stored is None, "reject 不写台账，get 应返回 None"


# ---------------------------------------------------------------------------
# T5: PgAuditLog — audit_boundary + read_audit 编解码保真
# ---------------------------------------------------------------------------

def test_audit_boundary_round_trip():
    """audit_boundary → read_audit → decode_boundary 还原等价 Boundary。"""
    store = _make_store()
    audit = PgAuditLog(store)
    thread_id = _unique_key("test_audit_thread")

    pending = PendingAction(
        tool_call_id="tc-audit-001",
        idem_key="idem-audit-001",
        frozen_action={"name": "open_gate", "arguments": {"gate_id": "G1"}},
        handle=None,
    )
    boundary = Boundary(
        status="awaiting_confirmation",
        turn_id="turn-audit-1",
        seq=1,
        pending_batch=[pending],
        budget_snapshot={"iters": 2, "tokens": 128, "grace_used": False},
    )

    async def _run():
        try:
            await audit.audit_boundary(thread_id, boundary)
            payloads = await audit.read_audit(thread_id)
            return payloads
        finally:
            await _cleanup_audit(store, thread_id)
            await store.aclose()

    payloads = run(_run())
    assert len(payloads) == 1

    recovered = decode_boundary(payloads[0])
    assert recovered.status == "awaiting_confirmation"
    assert recovered.turn_id == "turn-audit-1"
    assert recovered.seq == 1
    assert recovered.budget_snapshot == {"iters": 2, "tokens": 128, "grace_used": False}
    assert recovered.pending_batch is not None
    assert len(recovered.pending_batch) == 1
    assert recovered.pending_batch[0].idem_key == "idem-audit-001"
    assert recovered.pending_batch[0].frozen_action["name"] == "open_gate"


def test_audit_append_only_two_rows():
    """两次 audit_boundary → read_audit 返回两条（append-only，顺序一致）。"""
    store = _make_store()
    audit = PgAuditLog(store)
    thread_id = _unique_key("test_audit_two")

    b1 = Boundary(status="awaiting_confirmation", turn_id="t1", seq=1)
    b2 = Boundary(status="iteration", turn_id="t2", seq=2)

    async def _run():
        try:
            await audit.audit_boundary(thread_id, b1)
            await audit.audit_boundary(thread_id, b2)
            return await audit.read_audit(thread_id)
        finally:
            await _cleanup_audit(store, thread_id)
            await store.aclose()

    payloads = run(_run())
    assert len(payloads) == 2
    assert payloads[0]["status"] == "awaiting_confirmation"
    assert payloads[1]["status"] == "iteration"
    assert payloads[0]["seq"] == 1
    assert payloads[1]["seq"] == 2
