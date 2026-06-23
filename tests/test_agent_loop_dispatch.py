"""Tests for ToolExecOutcome disposition + SequentialToolExecutor (S2 — gate seam).

S2 设计不变量:
  - 普通工具  → disposition=="executed", message 有内容, pending is None
  - 普通工具业务失败 (ok=False) → disposition=="executed"(NOT "failed"),ok False
  - 普通工具 handler 抛异常  → disposition=="failed", ok False, message 含 [error]
  - is_control 工具到达执行器 → disposition=="failed"(类型安全后盾),handler 从未被调用
    (S2 起控制工具应由 gate ask 路径在 loop 层处理;executor 是最后一道防线)
"""
from __future__ import annotations
import asyncio
import pytest
from agent_loop.dispatch import SequentialToolExecutor, ToolExecOutcome
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolContext, ToolResult, OutputBudget
from agent_loop.messages import Message, ToolCallReq
from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget


# ─── 共用辅助 ────────────────────────────────────────────────────────────────

def _ctx() -> ToolContext:
    budget = BudgetTracker(LoopBudget(max_iterations=10))
    return ToolContext(budget=budget, depth=0)


def _reg(*tools: LoopTool) -> LoopToolRegistry:
    reg = LoopToolRegistry()
    for t in tools:
        reg.register(t)
    return reg


def _call(name: str, args: dict | None = None, cid: str = "c1") -> ToolCallReq:
    return ToolCallReq(id=cid, name=name, arguments=args or {})


# ─── 普通工具:executed ────────────────────────────────────────────────────────

def test_normal_tool_disposition_executed():
    """普通工具正常返回 → disposition="executed", pending=None, message 含结果。"""
    async def handler(args, ctx):
        return ToolResult(ok=True, content="pong")

    tool = LoopTool(name="ping", description="", parameters={}, handler=handler)
    reg = _reg(tool)
    executor = SequentialToolExecutor()
    outcomes = asyncio.run(executor.execute([_call("ping")], reg, _ctx()))

    assert len(outcomes) == 1
    o = outcomes[0]
    assert o.disposition == "executed"
    assert o.ok is True
    assert o.message is not None
    assert "pong" in o.message.content
    assert o.pending is None


# ─── execute_one:普通工具直接调用 ────────────────────────────────────────────

def test_execute_one_normal_tool():
    """execute_one 直接调用普通工具 → executed。"""
    async def handler(args, ctx):
        return ToolResult(ok=True, content="direct")

    tool = LoopTool(name="direct", description="", parameters={}, handler=handler)
    reg = _reg(tool)
    executor = SequentialToolExecutor()
    outcome = asyncio.run(executor.execute_one(_call("direct"), reg, _ctx()))

    assert outcome.disposition == "executed"
    assert outcome.ok is True
    assert outcome.message is not None
    assert "direct" in outcome.message.content


# ─── 普通工具业务失败:仍是 executed(非 failed) ───────────────────────────────

def test_business_error_is_executed_not_failed():
    """handler 返回 ok=False(领域错误) → disposition="executed",ok=False,不是 "failed"。
    区分:executed+ok=False = 业务"否";failed = 基础设施/异常。"""
    async def handler(args, ctx):
        return ToolResult(ok=False, content="", error="record not found")

    tool = LoopTool(name="lookup", description="", parameters={}, handler=handler)
    reg = _reg(tool)
    executor = SequentialToolExecutor()
    outcomes = asyncio.run(executor.execute([_call("lookup")], reg, _ctx()))

    o = outcomes[0]
    assert o.disposition == "executed"   # 关键:不是 "failed"
    assert o.ok is False
    assert o.message is not None
    assert "[error]" in o.message.content
    assert o.pending is None


# ─── 普通工具 handler 抛异常:failed ─────────────────────────────────────────

def test_handler_exception_is_failed():
    """handler 抛异常 → disposition="failed",ok=False,message 含 [error]。"""
    async def handler(args, ctx):
        raise RuntimeError("boom from infra")

    tool = LoopTool(name="boomer", description="", parameters={}, handler=handler)
    reg = _reg(tool)
    executor = SequentialToolExecutor()
    outcomes = asyncio.run(executor.execute([_call("boomer")], reg, _ctx()))

    o = outcomes[0]
    assert o.disposition == "failed"
    assert o.ok is False
    assert o.message is not None
    assert "[error]" in o.message.content
    assert "boom from infra" in o.message.content
    assert o.pending is None


# ─── 控制工具到达 executor:类型安全后盾 → failed ──────────────────────────────

def test_control_tool_reaching_executor_is_failed_backstop():
    """S2 类型安全后盾(§六补 invariant):
    is_control=True 的工具不应到达执行器;gate ask 路径应在 loop 层处理。
    若仍到达:disposition="failed",handler 从未被调用,message 含错误描述。"""
    handler_called = False

    async def handler(args, ctx):
        nonlocal handler_called
        handler_called = True
        return ToolResult(ok=True, content="should not reach here")

    tool = LoopTool(
        name="open_gate",
        description="控制工具:开闸",
        parameters={},
        handler=handler,
        is_control=True,
    )
    reg = _reg(tool)
    executor = SequentialToolExecutor()
    # S2: execute_one 直接测试后盾(无需 freezer 参数)
    outcome = asyncio.run(executor.execute_one(_call("open_gate", cid="tc-99"), reg, _ctx()))

    assert outcome.disposition == "failed"
    assert outcome.ok is False
    assert outcome.message is not None
    assert "控制工具" in outcome.message.content or "error" in outcome.message.content.lower()
    assert outcome.pending is None

    # 核心断言:handler 从未被调用
    assert handler_called is False, "控制工具的 handler 不得被执行器内联调用!"


# ─── execute_one:控制工具后盾也适用 ─────────────────────────────────────────

def test_execute_one_control_tool_backstop():
    """execute_one 也执行类型安全后盾:控制工具 → failed,handler 不调用。"""
    handler_called = False

    async def handler(args, ctx):
        nonlocal handler_called
        handler_called = True
        return ToolResult(ok=True, content="nope")

    tool = LoopTool(name="ctrl", description="", parameters={}, handler=handler, is_control=True)
    reg = _reg(tool)
    executor = SequentialToolExecutor()
    outcome = asyncio.run(executor.execute_one(_call("ctrl"), reg, _ctx()))

    assert outcome.disposition == "failed"
    assert handler_called is False


# ─── output_budget 截断:仍走 executed 路径 ───────────────────────────────────

def test_output_budget_truncation_on_executed_tool():
    """output_budget 截断对 executed 普通工具仍生效,disposition 不受影响。"""
    async def handler(args, ctx):
        return ToolResult(ok=True, content="A" * 200)

    tool = LoopTool(
        name="big_read",
        description="",
        parameters={},
        handler=handler,
        output_budget=OutputBudget(max_chars=10),
    )
    reg = _reg(tool)
    executor = SequentialToolExecutor()
    outcomes = asyncio.run(executor.execute([_call("big_read")], reg, _ctx()))

    o = outcomes[0]
    assert o.disposition == "executed"
    assert o.ok is True
    # 截断后内容长度 = max_chars + 1(省略号 "…" 是单字符)
    assert len(o.message.content) == 11
    assert o.message.content.endswith("…")


# ─── 多工具:普通 + 普通(控制工具不再进 execute,而是通过 gate 路由) ───────────

def test_mixed_normal_calls_execute_in_order():
    """两条普通 tool call 串行执行,顺序保持。"""
    results = []

    async def h1(args, ctx):
        results.append("first")
        return ToolResult(ok=True, content="first_result")

    async def h2(args, ctx):
        results.append("second")
        return ToolResult(ok=True, content="second_result")

    t1 = LoopTool(name="t1", description="", parameters={}, handler=h1)
    t2 = LoopTool(name="t2", description="", parameters={}, handler=h2)

    reg = _reg(t1, t2)
    executor = SequentialToolExecutor()

    calls = [_call("t1", cid="c1"), _call("t2", cid="c2")]
    outcomes = asyncio.run(executor.execute(calls, reg, _ctx()))

    assert len(outcomes) == 2
    assert outcomes[0].disposition == "executed"
    assert outcomes[1].disposition == "executed"
    assert results == ["first", "second"]
