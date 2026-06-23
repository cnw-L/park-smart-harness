"""Tests for RunControl interrupt / rollback semantics (Task 6).

中断 = 不 commit 当前在途迭代(事务回滚)。
"""
from __future__ import annotations

import asyncio

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.conversation import Boundary, Conversation, InMemoryConversationStore
from agent_loop.dispatch import ToolExecOutcome
from agent_loop.loop import run_loop
from agent_loop.llm import FakeModelCaller, ModelTurn
from agent_loop.messages import Message, ToolCallReq
from agent_loop.runcontrol import RunControl
from agent_loop.stubs import echo_tool
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolContext, ToolResult


# ─── 共用辅助 ────────────────────────────────────────────────────────────────

def _cfg(max_iter: int = 10) -> LoopConfig:
    return LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=["echo"],
        budget=LoopBudget(max_iterations=max_iter),
    )


def _seeded(tid: str = "t") -> Conversation:
    c = Conversation(thread_id=tid)
    c.append(Message(role="user", content="开始"))
    return c


def run(coro):
    return asyncio.run(coro)


# ─── 1. 首次迭代前预中断 → interrupted;store 无边界 ──────────────────────────

def test_pre_interrupted_returns_immediately_no_commit():
    """RunControl 在首次迭代前置位 → 立即返回 interrupted;store 没有任何边界(不曾 commit)。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([ModelTurn(content="不应到达", tool_calls=[])])
    conv = _seeded()
    cfg = _cfg(); budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    rc = RunControl()
    rc.request_interrupt()   # 提前中断

    res = run(run_loop(cfg, conv, reg, budget, fake,
                       store=store, run_control=rc))

    assert res.status == "interrupted"
    assert res.final == "(中断)"

    # 未曾 commit:无边界
    boundary = run(store.latest_boundary("t"))
    assert boundary is None


# ─── 2. 迭代中途中断:工具批次后、commit 前 → 回滚;store 不变 ────────────────

def test_interrupt_mid_iteration_rollback():
    """中断在工具批次执行中触发(executor 执行时调用 rc.request_interrupt()),
    loop 在 pre-commit 检查时发现 rc.interrupted,丢弃本轮 buffer,不 commit。

    方式:用包装 executor 在 execute() 里调用 rc.request_interrupt(),
    然后正常返回工具结果;loop 的 post-tool、pre-commit 中断检查捕获。

    预置状态:先正常跑完一轮(commit 一条 iteration 边界),再触发中断,
    断言 store.latest_boundary 仍指向第一轮边界(第二轮被回滚)。
    """
    reg = LoopToolRegistry(); reg.register(echo_tool())

    rc = RunControl()

    class InterruptingExecutor:
        """execute_one() 调用后立即请求中断;仍正常返回工具结果(模拟处理完成但连接即将断开)。"""
        def __init__(self, real_executor, rc: RunControl) -> None:
            self._real = real_executor
            self._rc = rc

        async def execute_one(self, call, registry, ctx):
            outcome = await self._real.execute_one(call, registry, ctx)
            self._rc.request_interrupt()   # 触发中断
            return outcome

        async def execute(self, calls, registry, ctx):
            outcomes = []
            for call in calls:
                outcomes.append(await self.execute_one(call, registry, ctx))
            return outcomes

    from agent_loop.dispatch import SequentialToolExecutor
    interrupting_exec = InterruptingExecutor(SequentialToolExecutor(), rc)

    # 两轮:第一轮普通 echo → commit;第二轮 echo(中断在 executor 里触发)→ 回滚
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "iter1"})]),
        ModelTurn(content="完成", tool_calls=[]),      # 第二轮如果到达则返回 final(不会到达)
    ])
    conv = _seeded()
    cfg = _cfg(); budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    # 第一轮:正常提交(使用正常 executor)
    from agent_loop.dispatch import SequentialToolExecutor
    fake1 = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "iter1"})]),
    ])
    conv1 = _seeded("t2")
    budget1 = BudgetTracker(cfg.budget)
    # 先让第一轮正常完成(一条 iteration 边界)— 但 FakeModelCaller 只有一条 turn,
    # 需要再加一条 final answer 让它 commit iteration 边界后完成
    # 实际上:工具后无 final,loop 继续;所以我们需要在工具批次后给 final answer
    # 为简化,用完整两轮 fake:
    fake_setup = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "iter1"})]),
        ModelTurn(content="中间完成", tool_calls=[]),
    ])
    res_setup = run(run_loop(cfg, conv1, reg, budget1, fake_setup,
                             store=store, executor=SequentialToolExecutor()))
    assert res_setup.status == "completed"
    # 此时 store 有 2 条边界 (iteration + completed)
    state_after_setup = store._threads.get("t2")
    assert state_after_setup is not None
    boundaries_before = len(state_after_setup.boundaries)
    last_boundary_before = run(store.latest_boundary("t2"))

    # 第二阶段:重新加载,用 InterruptingExecutor 运行,预期在工具批次后中断回滚
    conv2 = run(store.load("t2"))
    conv2.messages = [Message(role="user", content="开始")] + conv2.messages
    budget2 = BudgetTracker(cfg.budget)
    fake2 = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c2", name="echo", arguments={"text": "iter2"})]),
        ModelTurn(content="这轮不应提交", tool_calls=[]),
    ])
    # 重置 rc 为新的(第一阶段已完成无中断)
    rc2 = RunControl()
    interrupting_exec2 = InterruptingExecutor(SequentialToolExecutor(), rc2)  # type: ignore[arg-type]

    res2 = run(run_loop(cfg, conv2, reg, budget2, fake2,
                        store=store, executor=interrupting_exec2,
                        run_control=rc2))

    assert res2.status == "interrupted"

    # store.latest_boundary 仍指向第一阶段结束的边界(第二轮未 commit)
    latest = run(store.latest_boundary("t2"))
    assert latest is not None
    assert latest.seq == last_boundary_before.seq   # seq 未增加
    assert len(store._threads["t2"].boundaries) == boundaries_before

    # conv2.messages 已回滚(不含 iter2 的 assistant/tool 消息)
    assert not any(
        m.role == "tool" and m.content == "iter2"
        for m in conv2.messages
    )


# ─── 3. 迭代顶部中断:在 grace 检查之前 → interrupted;不耗 grace ──────────────

def test_interrupt_at_top_of_iteration_with_prior_boundary():
    """先正常跑一轮(iteration 边界),再在第二轮顶部中断。
    store 应仍指向第一轮边界;grace 未被消耗。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    store = InMemoryConversationStore()
    cfg = _cfg(max_iter=10)

    # 第一轮:正常工具 + final
    conv1 = _seeded("t3")
    budget1 = BudgetTracker(cfg.budget)
    fake1 = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="x1", name="echo", arguments={"text": "r1"})]),
        ModelTurn(content="第一轮完成", tool_calls=[]),
    ])
    run(run_loop(cfg, conv1, reg, budget1, fake1, store=store))
    b1 = run(store.latest_boundary("t3"))
    assert b1 is not None

    # 第二轮:预中断
    rc = RunControl()
    rc.request_interrupt()
    conv2 = run(store.load("t3"))
    conv2.messages = [Message(role="user", content="开始")] + conv2.messages
    budget2 = BudgetTracker(cfg.budget)
    fake2 = FakeModelCaller([ModelTurn(content="不应到达", tool_calls=[])])

    res2 = run(run_loop(cfg, conv2, reg, budget2, fake2,
                        store=store, run_control=rc))

    assert res2.status == "interrupted"

    # store 边界不变
    b2 = run(store.latest_boundary("t3"))
    assert b2 is not None
    assert b2.seq == b1.seq
