"""Tests for the verify seam (Task S3): business_ok / is_error 回灌.

设计不变量(§二、§五补):
  - verify 在结果边界运行,仅对 allow-executed 结果执行;
  - business_ok=False → loop 把该 tool 结果标 is_error=True 并前缀 [verify-failed];
  - verify 失败 ≠ 基础设施失败,不计入 failures(循环照常继续/完成);
  - NullVerifier: business_ok = outcome.ok,是透明默认值。
"""
from __future__ import annotations

import asyncio
import pytest

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.conversation import Conversation, InMemoryConversationStore
from agent_loop.dispatch import ToolExecOutcome
from agent_loop.loop import run_loop
from agent_loop.llm import FakeModelCaller, ModelTurn
from agent_loop.messages import Message, ToolCallReq
from agent_loop.stubs import echo_tool
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolContext, ToolResult
from agent_loop.verify import NullVerifier, VerifyVerdict, Verifier


# ─── 共用辅助 ────────────────────────────────────────────────────────────────

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


def _budget(cfg: LoopConfig) -> BudgetTracker:
    return BudgetTracker(cfg.budget)


# ─── 1. NullVerifier:business_ok 镜像 outcome.ok ──────────────────────────────

def test_null_verifier_ok_result_business_ok_true():
    """NullVerifier 对 ok=True 的 executed outcome 返回 business_ok=True。"""
    async def h(args, ctx):
        return ToolResult(ok=True, content="all good")

    tool = LoopTool(name="t", description="", parameters={}, handler=h)
    ctx = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=10)), depth=0)
    call = ToolCallReq(id="c1", name="t", arguments={})

    # 手工构造一个 executed outcome
    from agent_loop.dispatch import SequentialToolExecutor
    reg = LoopToolRegistry(); reg.register(tool)
    outcome = run(SequentialToolExecutor().execute_one(call, reg, ctx))

    verifier = NullVerifier()
    verdict = run(verifier.verify(call, tool, outcome, ctx))

    assert isinstance(verdict, VerifyVerdict)
    assert verdict.business_ok is True


def test_null_verifier_business_fail_outcome_business_ok_false():
    """NullVerifier 对 ok=False 的 executed outcome 返回 business_ok=False。"""
    async def h(args, ctx):
        return ToolResult(ok=False, content="", error="not found")

    tool = LoopTool(name="t", description="", parameters={}, handler=h)
    ctx = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=10)), depth=0)
    call = ToolCallReq(id="c1", name="t", arguments={})

    from agent_loop.dispatch import SequentialToolExecutor
    reg = LoopToolRegistry(); reg.register(tool)
    outcome = run(SequentialToolExecutor().execute_one(call, reg, ctx))

    verifier = NullVerifier()
    verdict = run(verifier.verify(call, tool, outcome, ctx))

    assert verdict.business_ok is False


# ─── 2. 自定义 Verifier:business_ok=False → is_error 回灌 ───────────────────

class _AlwaysFailVerifier:
    """对指定工具名始终返回 business_ok=False,带可选 note。"""
    def __init__(self, target_name: str, note: str = ""):
        self._target = target_name
        self._note = note

    async def verify(self, call: ToolCallReq, tool: LoopTool,
                     outcome: ToolExecOutcome, ctx: ToolContext) -> VerifyVerdict:
        if call.name == self._target:
            return VerifyVerdict(business_ok=False, note=self._note)
        return VerifyVerdict(business_ok=True)


def test_verify_fail_marks_tool_message_is_error():
    """自定义 Verifier 返回 business_ok=False → loop 把 tool 结果 is_error 置 True。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "hi"})]),
        ModelTurn(content="完成", tool_calls=[]),
    ])
    conv = _seeded("v-fail")
    cfg = _cfg(); budget = _budget(cfg)
    store = InMemoryConversationStore()
    verifier = _AlwaysFailVerifier("echo")

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store, verifier=verifier))

    # 循环仍正常完成(verify 失败不是基础设施失败)
    assert res.status == "completed"

    # 会话中 echo 的 tool 消息 is_error=True
    tool_msgs = [m for m in conv.messages if m.role == "tool" and m.tool_call_id == "c1"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0].is_error is True


def test_verify_fail_prepends_verify_failed_in_content():
    """verify 失败 → tool 消息 content 含 [verify-failed]。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "hello"})]),
        ModelTurn(content="ok", tool_calls=[]),
    ])
    conv = _seeded("v-prefix")
    cfg = _cfg(); budget = _budget(cfg)
    store = InMemoryConversationStore()
    verifier = _AlwaysFailVerifier("echo")

    run(run_loop(cfg, conv, reg, budget, fake, store=store, verifier=verifier))

    tool_msg = next(m for m in conv.messages if m.role == "tool" and m.tool_call_id == "c1")
    assert "[verify-failed]" in tool_msg.content


def test_verify_fail_with_note_appears_in_content():
    """Verifier 带 note → note 出现在标记后的 content 中。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "x"})]),
        ModelTurn(content="done", tool_calls=[]),
    ])
    conv = _seeded("v-note")
    cfg = _cfg(); budget = _budget(cfg)
    store = InMemoryConversationStore()
    verifier = _AlwaysFailVerifier("echo", note="校验回读不一致")

    run(run_loop(cfg, conv, reg, budget, fake, store=store, verifier=verifier))

    tool_msg = next(m for m in conv.messages if m.role == "tool" and m.tool_call_id == "c1")
    assert "校验回读不一致" in tool_msg.content
    assert " | " in tool_msg.content   # 有 note → 用 ' | ' 分隔


def test_verify_fail_empty_note_no_dangling_separator():
    """note 为空 → content 直接 [verify-failed] <原文>,无悬空的 ' | ' 分隔符。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "hello"})]),
        ModelTurn(content="ok", tool_calls=[]),
    ])
    conv = _seeded("v-empty-note")
    cfg = _cfg(); budget = _budget(cfg)
    store = InMemoryConversationStore()
    verifier = _AlwaysFailVerifier("echo")   # note 默认空

    run(run_loop(cfg, conv, reg, budget, fake, store=store, verifier=verifier))

    tool_msg = next(m for m in conv.messages if m.role == "tool" and m.tool_call_id == "c1")
    assert tool_msg.content == "[verify-failed] hello"
    assert " | " not in tool_msg.content


def test_verify_fail_does_not_count_as_infra_failure():
    """verify 失败 NOT 计入 failures → 即使 max_fail=1 也不触发熔断;循环正常完成。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "a"})]),
        ModelTurn(content="收尾", tool_calls=[]),
    ])
    conv = _seeded("v-nofail")
    # max_fail=1:若 verify 失败被计为基础设施失败,循环应在第一轮后熔断
    cfg = _cfg(max_fail=1); budget = _budget(cfg)
    store = InMemoryConversationStore()
    verifier = _AlwaysFailVerifier("echo")

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store, verifier=verifier))

    # 不应熔断,应完成
    assert res.status == "completed"
    assert res.final == "收尾"


def test_verify_fail_message_visible_in_conversation():
    """verify-failed 的 tool 消息在 conversation.messages 中可见(模型下轮能看到)。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "check"})]),
        ModelTurn(content="完毕", tool_calls=[]),
    ])
    conv = _seeded("v-visible")
    cfg = _cfg(); budget = _budget(cfg)
    store = InMemoryConversationStore()
    verifier = _AlwaysFailVerifier("echo")

    run(run_loop(cfg, conv, reg, budget, fake, store=store, verifier=verifier))

    # conversation.messages 中存在 is_error=True 的 tool 消息
    error_tool_msgs = [m for m in conv.messages if m.role == "tool" and m.is_error]
    assert len(error_tool_msgs) >= 1


# ─── 3. 默认 NullVerifier(无传参):ok 结果 is_error=False,内容未前缀 ──────────

def test_default_null_verifier_ok_result_no_is_error():
    """不传 verifier 时用 NullVerifier 默认值:ok=True 的 tool 结果 is_error 保持 False。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "hi"})]),
        ModelTurn(content="完成", tool_calls=[]),
    ])
    conv = _seeded("null-ok")
    cfg = _cfg(); budget = _budget(cfg)
    store = InMemoryConversationStore()

    # 不传 verifier,使用默认 NullVerifier
    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "completed"
    tool_msgs = [m for m in conv.messages if m.role == "tool"]
    assert all(m.is_error is False for m in tool_msgs)
    assert all("[verify-failed]" not in m.content for m in tool_msgs)


def test_default_null_verifier_loop_completes_normally():
    """NullVerifier 是透明无副作用的:现有工具调用行为不变。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "world"})]),
        ModelTurn(content="透明完成", tool_calls=[]),
    ])
    conv = _seeded("null-transparent")
    cfg = _cfg(); budget = _budget(cfg)
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "completed"
    assert res.final == "透明完成"
    tool_msgs = [m for m in conv.messages if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert "world" in tool_msgs[0].content
    assert tool_msgs[0].is_error is False


# ─── 4. infra failed 不走 verify(disposition=="failed" 不触发验证器) ──────────

def test_infra_failed_does_not_invoke_verifier():
    """handler 抛异常 → disposition==failed → verify 不被调用;失败计入 failures。"""
    verify_called = False

    class _TrackVerifier:
        async def verify(self, call, tool, outcome, ctx) -> VerifyVerdict:
            nonlocal verify_called
            verify_called = True
            return VerifyVerdict(business_ok=True)

    async def boom(args, ctx):
        raise RuntimeError("infra boom")

    boom_tool = LoopTool(name="boom", description="", parameters={}, handler=boom)
    reg = LoopToolRegistry(); reg.register(boom_tool)
    # max_fail=1:一次 infra 失败就熔断
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="b1", name="boom", arguments={})]),
        ModelTurn(content="不应到达", tool_calls=[]),
    ])
    conv = _seeded("infra-fail")
    cfg = _cfg(toolset=["boom"], max_fail=1); budget = _budget(cfg)
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store,
                       verifier=_TrackVerifier()))

    # 基础设施失败触发熔断
    assert res.status == "failed"
    # verifier 未被调用(disposition==failed 不走 verify 路径)
    assert verify_called is False


# ── ControlVerifier:控制"已受理≠已生效"标 verify-failed(替 NullVerifier 桩)──────

def test_control_verifier_flags_accepted_but_not_effective():
    from agent_loop.verify import ControlVerifier
    from agent_loop.dispatch import ToolExecOutcome
    from agent_loop.messages import Message, ToolCallReq
    from agent_loop.tools import LoopTool

    def _oc(content):
        return ToolExecOutcome(disposition="executed", ok=True, pending=None,
            message=Message(role="tool", content=content, tool_call_id="c", name="execute_proposal"))
    v = ControlVerifier()
    call = ToolCallReq(id="c", name="execute_proposal", arguments={})
    ctl = LoopTool(name="execute_proposal", description="", parameters={}, handler=None, is_control=True)
    rd = LoopTool(name="record_query", description="", parameters={}, handler=None)

    bad = asyncio.run(v.verify(call, ctl, _oc("[executed] deviceCtrl readback=accepted=True effective=False"), None))
    assert bad.business_ok is False                                   # 已受理未生效 → verify-failed
    pend = asyncio.run(v.verify(call, ctl, _oc("[executed] deviceCtrl readback=accepted=True effective=pending(…)"), None))
    assert pend.business_ok is False                                  # 待生效也判 failed
    good = asyncio.run(v.verify(call, ctl, _oc("[executed] deviceCtrl readback=accepted=True effective=True"), None))
    assert good.business_ok is True                                   # 真生效 → 放行
    rdv = asyncio.run(v.verify(call, rd, _oc("工单 276 单"), None))
    assert rdv.business_ok is True                                    # 只读放行
