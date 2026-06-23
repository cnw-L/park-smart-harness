"""test_agent_loop_audited_store_live.py — 实时测试 AuditedConversationStore (A1).

需要真实 Redis@localhost:6379 + Postgres@localhost:5432/smart_park。
运行方式:
    AGENT_LOOP_LIVE_INFRA=1 python -m pytest tests/test_agent_loop_audited_store_live.py -v --timeout=60

清理:finally 块精确删除测试 thread 的 Redis keys + PG 审计行,不 flushdb / TRUNCATE。
"""
from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("AGENT_LOOP_LIVE_INFRA") != "1",
    reason="set AGENT_LOOP_LIVE_INFRA=1 for live redis+pg @ localhost",
)

from agent_loop.audited_store import AuditedConversationStore
from agent_loop.codec import decode_boundary
from agent_loop.conversation import Boundary
from agent_loop.messages import Message
from agent_loop.pg_store import PgAuditLog, PgStore
from agent_loop.redis_store import RedisConversationStore


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def run(coro):
    """同步运行协程(无 pytest-asyncio 依赖,与其他 live 测试风格一致)。"""
    return asyncio.run(coro)


def _unique_prefix() -> str:
    return f"audit_test_{uuid4().hex[:8]}"


def _b(seq: int, status: str = "iteration") -> Boundary:
    return Boundary(status=status, turn_id=f"turn-{seq}", seq=seq)


def _msg(content: str) -> Message:
    return Message(role="assistant", content=content)


async def _cleanup_redis(redis_store: RedisConversationStore, thread_id: str) -> None:
    """精确删除测试 thread 的 Redis 两个 key。"""
    try:
        client = redis_store._get_client()
        mkey = redis_store._messages_key(thread_id)
        bkey = redis_store._boundaries_key(thread_id)
        await client.delete(mkey, bkey)
    except Exception as exc:
        print(f"[A1-live] redis cleanup warning: {exc}")


async def _cleanup_pg(pg_store: PgStore, thread_id: str) -> None:
    """精确删除该 thread_id 的全部审计行。"""
    try:
        pool = await pg_store._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM agentloop_audit WHERE thread_id=$1",
                thread_id,
            )
    except Exception as exc:
        print(f"[A1-live] pg cleanup warning: {exc}")


# ---------------------------------------------------------------------------
# Test 1: commit → read_audit → decode_boundary round-trip
# ---------------------------------------------------------------------------

def test_live_commit_audit_roundtrip():
    """commit 一个 boundary → read_audit 返回 payload → decode_boundary 等于原值。"""
    prefix = _unique_prefix()
    thread_id = f"live_audit_{uuid4().hex}"

    pg_store = PgStore()
    audit = PgAuditLog(pg_store)
    redis_store = RedisConversationStore(key_prefix=prefix)
    store = AuditedConversationStore(redis_store, audit)

    b1 = _b(seq=1, status="iteration")

    async def _run():
        try:
            await store.commit(thread_id, [_msg("hello")], b1)

            rows = await audit.read_audit(thread_id)
            assert len(rows) == 1, f"期望 1 行审计记录,实际 {len(rows)}"

            decoded = decode_boundary(rows[0])
            assert decoded.seq == b1.seq
            assert decoded.status == b1.status
            assert decoded.turn_id == b1.turn_id
        finally:
            await _cleanup_redis(redis_store, thread_id)
            await _cleanup_pg(pg_store, thread_id)
            await store.aclose()
            await pg_store.aclose()

    run(_run())


# ---------------------------------------------------------------------------
# Test 2: 两次 commit → 两条审计行(append-only)
# ---------------------------------------------------------------------------

def test_live_two_commits_two_audit_rows():
    """两次 commit → agentloop_audit 有两行,且按序递增(append-only)。"""
    prefix = _unique_prefix()
    thread_id = f"live_audit_2_{uuid4().hex}"

    pg_store = PgStore()
    audit = PgAuditLog(pg_store)
    redis_store = RedisConversationStore(key_prefix=prefix)
    store = AuditedConversationStore(redis_store, audit)

    b1 = _b(seq=1, status="iteration")
    b2 = _b(seq=2, status="completed")

    async def _run():
        try:
            await store.commit(thread_id, [_msg("first")], b1)
            await store.commit(thread_id, [_msg("second")], b2)

            rows = await audit.read_audit(thread_id)
            assert len(rows) == 2, f"期望 2 行审计记录,实际 {len(rows)}"

            d1 = decode_boundary(rows[0])
            d2 = decode_boundary(rows[1])
            assert d1.seq == 1
            assert d2.seq == 2
            assert d2.status == "completed"
        finally:
            await _cleanup_redis(redis_store, thread_id)
            await _cleanup_pg(pg_store, thread_id)
            await store.aclose()
            await pg_store.aclose()

    run(_run())
