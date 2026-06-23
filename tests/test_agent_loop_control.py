"""Task 4: FakeControlCapability — freeze / resolve / idempotency tests."""
from __future__ import annotations

import asyncio

import pytest

from agent_loop.messages import ToolCallReq
from agent_loop.control import FakeControlCapability
from agent_loop.pending import ControlFreezer


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _call(name: str = "open_gate", args: dict | None = None) -> ToolCallReq:
    return ToolCallReq(id="tc-001", name=name, arguments=args or {"gate_id": "G1"})


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# freeze
# ---------------------------------------------------------------------------

def test_freeze_returns_pending_with_nonempty_idem_key():
    cap = FakeControlCapability()
    pending = cap.freeze(_call())
    assert pending.idem_key, "idem_key 不应为空"
    assert pending.tool_call_id == "tc-001"
    assert pending.frozen_action["name"] == "open_gate"
    assert pending.frozen_action["arguments"] == {"gate_id": "G1"}


def test_freeze_twice_produces_different_idem_keys():
    """每次 freeze 都产生全新 idem_key(不复用),否则两个并发动作互相污染 ledger。"""
    cap = FakeControlCapability()
    call = _call()
    p1 = cap.freeze(call)
    p2 = cap.freeze(call)
    assert p1.idem_key != p2.idem_key


def test_freeze_copies_arguments_no_aliasing():
    """frozen_action 必须是 arguments 的副本:冻结后修改原始 call.arguments 不影响 frozen_action。"""
    cap = FakeControlCapability()
    original_args = {"gate_id": "G1"}
    call = ToolCallReq(id="tc-001", name="open_gate", arguments=original_args)
    pending = cap.freeze(call)

    # 修改原始字典
    original_args["gate_id"] = "MUTATED"

    assert pending.frozen_action["arguments"]["gate_id"] == "G1", (
        "冻结后的 arguments 不应随原始 dict 变化"
    )


# ---------------------------------------------------------------------------
# approve
# ---------------------------------------------------------------------------

def test_approve_returns_ok_result_with_executed_marker():
    cap = FakeControlCapability()
    pending = cap.freeze(_call())
    result = run(cap.resolve(pending, "approve"))
    assert result.ok
    assert "[executed]" in result.content
    assert "readback=ok" in result.content


def test_approve_increments_execute_count():
    cap = FakeControlCapability()
    pending = cap.freeze(_call())
    run(cap.resolve(pending, "approve"))
    assert cap.execute_count == 1


# ---------------------------------------------------------------------------
# idempotency — the critical test
# ---------------------------------------------------------------------------

def test_idempotency_second_approve_returns_cached_no_reexecution():
    """核心幂等测试:相同 PendingAction resolve 两次 → 结果相同,execute_count 仍为 1。

    模拟崩溃场景:execute 后 commit 前进程崩溃,resume 再次 resolve 同一 pending。
    后端 deviceCtrl 不应收到两次指令。
    """
    cap = FakeControlCapability()
    pending = cap.freeze(_call())

    result1 = run(cap.resolve(pending, "approve"))
    result2 = run(cap.resolve(pending, "approve"))  # 同一 pending,幂等重入

    # 内容完全相同(返回缓存)
    assert result1.content == result2.content, "第二次 resolve 应返回与第一次完全相同的内容"
    assert result2.ok

    # 关键断言:execute_count 仍为 1,没有重发
    assert cap.execute_count == 1, (
        f"幂等重入不应再次执行,但 execute_count={cap.execute_count}"
    )


# ---------------------------------------------------------------------------
# reject
# ---------------------------------------------------------------------------

def test_reject_returns_rejected_result():
    cap = FakeControlCapability()
    pending = cap.freeze(_call())
    result = run(cap.resolve(pending, "reject"))
    assert result.ok
    assert "[rejected]" in result.content
    assert "not executed" in result.content


def test_reject_does_not_increment_execute_count():
    cap = FakeControlCapability()
    pending = cap.freeze(_call())
    run(cap.resolve(pending, "reject"))
    assert cap.execute_count == 0


def test_reject_does_not_pollute_ledger():
    """reject 后 ledger 为空:后续若改 approve(实践中不会,但契约要保证)不会读到 reject 缓存。"""
    cap = FakeControlCapability()
    pending = cap.freeze(_call())
    run(cap.resolve(pending, "reject"))
    # ledger 应为空
    assert len(cap._ledger) == 0


# ---------------------------------------------------------------------------
# unknown decision (defensive)
# ---------------------------------------------------------------------------

def test_unknown_decision_returns_error():
    cap = FakeControlCapability()
    pending = cap.freeze(_call())
    result = run(cap.resolve(pending, "unknown"))  # type: ignore[arg-type]
    assert not result.ok
    assert result.error == "unknown decision"


# ---------------------------------------------------------------------------
# ControlFreezer 协议兼容性
# ---------------------------------------------------------------------------

def test_fake_satisfies_control_freezer_protocol():
    """FakeControlCapability 结构上满足 ControlFreezer 协议(有可调用的 freeze)。"""
    cap = FakeControlCapability()
    # ControlFreezer 是 Protocol;运行时检查 freeze 是否可调用即满足结构性要求
    assert callable(getattr(cap, "freeze", None)), (
        "FakeControlCapability 必须有 callable freeze 以满足 ControlFreezer 协议"
    )
    # 也可直接把 cap 当作 ControlFreezer 使用(鸭子类型)
    freezer: ControlFreezer = cap  # type: ignore[assignment]
    pending = freezer.freeze(_call())
    assert pending.idem_key
