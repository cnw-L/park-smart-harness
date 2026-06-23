"""Tests for Boundary + atomic-commit ConversationStore (Task 1 — transactional store).

TDD: these tests are written BEFORE the implementation and must fail first, then pass.
"""
from __future__ import annotations

import asyncio
import pytest

from agent_loop.conversation import Boundary, InMemoryConversationStore
from agent_loop.messages import Message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _msg(role: str, content: str) -> Message:
    return Message(role=role, content=content)


def _boundary(status: str, turn_id: str, seq: int, **kwargs) -> Boundary:
    return Boundary(status=status, turn_id=turn_id, seq=seq, **kwargs)


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# latest_boundary on empty thread → None
# ---------------------------------------------------------------------------

def test_latest_boundary_empty_thread_is_none():
    store = InMemoryConversationStore()

    async def _run():
        return await store.latest_boundary("no-such-thread")

    result = run(_run())
    assert result is None


# ---------------------------------------------------------------------------
# commit two iterations → load returns all messages; latest_boundary is 2nd
# ---------------------------------------------------------------------------

def test_commit_two_iterations_load_returns_all():
    store = InMemoryConversationStore()

    iter1_msgs = [_msg("user", "hello"), _msg("assistant", "thinking")]
    b1 = _boundary("iteration", turn_id="t1", seq=1)

    iter2_msgs = [_msg("assistant", "done")]
    b2 = _boundary("completed", turn_id="t2", seq=2)

    async def _run():
        await store.commit("th1", iter1_msgs, b1)
        await store.commit("th1", iter2_msgs, b2)
        conv = await store.load("th1")
        latest = await store.latest_boundary("th1")
        return conv, latest

    conv, latest = run(_run())

    # All 3 messages in order
    assert len(conv.messages) == 3
    assert conv.messages[0].content == "hello"
    assert conv.messages[1].content == "thinking"
    assert conv.messages[2].content == "done"

    # latest boundary is the second one
    assert latest is not None
    assert latest.seq == 2
    assert latest.turn_id == "t2"
    assert latest.status == "completed"


# ---------------------------------------------------------------------------
# Torn tail: messages appended without boundary → load discards them
# ---------------------------------------------------------------------------

def test_torn_tail_discarded_on_load():
    store = InMemoryConversationStore()

    iter1_msgs = [_msg("user", "start"), _msg("assistant", "iter1-reply")]
    b1 = _boundary("iteration", turn_id="t1", seq=1)

    torn_msgs = [_msg("assistant", "torn-message-never-committed")]

    async def _run():
        # Commit iteration 1 properly
        await store.commit("th2", iter1_msgs, b1)
        # Simulate a torn write: messages written but boundary never committed
        store._append_uncommitted("th2", torn_msgs)
        # load must return only iteration-1 messages
        conv = await store.load("th2")
        latest = await store.latest_boundary("th2")
        return conv, latest

    conv, latest = run(_run())

    assert len(conv.messages) == 2
    assert conv.messages[0].content == "start"
    assert conv.messages[1].content == "iter1-reply"
    # No torn message visible
    assert all(m.content != "torn-message-never-committed" for m in conv.messages)

    # latest boundary still points to iteration 1
    assert latest is not None
    assert latest.seq == 1
    assert latest.turn_id == "t1"


# ---------------------------------------------------------------------------
# pending_batch and budget_snapshot round-trip through commit → load/latest_boundary
# ---------------------------------------------------------------------------

def test_boundary_pending_batch_and_budget_snapshot_roundtrip():
    store = InMemoryConversationStore()

    pending = [{"action": "turn_on", "device_id": "d-001"}]
    snapshot = {"iterations_remaining": 3, "tokens_used": 512}

    b = _boundary(
        "awaiting_confirmation",
        turn_id="t-confirm",
        seq=1,
        pending_batch=pending,
        budget_snapshot=snapshot,
    )
    msgs = [_msg("assistant", "请确认操作")]

    async def _run():
        await store.commit("th3", msgs, b)
        latest = await store.latest_boundary("th3")
        return latest

    latest = run(_run())

    assert latest is not None
    assert latest.status == "awaiting_confirmation"
    assert latest.pending_batch == pending
    assert latest.budget_snapshot == snapshot


# ---------------------------------------------------------------------------
# Boundary default fields
# ---------------------------------------------------------------------------

def test_boundary_defaults():
    b = Boundary(status="iteration", turn_id="t0", seq=0)
    assert b.pending_batch is None
    assert b.budget_snapshot is None


# ---------------------------------------------------------------------------
# plan is preserved across commits (default PlanState present)
# ---------------------------------------------------------------------------

def test_plan_preserved_after_commit():
    store = InMemoryConversationStore()

    msgs = [_msg("user", "plan test")]
    b = _boundary("iteration", turn_id="tp1", seq=1)

    async def _run():
        await store.commit("th4", msgs, b)
        conv = await store.load("th4")
        return conv

    conv = run(_run())
    # PlanState default is present (not None)
    assert conv.plan is not None
    assert conv.plan.items == []


# ---------------------------------------------------------------------------
# commit is idempotent w.r.t. multiple threads (isolation)
# ---------------------------------------------------------------------------

def test_multiple_threads_isolated():
    store = InMemoryConversationStore()

    msgs_a = [_msg("user", "thread-a")]
    msgs_b = [_msg("user", "thread-b")]
    b_a = _boundary("completed", turn_id="ta", seq=1)
    b_b = _boundary("completed", turn_id="tb", seq=1)

    async def _run():
        await store.commit("threadA", msgs_a, b_a)
        await store.commit("threadB", msgs_b, b_b)
        conv_a = await store.load("threadA")
        conv_b = await store.load("threadB")
        return conv_a, conv_b

    conv_a, conv_b = run(_run())

    assert len(conv_a.messages) == 1
    assert conv_a.messages[0].content == "thread-a"
    assert len(conv_b.messages) == 1
    assert conv_b.messages[0].content == "thread-b"
