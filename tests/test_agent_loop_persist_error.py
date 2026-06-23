"""test_agent_loop_persist_error.py — H1: store 失败合约

store.* 调用失败时 run_loop 不抛原始异常,而是返回
LoopResult(status="failed", reason="persist_error")。

覆盖:
  P1. commit 失败 → failed/persist_error,不 raise
  P2. latest_boundary 失败(入口) → failed/persist_error,不 raise
  P3. resolve_pending 失败(恢复路径) → failed/persist_error,不 raise
  P4. 正常 InMemoryConversationStore → 现有行为不变(sanity)
  P5. 工具 handler 抛异常 → 不被吸收为 persist_error(走既有 failed/tool_failures 路径)
"""
from __future__ import annotations

import asyncio

import pytest

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.control import FakeControlCapability
from agent_loop.conversation import (
    Boundary,
    Conversation,
    ConversationStore,
    InMemoryConversationStore,
)
from agent_loop.llm import FakeModelCaller, ModelTurn
from agent_loop.loop import run_loop
from agent_loop.messages import Message, ToolCallReq
from agent_loop.stubs import echo_tool
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolResult


# ─── 辅助工厂 ────────────────────────────────────────────────────────────────

def _cfg(max_iter: int = 5, max_fail: int = 3, toolset=None) -> LoopConfig:
    return LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=toolset or ["echo"],
        budget=LoopBudget(max_iterations=max_iter, max_tool_failures=max_fail),
    )


def _seeded(tid: str = "t") -> Conversation:
    c = Conversation(thread_id=tid)
    c.append(Message(role="user", content="开始"))
    return c


def run(coro):
    return asyncio.run(coro)


# ─── 故障存储桩 ───────────────────────────────────────────────────────────────

class _CommitRaisingStore(InMemoryConversationStore):
    """commit 抛 ConnectionError,其余方法正常。"""

    async def commit(self, thread_id, new_messages, boundary):
        raise ConnectionError("redis unreachable")


class _LatestBoundaryRaisingStore(InMemoryConversationStore):
    """latest_boundary 抛异常,阻断入口。"""

    async def latest_boundary(self, thread_id):
        raise ConnectionError("pg unreachable")


class _ResolvePendingRaisingStore(InMemoryConversationStore):
    """resolve_pending 抛异常;其余方法正常。
    用于验证恢复路径(awaiting_confirmation)中 resolve_pending 失败场景。
    """

    async def resolve_pending(self, thread_id, resolved, boundary):
        raise ConnectionError("pg unreachable during resolve")


# ─── P1: commit 失败 ──────────────────────────────────────────────────────────

def test_commit_failure_returns_persist_error_not_raises():
    """store.commit 抛 ConnectionError → run_loop 返回 failed/persist_error,不传播异常。"""
    reg = LoopToolRegistry()
    reg.register(echo_tool())
    fake = FakeModelCaller([ModelTurn(content="完成", tool_calls=[])])
    conv = _seeded()
    cfg = _cfg()
    budget = BudgetTracker(cfg.budget)
    store = _CommitRaisingStore()

    # 不应 raise
    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "failed"
    assert res.reason == "persist_error"


def test_commit_failure_does_not_raise():
    """确认 run_loop 调用本身不抛出任何异常(显式捕获验证)。"""
    reg = LoopToolRegistry()
    reg.register(echo_tool())
    fake = FakeModelCaller([ModelTurn(content="完成", tool_calls=[])])
    conv = _seeded()
    cfg = _cfg()
    budget = BudgetTracker(cfg.budget)
    store = _CommitRaisingStore()

    try:
        run(run_loop(cfg, conv, reg, budget, fake, store=store))
    except Exception as exc:
        pytest.fail(f"run_loop 不应抛出异常,实际抛出:{exc!r}")


# ─── P2: latest_boundary(入口)失败 ──────────────────────────────────────────

def test_latest_boundary_failure_at_entry_returns_persist_error():
    """store.latest_boundary 在入口抛异常 → failed/persist_error,不 raise。"""
    reg = LoopToolRegistry()
    reg.register(echo_tool())
    fake = FakeModelCaller([ModelTurn(content="不应到达", tool_calls=[])])
    conv = _seeded("lb-err")
    cfg = _cfg()
    budget = BudgetTracker(cfg.budget)
    store = _LatestBoundaryRaisingStore()

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "failed"
    assert res.reason == "persist_error"


# ─── P3: resolve_pending 失败(恢复路径) ──────────────────────────────────────

def test_resolve_pending_failure_during_resume_returns_persist_error():
    """恢复路径(awaiting_confirmation → resolution)中 resolve_pending 抛异常 →
    failed/persist_error,不 raise。

    流程:
      Run1: 正常 store → device_ctrl → awaiting_confirmation 落库
      Run2: 换上 _ResolvePendingRaisingStore,传入 resolution → 触发 resolve_pending → 失败
    """
    # ── 控制工具定义 ──────────────────────────────────────────────────────────
    ctrl = LoopTool(
        name="ctrl", description="控制工具", is_control=True,
        parameters={}, handler=lambda a, c: ToolResult(ok=True, content="ok"),
    )
    reg = LoopToolRegistry()
    reg.register(ctrl)
    reg.register(echo_tool())

    cfg = LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=["ctrl", "echo"],
        budget=LoopBudget(max_iterations=10),
    )

    # ── Run1: 正常 store,驱动到 awaiting_confirmation ──────────────────────
    good_store = InMemoryConversationStore()
    # 服务端预先落库 user 消息
    run(good_store.commit(
        "rp", [Message(role="user", content="开始")],
        Boundary(status="user", turn_id="turn-0", seq=0,
                 pending_batch=None, budget_snapshot=None),
    ))
    conv1 = run(good_store.load("rp"))

    fake1 = FakeModelCaller([
        ModelTurn(content="", tool_calls=[
            ToolCallReq(id="ctl1", name="ctrl", arguments={"cmd": "open"})
        ]),
    ])
    control = FakeControlCapability()
    budget1 = BudgetTracker(cfg.budget)

    res1 = run(run_loop(cfg, conv1, reg, budget1, fake1,
                        store=good_store, control=control))
    assert res1.status == "awaiting_confirmation", f"Run1 应挂起,得到 {res1.status}"

    # ── Run2: 换上故障 store,传入 approve resolution ─────────────────────
    # 把 good_store 的已提交状态迁移到故障 store(复制内部 _threads dict)
    bad_store = _ResolvePendingRaisingStore()
    bad_store._threads = good_store._threads  # 共享已提交状态

    pending = res1.pending[0]
    resolution = {pending.tool_call_id: "approve"}

    conv2 = run(good_store.load("rp"))   # 仍从正常 store 重载会话
    budget2 = BudgetTracker(cfg.budget)
    fake2 = FakeModelCaller([ModelTurn(content="已执行", tool_calls=[])])

    res2 = run(run_loop(cfg, conv2, reg, budget2, fake2,
                        store=bad_store, control=control,
                        resolution=resolution))

    assert res2.status == "failed"
    assert res2.reason == "persist_error"


# ─── P4: 正常 store sanity — 现有行为不变 ────────────────────────────────────

def test_normal_store_happy_path_still_completes():
    """健康路径:InMemoryConversationStore 正常 → completed,行为与改动前完全一致。"""
    reg = LoopToolRegistry()
    reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[
            ToolCallReq(id="c1", name="echo", arguments={"text": "hi"})
        ]),
        ModelTurn(content="完成", tool_calls=[]),
    ])
    conv = _seeded("sanity")
    cfg = _cfg()
    budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "completed"
    assert res.final == "完成"
    # store 有两条边界:iteration + completed
    state = store._threads.get("sanity")
    assert state is not None
    assert len(state.boundaries) == 2
    assert state.boundaries[0].status == "iteration"
    assert state.boundaries[1].status == "completed"


# ─── P5: 工具 handler 异常 → 不被吸收为 persist_error ────────────────────────

def test_tool_handler_exception_not_swallowed_as_persist_error():
    """工具 handler 内部 raise → executor 捕获为 failed disposition → 走既有
    tool_failures 路径(failed/tool_failures),不被误判为 persist_error。"""

    async def boom_handler(args, ctx):
        raise RuntimeError("tool infra error")

    boom = LoopTool(
        name="boom", description="爆炸工具", is_control=False,
        parameters={"type": "object", "properties": {}},
        handler=boom_handler,
    )
    reg = LoopToolRegistry()
    reg.register(boom)

    # max_fail=1:一次 failed → 立即熔断
    cfg = LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=["boom"],
        budget=LoopBudget(max_iterations=10, max_tool_failures=1),
    )
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[
            ToolCallReq(id="b1", name="boom", arguments={})
        ]),
        ModelTurn(content="不应到达", tool_calls=[]),
    ])
    conv = _seeded("tool-exc")
    budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))

    # 工具异常走既有路径,不是 persist_error
    assert res.status == "failed"
    assert res.reason == "tool_failures"          # 不是 persist_error
    assert res.reason != "persist_error"
