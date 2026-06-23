"""Tests for suspend / resume semantics (Task 6).

控制工具 → 挂起(awaiting_confirmation)→ 恢复(approve/reject) → completed。
幂等重入:同一 idem_key 不重复执行。
预算跨恢复持久化。
"""
from __future__ import annotations

import asyncio

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.control import FakeControlCapability
from agent_loop.conversation import Conversation, InMemoryConversationStore
from agent_loop.loop import run_loop
from agent_loop.llm import FakeModelCaller, ModelTurn
from agent_loop.messages import Message, ToolCallReq
from agent_loop.stubs import echo_tool
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolResult


# ─── 共用辅助 ────────────────────────────────────────────────────────────────

def _cfg(max_iter: int = 10) -> LoopConfig:
    return LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=["ctrl", "echo"],
        budget=LoopBudget(max_iterations=max_iter),
    )


def _seeded(tid: str = "t") -> Conversation:
    c = Conversation(thread_id=tid)
    c.append(Message(role="user", content="请操作"))
    return c


def _ctrl_tool() -> LoopTool:
    """is_control=True 工具;executor 将冻结它而非内联执行。"""
    async def h(args, ctx):  # 这个 handler 不应被调用
        return ToolResult(ok=True, content="should-not-run")
    return LoopTool(
        name="ctrl", description="控制工具", is_control=True,
        parameters={"type": "object", "properties": {"cmd": {"type": "string"}}},
        handler=h,
    )


def run(coro):
    return asyncio.run(coro)


# ─── 1. 控制工具 → awaiting_confirmation;handler 从未执行 ────────────────────

def test_control_tool_suspends_with_placeholder():
    """首次 run:control tool → awaiting_confirmation;
    - store.latest_boundary.status == "awaiting_confirmation"
    - pending_batch 有 1 个 PendingAction
    - 已提交日志含 [pending_confirmation] 占位符
    - FakeControlCapability.execute_count == 0(handler 未执行)
    """
    reg = LoopToolRegistry(); reg.register(echo_tool()); reg.register(_ctrl_tool())
    ctrl_call = ToolCallReq(id="tc1", name="ctrl", arguments={"cmd": "open"})
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ctrl_call]),
        ModelTurn(content="操作完成", tool_calls=[]),
    ])
    conv = _seeded()
    cfg = _cfg()
    budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()
    control = FakeControlCapability()

    res = run(run_loop(cfg, conv, reg, budget, fake,
                       store=store, control=control))

    assert res.status == "awaiting_confirmation"
    assert res.pending is not None
    assert len(res.pending) == 1

    # 控制能力未执行
    assert control.execute_count == 0

    # store 边界正确
    boundary = run(store.latest_boundary("t"))
    assert boundary is not None
    assert boundary.status == "awaiting_confirmation"
    assert boundary.pending_batch is not None
    assert len(boundary.pending_batch) == 1
    assert boundary.pending_batch[0].tool_call_id == "tc1"

    # 已提交日志含占位符
    persisted = run(store.load("t"))
    tool_msgs = [m for m in persisted.messages if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0].content == "[pending_confirmation]"
    assert tool_msgs[0].tool_call_id == "tc1"


# ─── 2. approve 恢复 → 控制执行 → completed ──────────────────────────────────

def test_resume_with_approve_executes_and_completes():
    """恢复(approve):
    - control.execute_count == 1(真实执行)
    - 占位符替换为真实结果
    - 循环继续到 completed
    """
    reg = LoopToolRegistry(); reg.register(echo_tool()); reg.register(_ctrl_tool())
    ctrl_call = ToolCallReq(id="tc1", name="ctrl", arguments={"cmd": "open"})

    # 第一次 run:挂起
    store = InMemoryConversationStore()
    control = FakeControlCapability()
    fake1 = FakeModelCaller([ModelTurn(content="", tool_calls=[ctrl_call])])
    conv1 = _seeded()
    cfg = _cfg()
    budget1 = BudgetTracker(cfg.budget)

    res1 = run(run_loop(cfg, conv1, reg, budget1, fake1,
                        store=store, control=control))
    assert res1.status == "awaiting_confirmation"

    # 重新加载会话并恢复
    conv2 = run(store.load("t"))
    conv2.messages = [Message(role="user", content="请操作")] + conv2.messages
    budget2 = BudgetTracker(cfg.budget)
    fake2 = FakeModelCaller([ModelTurn(content="操作完成", tool_calls=[])])

    res2 = run(run_loop(cfg, conv2, reg, budget2, fake2,
                        store=store, control=control,
                        resolution={"tc1": "approve"}))

    assert res2.status == "completed"
    assert res2.final == "操作完成"

    # 控制工具恰好执行了一次
    assert control.execute_count == 1

    # 占位符已被替换(会话不含 [pending_confirmation])
    assert not any(
        m.role == "tool" and m.content == "[pending_confirmation]"
        for m in conv2.messages
    )
    # 有真实执行结果
    assert any(
        m.role == "tool" and "[executed]" in m.content
        for m in conv2.messages
    )


# ─── 3. reject 恢复 → 拒绝结果填槽 → completed;execute_count==0 ──────────────

def test_resume_with_reject_fills_slot_and_completes():
    """恢复(reject):
    - execute_count == 0(未执行)
    - 占位符替换为 [rejected] 消息
    - 循环继续到 completed
    """
    reg = LoopToolRegistry(); reg.register(echo_tool()); reg.register(_ctrl_tool())
    ctrl_call = ToolCallReq(id="tc2", name="ctrl", arguments={"cmd": "close"})

    store = InMemoryConversationStore()
    control = FakeControlCapability()
    fake1 = FakeModelCaller([ModelTurn(content="", tool_calls=[ctrl_call])])
    conv1 = _seeded("t2")
    cfg = _cfg()
    budget1 = BudgetTracker(cfg.budget)

    res1 = run(run_loop(cfg, conv1, reg, budget1, fake1,
                        store=store, control=control))
    assert res1.status == "awaiting_confirmation"

    conv2 = run(store.load("t2"))
    conv2.messages = [Message(role="user", content="请操作")] + conv2.messages
    budget2 = BudgetTracker(cfg.budget)
    fake2 = FakeModelCaller([ModelTurn(content="已拒绝完成", tool_calls=[])])

    res2 = run(run_loop(cfg, conv2, reg, budget2, fake2,
                        store=store, control=control,
                        resolution={"tc2": "reject"}))

    assert res2.status == "completed"
    assert control.execute_count == 0

    # 有 [rejected] 消息
    assert any(
        m.role == "tool" and "[rejected]" in m.content
        for m in conv2.messages
    )


# ─── 4. 幂等重入:同一 idem_key 不重复执行 ───────────────────────────────────

def test_idempotent_re_resume_no_double_execute():
    """对同一 awaiting_confirmation 边界 approve 两次:execute_count 仍为 1。

    模拟崩溃后重入:第二次 resolve 通过 FakeControlCapability 的 ledger 幂等保护
    不再递增 execute_count。
    """
    reg = LoopToolRegistry(); reg.register(echo_tool()); reg.register(_ctrl_tool())
    ctrl_call = ToolCallReq(id="tc3", name="ctrl", arguments={"cmd": "toggle"})

    # 首次 run → 挂起
    store = InMemoryConversationStore()
    control = FakeControlCapability()
    fake1 = FakeModelCaller([ModelTurn(content="", tool_calls=[ctrl_call])])
    conv1 = _seeded("t3")
    cfg = _cfg()
    budget1 = BudgetTracker(cfg.budget)

    res1 = run(run_loop(cfg, conv1, reg, budget1, fake1,
                        store=store, control=control))
    assert res1.status == "awaiting_confirmation"

    # 第一次恢复(approve)
    conv2 = run(store.load("t3"))
    conv2.messages = [Message(role="user", content="请操作")] + conv2.messages
    budget2 = BudgetTracker(cfg.budget)
    fake2 = FakeModelCaller([ModelTurn(content="完成", tool_calls=[])])
    run(run_loop(cfg, conv2, reg, budget2, fake2,
                 store=store, control=control, resolution={"tc3": "approve"}))
    assert control.execute_count == 1

    # 模拟崩溃:重新加载挂起状态(从 store 中取原始 awaiting 边界)
    # 直接对同一 pending action 再次调用 resolve(模拟第二次 approve)
    pending_batch = res1.pending
    assert pending_batch is not None
    assert len(pending_batch) == 1
    pending = pending_batch[0]

    result = run(control.resolve(pending, "approve"))
    # 幂等:ledger 命中,不重新执行
    assert control.execute_count == 1   # 仍为 1,不是 2
    assert result.ok


# ─── 5. 预算跨恢复持续:消耗计数不清零 ───────────────────────────────────────

def test_budget_rehydrated_on_resume():
    """挂起时 budget 快照写入边界;恢复时重水化——消耗量从中断点延续,不从 0 开始。

    验证方式:设定 max_iterations=2。
    - 首次 run:消耗 1 次(控制工具轮),suspend。budget 快照 {iters:1}。
    - 重水化后 _iters=1;max=2;下一轮 1 < 2 → 正常;consume → _iters=2;
      再下一轮 2 >= 2 → grace → budget_exhausted。
    - 若不重水化(从 0 开始):下一轮 0 < 2 → 正常;consume → _iters=1;
      再下一轮 1 < 2 → 正常;consume → _iters=2;再 2 >= 2 → grace — 多跑一轮。
    - budget2._iters 恰好 == 3(1 restore + 1 normal + 1 grace);
      若未重水化则 == 3 也一样 —— 改用 boundaries 数量区分:
        重水化: 1(resolve) + 1(normal) + 1(grace-completed) = 3 boundaries total (t4 线程)
        未重水化: 1(resolve) + 2(normal) + 1(grace-completed) = 4 boundaries total
    """
    reg = LoopToolRegistry(); reg.register(echo_tool()); reg.register(_ctrl_tool())
    ctrl_call = ToolCallReq(id="tc4", name="ctrl", arguments={"cmd": "x"})

    store = InMemoryConversationStore()
    control = FakeControlCapability()
    cfg = _cfg(max_iter=2)

    # 首次 run:消耗 1 次迭代(ctrl 工具挂起)
    fake1 = FakeModelCaller([ModelTurn(content="", tool_calls=[ctrl_call])])
    conv1 = _seeded("t4")
    budget1 = BudgetTracker(cfg.budget)
    run(run_loop(cfg, conv1, reg, budget1, fake1,
                 store=store, control=control))
    assert budget1._iters == 1   # 确认消耗了 1 次

    # 边界数恢复前 == 1(awaiting_confirmation 边界)
    state_before = store._threads.get("t4")
    assert state_before is not None and len(state_before.boundaries) == 1

    # 恢复:新建 budget2,restore 后从 _iters=1 出发
    conv2 = run(store.load("t4"))
    conv2.messages = [Message(role="user", content="请操作")] + conv2.messages
    budget2 = BudgetTracker(cfg.budget)
    # 足够多 echo 轮以触发耗尽
    looping = [
        ModelTurn(content="", tool_calls=[ToolCallReq(id=f"e{i}", name="echo", arguments={"text": str(i)})])
        for i in range(5)
    ] + [ModelTurn(content="grace收尾", tool_calls=[])]
    fake2 = FakeModelCaller(looping)

    res2 = run(run_loop(cfg, conv2, reg, budget2, fake2,
                        store=store, control=control, resolution={"tc4": "approve"}))

    assert res2.status == "budget_exhausted"

    # 重水化验证:_iters 恢复到 1,正常跑 1 次(→2),grace 轮(→3)共消耗 3 次
    assert budget2._iters == 3  # restore(1) + 1 normal + 1 grace = 3 total

    # 边界数:1(awaiting) + 1(resolve_pending/iteration) + 1(normal iteration) + 1(grace completed) = 4
    state_after = store._threads.get("t4")
    assert state_after is not None
    assert len(state_after.boundaries) == 4
