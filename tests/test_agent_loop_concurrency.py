"""Tests for I1: concurrent allow-tool execution via asyncio.gather (§四 并行).

并发保序:结果按原 tool_calls 顺序写入 conversation,与完成顺序无关。
控制不并发:ask(is_control) 工具走 freeze 串行路径,绝不进 gather。
"""
from __future__ import annotations

import asyncio
import pytest

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.control import FakeControlCapability
from agent_loop.conversation import Conversation, InMemoryConversationStore
from agent_loop.dispatch import ToolExecOutcome
from agent_loop.gate import DefaultGate
from agent_loop.loop import run_loop
from agent_loop.llm import FakeModelCaller, ModelTurn
from agent_loop.messages import Message, ToolCallReq
from agent_loop.stubs import echo_tool
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolContext, ToolResult
from agent_loop.verify import VerifyVerdict


# ─── 共用辅助 ────────────────────────────────────────────────────────────────

def _cfg(toolset: list[str], max_iter: int = 10, max_fail: int = 5) -> LoopConfig:
    return LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=toolset,
        budget=LoopBudget(max_iterations=max_iter, max_tool_failures=max_fail),
    )


def _seeded(tid: str = "t") -> Conversation:
    c = Conversation(thread_id=tid)
    c.append(Message(role="user", content="开始"))
    return c


def run(coro):
    return asyncio.run(coro)


# ─── I1-1. 并发证明:两个慢读工具同时运行(max_running==2) ──────────────────────

def test_concurrent_allow_tools_overlap():
    """同一轮内两个 allow 工具应并发执行(asyncio.gather);
    max_running 追踪峰值并发数 — 串行实现下为 1,并发实现下为 2。"""
    running = 0
    max_running = 0

    async def slow_handler(args: dict, ctx: ToolContext) -> ToolResult:
        nonlocal running, max_running
        running += 1
        max_running = max(max_running, running)
        await asyncio.sleep(0.05)   # 人为延迟,让两个调用时间窗口重叠
        running -= 1
        return ToolResult(ok=True, content=f"done:{args.get('id','?')}")

    tool_a = LoopTool(name="slow_a", description="慢工具A",
                      parameters={"type": "object", "properties": {"id": {"type": "string"}}},
                      handler=slow_handler)
    tool_b = LoopTool(name="slow_b", description="慢工具B",
                      parameters={"type": "object", "properties": {"id": {"type": "string"}}},
                      handler=slow_handler)

    reg = LoopToolRegistry()
    reg.register(tool_a)
    reg.register(tool_b)

    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[
            ToolCallReq(id="c1", name="slow_a", arguments={"id": "A"}),
            ToolCallReq(id="c2", name="slow_b", arguments={"id": "B"}),
        ]),
        ModelTurn(content="完成", tool_calls=[]),
    ])
    conv = _seeded("concurrent")
    cfg = _cfg(["slow_a", "slow_b"])
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, BudgetTracker(cfg.budget), fake, store=store))

    assert res.status == "completed"
    # 核心断言:两工具并发执行时峰值并发数为 2(串行为 1)
    assert max_running == 2, (
        f"max_running={max_running},期望 2——工具应并发执行而非串行"
    )


# ─── I1-2. 并发保序:完成顺序≠发出顺序时,结果仍按原 tool_calls 顺序排列 ──────

def test_concurrent_allow_order_preservation():
    """三个 allow 工具睡眠时间各异,最快的最先完成,但 conversation 中
    tool 结果必须按 [c1, c2, c3] 原顺序排列(保序,不按完成顺序)。"""
    async def make_handler(delay: float, label: str):
        async def h(args: dict, ctx: ToolContext) -> ToolResult:
            await asyncio.sleep(delay)
            return ToolResult(ok=True, content=label)
        return h

    # c1=慢(0.09s), c2=中(0.05s), c3=快(0.01s) → 完成顺序 c3 < c2 < c1
    async def h1(args, ctx): await asyncio.sleep(0.09); return ToolResult(ok=True, content="result-1")
    async def h2(args, ctx): await asyncio.sleep(0.05); return ToolResult(ok=True, content="result-2")
    async def h3(args, ctx): await asyncio.sleep(0.01); return ToolResult(ok=True, content="result-3")

    t1 = LoopTool(name="t1", description="", parameters={"type": "object", "properties": {}}, handler=h1)
    t2 = LoopTool(name="t2", description="", parameters={"type": "object", "properties": {}}, handler=h2)
    t3 = LoopTool(name="t3", description="", parameters={"type": "object", "properties": {}}, handler=h3)

    reg = LoopToolRegistry()
    for t in [t1, t2, t3]:
        reg.register(t)

    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[
            ToolCallReq(id="c1", name="t1", arguments={}),
            ToolCallReq(id="c2", name="t2", arguments={}),
            ToolCallReq(id="c3", name="t3", arguments={}),
        ]),
        ModelTurn(content="保序完成", tool_calls=[]),
    ])
    conv = _seeded("order")
    cfg = _cfg(["t1", "t2", "t3"])
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, BudgetTracker(cfg.budget), fake, store=store))

    assert res.status == "completed"
    # 提取 tool 结果消息,按在 conversation 中出现的顺序
    tool_msgs = [m for m in conv.messages if m.role == "tool"]
    assert len(tool_msgs) == 3
    # 核心断言:顺序必须是 c1, c2, c3(原发出顺序),而非 c3, c2, c1(完成顺序)
    assert [m.tool_call_id for m in tool_msgs] == ["c1", "c2", "c3"]
    assert [m.content for m in tool_msgs] == ["result-1", "result-2", "result-3"]


# ─── I1-3. 混合批次:allow + ask + deny 同一轮,各路由正确,顺序正确 ──────────

def test_mixed_batch_allow_ask_deny_order_and_routing():
    """同一轮:echo(allow) + ctrl(ask) + blocked_tool(deny).
    allow 被执行;ask → pending_confirmation 占位 + pending_batch;deny → [blocked];
    结果按原 tool_calls 顺序 [a1, k1, d1] 出现;control.execute_count==0。"""
    async def ctrl_handler(args, ctx):
        return ToolResult(ok=True, content="should-not-run")

    ctrl = LoopTool(name="ctrl", description="控制", is_control=True,
                    parameters={"type": "object", "properties": {}}, handler=ctrl_handler)
    blocked = LoopTool(name="blocked_tool", description="被拒", is_control=False,
                       parameters={"type": "object", "properties": {}},
                       handler=lambda a, c: None)

    reg = LoopToolRegistry()
    reg.register(echo_tool())
    reg.register(ctrl)
    reg.register(blocked)

    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[
            ToolCallReq(id="a1", name="echo", arguments={"text": "mix"}),
            ToolCallReq(id="k1", name="ctrl", arguments={"cmd": "open"}),
            ToolCallReq(id="d1", name="blocked_tool", arguments={}),
        ]),
    ])
    conv = _seeded("mixed-order")
    cfg = LoopConfig(model="m", max_tokens=100, temperature=0.0, role="main",
                     toolset=["echo", "ctrl", "blocked_tool"],
                     budget=LoopBudget(max_iterations=10))
    store = InMemoryConversationStore()
    control = FakeControlCapability()
    gate = DefaultGate(denied=lambda call, tool: tool.name == "blocked_tool")

    res = run(run_loop(cfg, conv, reg, BudgetTracker(cfg.budget), fake,
                       store=store, control=control, gate=gate))

    assert res.status == "awaiting_confirmation"
    assert res.pending is not None and len(res.pending) == 1  # 仅 ctrl 进 pending

    tool_msgs = [m for m in conv.messages if m.role == "tool"]
    assert len(tool_msgs) == 3

    # 顺序必须保持原发出顺序 [a1, k1, d1]
    assert [m.tool_call_id for m in tool_msgs] == ["a1", "k1", "d1"]

    # 各路由结果正确
    by_id = {m.tool_call_id: m for m in tool_msgs}
    assert "mix" in by_id["a1"].content          # allow 执行结果
    assert by_id["k1"].content == "[pending_confirmation]"   # ask 占位
    assert "[blocked]" in by_id["d1"].content    # deny 合成

    # control.freeze 被调用但 handler 未执行
    assert control.execute_count == 0


# ─── I1-4. 控制不并发:两个 ask 工具同一轮,均走 freeze 串行路径 ─────────────

def test_control_tools_never_concurrent():
    """两个 is_control 工具同一轮 → 均走 ask/freeze 串行路径,进入 pending_batch;
    loop 挂起 awaiting_confirmation;两者均非并发执行(pending_batch 长度=2)。"""
    async def ctrl_handler(args, ctx):
        return ToolResult(ok=True, content="ctrl")

    ctrl1 = LoopTool(name="ctrl1", description="控制1", is_control=True,
                     parameters={"type": "object", "properties": {}}, handler=ctrl_handler)
    ctrl2 = LoopTool(name="ctrl2", description="控制2", is_control=True,
                     parameters={"type": "object", "properties": {}}, handler=ctrl_handler)

    reg = LoopToolRegistry()
    reg.register(ctrl1)
    reg.register(ctrl2)

    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[
            ToolCallReq(id="k1", name="ctrl1", arguments={}),
            ToolCallReq(id="k2", name="ctrl2", arguments={}),
        ]),
    ])
    conv = _seeded("ctrl-serial")
    cfg = LoopConfig(model="m", max_tokens=100, temperature=0.0, role="main",
                     toolset=["ctrl1", "ctrl2"],
                     budget=LoopBudget(max_iterations=10))
    store = InMemoryConversationStore()
    control = FakeControlCapability()

    res = run(run_loop(cfg, conv, reg, BudgetTracker(cfg.budget), fake,
                       store=store, control=control))

    # 两个控制工具都冻结 → pending_batch 长度=2 → 挂起
    assert res.status == "awaiting_confirmation"
    assert res.pending is not None and len(res.pending) == 2

    # 无一被执行(均为冻结,非并发执行)
    assert control.execute_count == 0

    # 两个占位符都在 conversation 中
    placeholders = [m for m in conv.messages
                    if m.role == "tool" and m.content == "[pending_confirmation]"]
    assert len(placeholders) == 2
    placeholder_ids = {m.tool_call_id for m in placeholders}
    assert placeholder_ids == {"k1", "k2"}


# ─── I1-5. verify 在并发 allow 中仍生效:失败的一个标 is_error,另一个干净 ──────

def test_verify_still_works_on_concurrent_allows():
    """两个并发 allow 调用,自定义 Verifier 令其中一个失败;
    失败结果有 [verify-failed] 前缀且 is_error=True,另一个干净;顺序保持原发出顺序。"""
    async def h_ok(args, ctx): return ToolResult(ok=True, content="ok-result")
    async def h_fail(args, ctx): return ToolResult(ok=True, content="bad-result")

    tool_ok = LoopTool(name="tool_ok", description="", parameters={"type": "object", "properties": {}}, handler=h_ok)
    tool_fail = LoopTool(name="tool_fail", description="", parameters={"type": "object", "properties": {}}, handler=h_fail)

    reg = LoopToolRegistry()
    reg.register(tool_ok)
    reg.register(tool_fail)

    class PartialVerifier:
        """tool_fail 的结果 business_ok=False(带 note);tool_ok 通过。"""
        async def verify(self, call, tool, outcome, ctx) -> VerifyVerdict:
            if tool.name == "tool_fail":
                return VerifyVerdict(business_ok=False, note="校验不通过")
            return VerifyVerdict(business_ok=True)

    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[
            ToolCallReq(id="v1", name="tool_ok", arguments={}),
            ToolCallReq(id="v2", name="tool_fail", arguments={}),
        ]),
        ModelTurn(content="verify 完成", tool_calls=[]),
    ])
    conv = _seeded("verify-concurrent")
    cfg = _cfg(["tool_ok", "tool_fail"])
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, BudgetTracker(cfg.budget), fake,
                       store=store, verifier=PartialVerifier()))

    assert res.status == "completed"

    tool_msgs = [m for m in conv.messages if m.role == "tool"]
    assert len(tool_msgs) == 2

    # 保序:v1 在前,v2 在后
    assert tool_msgs[0].tool_call_id == "v1"
    assert tool_msgs[1].tool_call_id == "v2"

    # tool_ok:干净结果,无 is_error
    assert tool_msgs[0].content == "ok-result"
    assert not tool_msgs[0].is_error

    # tool_fail:verify-failed 前缀(含 note),is_error=True
    assert tool_msgs[1].is_error is True
    assert "[verify-failed]" in tool_msgs[1].content
    assert "校验不通过" in tool_msgs[1].content
    assert "bad-result" in tool_msgs[1].content
