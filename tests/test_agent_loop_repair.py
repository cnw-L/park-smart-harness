"""Tests for Task S1: defensive repair seam (port Hermes) + unify interrupt on RunControl.

TDD: 先写测试(这些测试在实现前会失败)。
覆盖:
  - repair_messages: 孤立 tool 消息被丢弃
  - repair_messages: 与 assistant tool_call 配对的 tool 消息保留
  - repair_messages: 连续 user 消息合并(内容保留)
  - repair_messages: 合法的 assistant(tool_calls)+tool+user 序列不被修改
  - repair_messages: 空列表不崩溃,返回 0
  - repair_messages: 修复后消息序列 role 顺序合法
  - loop 集成:带孤立 tool 消息的会话进入循环后孤立消息被清理
  - budget 清理:BudgetTracker 不再有 interrupted/request_interrupt
"""
from __future__ import annotations

import asyncio

from agent_loop.messages import Message, ToolCallReq
from agent_loop.repair import repair_messages


# ─── 辅助 ────────────────────────────────────────────────────────────────────

def _msg(role: str, content: str = "", *, tool_call_id: str | None = None,
         tool_calls: list[ToolCallReq] | None = None) -> Message:
    return Message(
        role=role,
        content=content,
        tool_call_id=tool_call_id,
        tool_calls=tool_calls or [],
    )


def _tc(tc_id: str) -> ToolCallReq:
    return ToolCallReq(id=tc_id, name="echo", arguments={"text": "x"})


# ─── 1. 孤立 tool 消息被丢弃 ──────────────────────────────────────────────────

def test_orphan_tool_message_dropped():
    """tool 消息的 tool_call_id 不匹配任何前置 assistant tool_call → 丢弃;repair count = 1。"""
    msgs = [
        _msg("user", "hello"),
        _msg("tool", "result", tool_call_id="orphan-id"),  # 没有对应的 assistant
    ]
    count = repair_messages(msgs)
    assert count == 1
    assert len(msgs) == 1
    assert msgs[0].role == "user"


def test_tool_after_assistant_with_empty_tool_calls_dropped():
    """assistant 携带空 tool_calls=[] 后紧跟 tool → 该 tool 仍是孤立(已知集合为空)→ 丢弃。"""
    msgs = [
        _msg("user", "hi"),
        _msg("assistant", "thinking", tool_calls=[]),   # 空 tool_calls → 已知 id 集合为空
        _msg("tool", "result", tool_call_id="x"),
    ]
    count = repair_messages(msgs)
    assert count == 1
    assert [m.role for m in msgs] == ["user", "assistant"]


# ─── 2. 配对的 tool 消息保留 ──────────────────────────────────────────────────

def test_paired_tool_message_kept():
    """tool 消息紧随其 assistant tool_call → 保留;repair count = 0。"""
    msgs = [
        _msg("user", "do it"),
        _msg("assistant", "", tool_calls=[_tc("tc-1")]),
        _msg("tool", "ok", tool_call_id="tc-1"),
    ]
    original_len = len(msgs)
    count = repair_messages(msgs)
    assert count == 0
    assert len(msgs) == original_len
    assert msgs[2].tool_call_id == "tc-1"


# ─── 3. 连续 user 消息合并 ────────────────────────────────────────────────────

def test_consecutive_user_messages_merged():
    """两条相邻 user 消息合并为一条,内容以 '\\n\\n' 分隔,repair count = 1。"""
    msgs = [
        _msg("user", "first"),
        _msg("user", "second"),
    ]
    count = repair_messages(msgs)
    assert count == 1
    assert len(msgs) == 1
    assert msgs[0].content == "first\n\nsecond"


def test_consecutive_user_empty_content_merge():
    """user 合并时,其中一条为空字符串不产生多余分隔符。"""
    msgs = [
        _msg("user", ""),
        _msg("user", "nonempty"),
    ]
    count = repair_messages(msgs)
    assert count == 1
    assert len(msgs) == 1
    assert msgs[0].content == "nonempty"


def test_three_consecutive_user_messages_merged():
    """三条连续 user 消息逐步合并为一条。"""
    msgs = [
        _msg("user", "a"),
        _msg("user", "b"),
        _msg("user", "c"),
    ]
    count = repair_messages(msgs)
    # 两次合并
    assert count == 2
    assert len(msgs) == 1
    assert msgs[0].content == "a\n\nb\n\nc"


# ─── 4. 合法的 ongoing-dialog 模式不被修改 ────────────────────────────────────

def test_valid_ongoing_dialog_not_altered():
    """assistant(tool_calls)+tool+user 是合法的进行中对话模式 → 不修改,repair = 0。"""
    msgs = [
        _msg("user", "请求"),
        _msg("assistant", "", tool_calls=[_tc("tc-ok")]),
        _msg("tool", "工具结果", tool_call_id="tc-ok"),
        _msg("user", "继续"),
    ]
    original_snapshot = [(m.role, m.content, m.tool_call_id) for m in msgs]
    count = repair_messages(msgs)
    assert count == 0
    assert [(m.role, m.content, m.tool_call_id) for m in msgs] == original_snapshot


# ─── 5. 空列表不崩溃 ──────────────────────────────────────────────────────────

def test_empty_list_returns_zero():
    """空消息列表 → 返回 0,不崩溃。"""
    msgs: list[Message] = []
    count = repair_messages(msgs)
    assert count == 0
    assert msgs == []


# ─── 6. 修复后序列 role 顺序合法 ─────────────────────────────────────────────

def test_repaired_sequence_is_role_valid():
    """修复后消息序列不含连续 user 消息也不含孤立 tool 消息。"""
    msgs = [
        _msg("user", "a"),
        _msg("user", "b"),                           # 连续 user → 合并
        _msg("tool", "orphan", tool_call_id="xyz"),  # 孤立 tool → 丢弃
        _msg("user", "c"),
    ]
    repair_messages(msgs)
    # 不能有连续两条相同 role
    for i in range(len(msgs) - 1):
        assert not (msgs[i].role == "user" and msgs[i + 1].role == "user"), \
            "修复后不应有连续 user"
        assert not (msgs[i].role == "tool" and msgs[i + 1].role == "tool"), \
            "修复后不应有连续 tool"
    # 也不应有孤立 tool
    known: set[str] = set()
    for m in msgs:
        if m.role == "assistant":
            known = {tc.id for tc in m.tool_calls}
        elif m.role == "tool":
            assert m.tool_call_id in known, f"孤立 tool: {m.tool_call_id!r}"
        elif m.role == "user":
            known = set()


# ─── 7. 无修复时不重写列表(对象标识保持) ────────────────────────────────────

def test_no_repair_does_not_rewrite_list():
    """无需修复时,消息对象标识保持(in-place 重写不触发)。"""
    m1 = _msg("user", "hi")
    m2 = _msg("assistant", "hello")
    msgs = [m1, m2]
    count = repair_messages(msgs)
    assert count == 0
    assert msgs[0] is m1
    assert msgs[1] is m2


# ─── 8. loop 集成:孤立 tool 消息在迭代前被清理 ──────────────────────────────

def test_loop_calls_repair_on_orphan_tool():
    """循环顶部 repair_messages 调用会在模型调用前清理孤立 tool 消息。"""
    from agent_loop.budget import BudgetTracker
    from agent_loop.config import LoopBudget, LoopConfig
    from agent_loop.conversation import Conversation, InMemoryConversationStore
    from agent_loop.llm import FakeModelCaller, ModelTurn
    from agent_loop.loop import run_loop
    from agent_loop.stubs import echo_tool
    from agent_loop.tools import LoopToolRegistry

    reg = LoopToolRegistry()
    reg.register(echo_tool())

    # 模型只返回一个最终答案
    fake = FakeModelCaller([ModelTurn(content="done", tool_calls=[])])

    # 会话里预埋一条孤立 tool 消息
    conv = Conversation(thread_id="repair-test")
    conv.append(_msg("user", "开始"))
    conv.append(_msg("tool", "stale result", tool_call_id="no-such-assistant-call"))

    cfg = LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=["echo"],
        budget=LoopBudget(max_iterations=5, max_tool_failures=3),
    )
    budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    res = asyncio.run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "completed"
    # 孤立 tool 消息应已从会话中清除
    tool_msgs = [m for m in conv.messages if m.role == "tool" and m.tool_call_id == "no-such-assistant-call"]
    assert tool_msgs == [], "孤立 tool 消息应在 repair 后消失"


# ─── 9. BudgetTracker 不再有 interrupted/request_interrupt ────────────────────

def test_budget_tracker_no_interrupt_attributes():
    """BudgetTracker 不再拥有 interrupted 属性和 request_interrupt 方法。"""
    from agent_loop.budget import BudgetTracker
    from agent_loop.config import LoopBudget

    t = BudgetTracker(LoopBudget(max_iterations=5))
    assert not hasattr(t, "interrupted"), \
        "BudgetTracker.interrupted 应已被移除,中断统一由 RunControl 管理"
    assert not hasattr(t, "request_interrupt"), \
        "BudgetTracker.request_interrupt 应已被移除,中断统一由 RunControl 管理"
