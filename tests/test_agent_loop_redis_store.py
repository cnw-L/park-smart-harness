"""Tests for agent_loop.redis_store — RedisConversationStore (P2).

实时测试（live tests）：需要 Redis @ localhost:6379。
运行方式：AGENT_LOOP_LIVE_INFRA=1 python -m pytest tests/test_agent_loop_redis_store.py -v

离线测试（offline）：不跳过，验证构造与配置解析不需要真实连接。
"""
from __future__ import annotations

import asyncio
import json
import os
from uuid import uuid4

import pytest

from agent_loop.codec import decode_boundary, decode_message
from agent_loop.conversation import Boundary
from agent_loop.messages import Message, ToolCallReq
from agent_loop.pending import PendingAction
from agent_loop.redis_store import RedisConversationStore

# ---------------------------------------------------------------------------
# 实时测试门控：无 AGENT_LOOP_LIVE_INFRA=1 时全部跳过
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    os.getenv("AGENT_LOOP_LIVE_INFRA") != "1",
    reason="set AGENT_LOOP_LIVE_INFRA=1 for live redis @ 90",
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def run(coro):
    """同步运行协程（无 pytest-asyncio 依赖）。"""
    return asyncio.run(coro)


def _msg(role: str, content: str, **kwargs) -> Message:
    return Message(role=role, content=content, **kwargs)


def _boundary(status: str, turn_id: str, seq: int, **kwargs) -> Boundary:
    return Boundary(status=status, turn_id=turn_id, seq=seq, **kwargs)


def _unique_prefix() -> str:
    """每个测试用唯一前缀，避免 key 冲突，便于清理。"""
    return f"agentloop_test_{uuid4().hex}"


async def _cleanup(store: RedisConversationStore, thread_id: str) -> None:
    """删除测试产生的 key（不影响其他 thread）。"""
    client = store._get_client()
    mkey = store._messages_key(thread_id)
    bkey = store._boundaries_key(thread_id)
    await client.delete(mkey, bkey)


# ---------------------------------------------------------------------------
# T1: commit 两次 → load 返回全部消息，latest_boundary 是第二个
# ---------------------------------------------------------------------------

def test_commit_two_iterations_load_returns_all():
    prefix = _unique_prefix()
    store = RedisConversationStore(key_prefix=prefix)
    thread_id = "th1"

    iter1_msgs = [_msg("user", "hello"), _msg("assistant", "thinking")]
    b1 = _boundary("iteration", turn_id="t1", seq=1)

    iter2_msgs = [_msg("assistant", "done")]
    b2 = _boundary("completed", turn_id="t2", seq=2)

    async def _run():
        try:
            await store.commit(thread_id, iter1_msgs, b1)
            await store.commit(thread_id, iter2_msgs, b2)
            conv = await store.load(thread_id)
            latest = await store.latest_boundary(thread_id)
            return conv, latest
        finally:
            await _cleanup(store, thread_id)
            await store.aclose()

    conv, latest = run(_run())

    assert len(conv.messages) == 3
    assert conv.messages[0].content == "hello"
    assert conv.messages[1].content == "thinking"
    assert conv.messages[2].content == "done"

    assert latest is not None
    assert latest.seq == 2
    assert latest.turn_id == "t2"
    assert latest.status == "completed"


# ---------------------------------------------------------------------------
# T2: 空 thread → latest_boundary 返回 None
# ---------------------------------------------------------------------------

def test_latest_boundary_empty_thread_is_none():
    prefix = _unique_prefix()
    store = RedisConversationStore(key_prefix=prefix)
    thread_id = f"no-such-{uuid4().hex}"

    async def _run():
        try:
            return await store.latest_boundary(thread_id)
        finally:
            await store.aclose()

    result = run(_run())
    assert result is None


# ---------------------------------------------------------------------------
# T3: resolve_pending — 占位符替换 + 新边界
# ---------------------------------------------------------------------------

def test_resolve_pending_swaps_placeholder_and_records_boundary():
    prefix = _unique_prefix()
    store = RedisConversationStore(key_prefix=prefix)
    thread_id = "th-resolve"

    # 原始消息：assistant 发起工具调用 + tool 占位符（pending_confirmation）
    tool_call_id = "call-pending-001"
    placeholder = Message(
        role="tool",
        content="[pending_confirmation]",
        tool_call_id=tool_call_id,
        name="open_gate",
    )
    original_msgs = [
        _msg("user", "请开大门"),
        Message(
            role="assistant",
            content="",
            tool_calls=[ToolCallReq(id=tool_call_id, name="open_gate", arguments={"gate_id": "G01"})],
        ),
        placeholder,
    ]
    b_suspend = _boundary(
        "awaiting_confirmation",
        turn_id="t-suspend",
        seq=1,
        pending_batch=[
            PendingAction(
                tool_call_id=tool_call_id,
                idem_key="idem-001",
                frozen_action={"tool": "open_gate", "args": {"gate_id": "G01"}},
            )
        ],
    )

    # resolve 后替换为真实结果
    resolved_msg = Message(
        role="tool",
        content='{"status": "opened"}',
        tool_call_id=tool_call_id,
        name="open_gate",
    )
    b_resolved = _boundary("iteration", turn_id="t-resolved", seq=2)

    async def _run():
        try:
            await store.commit(thread_id, original_msgs, b_suspend)
            await store.resolve_pending(thread_id, {tool_call_id: resolved_msg}, b_resolved)
            conv = await store.load(thread_id)
            latest = await store.latest_boundary(thread_id)
            return conv, latest
        finally:
            await _cleanup(store, thread_id)
            await store.aclose()

    conv, latest = run(_run())

    # 消息数量不变（原地替换，非追加）
    assert len(conv.messages) == 3

    # 占位符已被替换
    tool_results = [m for m in conv.messages if m.role == "tool"]
    assert len(tool_results) == 1
    assert tool_results[0].content == '{"status": "opened"}'
    assert tool_results[0].tool_call_id == tool_call_id

    # 新边界已记录
    assert latest is not None
    assert latest.seq == 2
    assert latest.turn_id == "t-resolved"
    assert latest.status == "iteration"


# ---------------------------------------------------------------------------
# T4: TTL — 挂起时 EXPIRE，恢复后 PERSIST
# ---------------------------------------------------------------------------

def test_ttl_set_on_suspend_removed_on_normal_commit():
    prefix = _unique_prefix()
    store = RedisConversationStore(key_prefix=prefix, ttl_minutes=5)
    thread_id = "th-ttl"

    msgs = [_msg("user", "请确认")]
    b_suspend = _boundary("awaiting_confirmation", turn_id="ts", seq=1)
    b_resume = _boundary("iteration", turn_id="tr", seq=2)

    async def _run():
        client = store._get_client()
        mkey = store._messages_key(thread_id)
        bkey = store._boundaries_key(thread_id)
        try:
            # 提交挂起边界 → 应设置 TTL
            await store.commit(thread_id, msgs, b_suspend)
            ttl_m = await client.ttl(mkey)
            ttl_b = await client.ttl(bkey)

            # 提交正常边界 → TTL 应被移除（PERSIST）
            await store.commit(thread_id, [_msg("assistant", "好的，已执行")], b_resume)
            ttl_m_after = await client.ttl(mkey)
            ttl_b_after = await client.ttl(bkey)

            return ttl_m, ttl_b, ttl_m_after, ttl_b_after
        finally:
            await _cleanup(store, thread_id)
            await store.aclose()

    ttl_m, ttl_b, ttl_m_after, ttl_b_after = run(_run())

    # 挂起时 TTL > 0
    assert ttl_m > 0, f"messages key TTL should be > 0 after suspend, got {ttl_m}"
    assert ttl_b > 0, f"boundaries key TTL should be > 0 after suspend, got {ttl_b}"

    # 恢复后 TTL = -1（无 TTL，PERSIST 成功）
    assert ttl_m_after == -1, f"messages key TTL should be -1 after normal commit, got {ttl_m_after}"
    assert ttl_b_after == -1, f"boundaries key TTL should be -1 after normal commit, got {ttl_b_after}"


# ---------------------------------------------------------------------------
# T6: refresh_on_read — 挂起态 load 刷新 TTL（默认行为,防确认期间过期）
# ---------------------------------------------------------------------------

def test_load_refreshes_ttl_when_suspended():
    prefix = _unique_prefix()
    store = RedisConversationStore(key_prefix=prefix, ttl_minutes=5, refresh_on_read=True)
    thread_id = "th-refresh"

    async def _run():
        client = store._get_client()
        mkey = store._messages_key(thread_id)
        try:
            await store.commit(thread_id, [_msg("user", "请确认")],
                               _boundary("awaiting_confirmation", turn_id="ts", seq=1))
            await client.expire(mkey, 100)        # 人为压低,模拟挂起期间时间流逝
            ttl_low = await client.ttl(mkey)
            await store.load(thread_id)            # refresh_on_read → 应重置回 ~300
            ttl_after = await client.ttl(mkey)
            return ttl_low, ttl_after
        finally:
            await _cleanup(store, thread_id)
            await store.aclose()

    ttl_low, ttl_after = run(_run())
    assert ttl_low <= 100
    assert ttl_after > 250, f"load 应把挂起态 TTL 刷新回 ~300,得 {ttl_after}"


# ---------------------------------------------------------------------------
# T5: 完整序列化保真 — 带 tool_calls 的 Message + 带 pending_batch 的 Boundary
# ---------------------------------------------------------------------------

def test_round_trip_fidelity_with_tool_calls_and_pending_batch():
    prefix = _unique_prefix()
    store = RedisConversationStore(key_prefix=prefix)
    thread_id = "th-roundtrip"

    tool_call_id = "call-rt-001"
    msg_assistant = Message(
        role="assistant",
        content="",
        reasoning="先查状态",
        tool_calls=[
            ToolCallReq(id=tool_call_id, name="get_gate_status", arguments={"gate_id": "G01", "verbose": True})
        ],
    )
    msg_tool = Message(
        role="tool",
        content='{"status": "closed"}',
        tool_call_id=tool_call_id,
        name="get_gate_status",
    )

    p1 = PendingAction(
        tool_call_id=tool_call_id,
        idem_key="idem-rt-001",
        frozen_action={"tool": "get_gate_status", "args": {"gate_id": "G01"}},
        handle="ticket-rt-001",
    )
    b = Boundary(
        status="awaiting_confirmation",
        turn_id="turn-rt",
        seq=1,
        pending_batch=[p1],
        budget_snapshot={"iters": 3, "tokens": 256, "grace_used": False},
    )

    async def _run():
        try:
            await store.commit(thread_id, [msg_assistant, msg_tool], b)
            conv = await store.load(thread_id)
            latest = await store.latest_boundary(thread_id)
            return conv, latest
        finally:
            await _cleanup(store, thread_id)
            await store.aclose()

    conv, latest = run(_run())

    # Message with tool_calls 保真
    assert len(conv.messages) == 2
    recovered_asst = conv.messages[0]
    assert recovered_asst.role == "assistant"
    assert recovered_asst.reasoning == "先查状态"
    assert len(recovered_asst.tool_calls) == 1
    assert recovered_asst.tool_calls[0].id == tool_call_id
    assert recovered_asst.tool_calls[0].arguments == {"gate_id": "G01", "verbose": True}

    recovered_tool = conv.messages[1]
    assert recovered_tool.tool_call_id == tool_call_id
    assert recovered_tool.name == "get_gate_status"

    # Boundary with pending_batch 保真
    assert latest is not None
    assert latest.status == "awaiting_confirmation"
    assert latest.turn_id == "turn-rt"
    assert latest.budget_snapshot == {"iters": 3, "tokens": 256, "grace_used": False}
    assert latest.pending_batch is not None
    assert len(latest.pending_batch) == 1
    assert latest.pending_batch[0].tool_call_id == tool_call_id
    assert latest.pending_batch[0].idem_key == "idem-rt-001"
    assert latest.pending_batch[0].handle == "ticket-rt-001"


# ---------------------------------------------------------------------------
# T7: load 从 Redis 消息日志派生 plan 投影（§1.3 Claude TodoWrite 式）
# ---------------------------------------------------------------------------

def test_redis_load_rebuilds_plan_from_messages():
    """commit 含 plan tool_call 的消息 → load 返回的 conv.plan.items 已重建。"""
    prefix = _unique_prefix()
    store = RedisConversationStore(key_prefix=prefix)
    thread_id = f"th-plan-{uuid4().hex[:8]}"

    plan_args = {
        "items": [
            {"id": "s1", "content": "查告警", "status": "done"},
            {"id": "s2", "content": "生成报告", "status": "doing",
             "spec": {"capability": "report", "zone": "B3"}},
        ]
    }
    msgs = [
        _msg("user", "帮我汇总告警"),
        Message(
            role="assistant",
            content="",
            tool_calls=[ToolCallReq(id="p1", name="plan", arguments=plan_args)],
        ),
        _msg("tool", "plan updated", tool_call_id="p1", name="plan"),
    ]
    b = _boundary("iteration", turn_id="t-plan", seq=1)

    async def _run():
        try:
            await store.commit(thread_id, msgs, b)
            conv = await store.load(thread_id)
            return conv
        finally:
            await _cleanup(store, thread_id)
            await store.aclose()

    conv = run(_run())

    # plan 投影已由 derive_plan 重建
    assert len(conv.plan.items) == 2
    assert conv.plan.items[0].id == "s1"
    assert conv.plan.items[0].status == "done"
    assert conv.plan.items[1].id == "s2"
    assert conv.plan.items[1].status == "doing"
    assert conv.plan.items[1].spec == {"capability": "report", "zone": "B3"}


# ---------------------------------------------------------------------------
# 离线测试（不需要 Redis，不受 pytestmark skipif 控制）
# ---------------------------------------------------------------------------

# 注:离线构造/配置解析测试移到 test_agent_loop_redis_store_offline.py
# (本文件 module 级 pytestmark 会跳过离线,故不能在此放离线测试)。
