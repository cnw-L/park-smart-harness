"""test_agent_loop_context.py — TDD for LayeredContextAssembler (Task S4)

五层分层组装(固定/记忆/知识/历史/任务),缓存序:
  - 固定层(system)必须跨迭代稳定,plan 不得出现在其中
  - plan 渲染为最后一条 Message(volatile tail),在历史之后
  - 记忆/知识层以 hook 注入,默认为空,位于固定层与历史层之间
"""
from __future__ import annotations

import asyncio
import pytest

from agent_loop.context import LayeredContextAssembler
from agent_loop.config import LoopConfig, LoopBudget
from agent_loop.conversation import Conversation, InMemoryConversationStore
from agent_loop.messages import Message
from agent_loop.plan import PlanState, make_plan_tool
from agent_loop.budget import BudgetTracker
from agent_loop.loop import run_loop
from agent_loop.tools import LoopToolRegistry
from agent_loop.stubs import echo_tool
from agent_loop.llm import FakeModelCaller, ModelTurn


# ─── 辅助 ─────────────────────────────────────────────────────────────────────

def _cfg(role: str = "test") -> LoopConfig:
    return LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role=role,
        toolset=["echo"], budget=LoopBudget(max_iterations=5),
    )


def _conv_with_user(thread_id: str = "t") -> Conversation:
    c = Conversation(thread_id=thread_id)
    c.append(Message(role="user", content="你好"))
    return c


def _plan_with_items(conv: Conversation) -> str:
    """给 conv.plan 写入一条 plan 并返回渲染文本。"""
    conv.plan.replace([{"id": "1", "content": "查设备", "status": "todo"}])
    text = conv.plan.render()
    assert text  # 确保非空
    return text


# ─── 1. 固定层稳定:position-0 system 消息不含 plan ──────────────────────────

def test_stable_system_does_not_contain_plan():
    """position-0 message 是 role=system 的固定层;plan 不进入其中。"""
    cfg = _cfg()
    conv = _conv_with_user()
    plan_text = _plan_with_items(conv)

    assembler = LayeredContextAssembler()
    msgs = assembler.assemble(cfg, conv)

    # position-0 必须是 system
    assert msgs[0].role == "system"
    # 固定层 content 不应含 plan 文本
    assert plan_text not in msgs[0].content
    assert "当前计划" not in msgs[0].content


def test_stable_system_contains_role_and_instructions():
    """固定层含 role 信息和基础 agent 指令。"""
    cfg = _cfg(role="supervisor")
    conv = _conv_with_user()

    assembler = LayeredContextAssembler()
    msgs = assembler.assemble(cfg, conv)

    sys_content = msgs[0].content
    assert "supervisor" in sys_content
    assert "agent" in sys_content


def test_system_unchanged_when_plan_changes():
    """plan 改变前后,position-0 system 消息内容完全相同(缓存前缀稳定性)。"""
    cfg = _cfg()
    conv = _conv_with_user()
    assembler = LayeredContextAssembler()

    # 无 plan 时
    msgs_before = assembler.assemble(cfg, conv)
    sys_before = msgs_before[0].content

    # 写入 plan
    _plan_with_items(conv)
    msgs_after = assembler.assemble(cfg, conv)
    sys_after = msgs_after[0].content

    # system 内容必须完全相同
    assert sys_before == sys_after


# ─── 2. plan 放在 volatile tail(历史之后、最后一条) ──────────────────────────

def test_plan_placed_as_last_message_after_history():
    """非空 plan → 渲染文本出现在最后一条 Message,在历史之后。"""
    cfg = _cfg()
    conv = _conv_with_user()
    conv.append(Message(role="assistant", content="好的"))
    conv.append(Message(role="user", content="继续"))
    plan_text = _plan_with_items(conv)

    assembler = LayeredContextAssembler()
    msgs = assembler.assemble(cfg, conv)

    last = msgs[-1]
    assert plan_text in last.content

    # plan 必须在历史之后:默认无 memory/knowledge hook,布局 = [system] + history + [plan]。
    # 结构断言(不靠内容匹配):plan 是最后一条,且恰在 system+history 之后。
    assert len(msgs) == 1 + len(conv.messages) + 1   # system + history + plan-tail
    assert msgs[-1] is last                          # plan 在末尾


def test_plan_not_in_system_prefix():
    """plan 渲染文本不出现在 msgs[0](system 前缀)中。"""
    cfg = _cfg()
    conv = _conv_with_user()
    plan_text = _plan_with_items(conv)

    assembler = LayeredContextAssembler()
    msgs = assembler.assemble(cfg, conv)

    assert plan_text not in msgs[0].content


# ─── 3. 空 plan → 无 trailing plan 消息 ─────────────────────────────────────

def test_empty_plan_no_trailing_message():
    """plan 为空 → assembled = system + history,无 trailing plan 消息。"""
    cfg = _cfg()
    conv = _conv_with_user()
    # 不写 plan,保持空

    assembler = LayeredContextAssembler()
    msgs = assembler.assemble(cfg, conv)

    # system + 1 user = 2 条
    assert len(msgs) == 2
    assert msgs[0].role == "system"
    assert msgs[1].role == "user"
    assert "当前计划" not in "".join(m.content for m in msgs)


# ─── 4. 记忆/知识 hook ────────────────────────────────────────────────────────

def test_memory_hook_injected_after_system_before_history():
    """memory hook 返回的 Message 列表出现在 system 之后、历史之前。"""
    cfg = _cfg()
    conv = _conv_with_user()

    mem_msg = Message(role="system", content="MEM:用户偏好A")
    assembler = LayeredContextAssembler(
        memory=lambda c, cv: [mem_msg]
    )
    msgs = assembler.assemble(cfg, conv)

    # 顺序:system → MEM → user
    assert msgs[0].role == "system"
    assert msgs[1].content == "MEM:用户偏好A"
    # user 历史在 MEM 之后
    user_idx = next(i for i, m in enumerate(msgs) if m.role == "user")
    mem_idx = next(i for i, m in enumerate(msgs) if m.content == "MEM:用户偏好A")
    assert mem_idx < user_idx


def test_knowledge_hook_injected_after_memory_before_history():
    """knowledge hook 返回的 Message 列表出现在 memory 之后、历史之前。"""
    cfg = _cfg()
    conv = _conv_with_user()

    mem_msg = Message(role="system", content="MEM:记忆")
    know_msg = Message(role="system", content="KNOW:知识库段落")
    assembler = LayeredContextAssembler(
        memory=lambda c, cv: [mem_msg],
        knowledge=lambda c, cv: [know_msg],
    )
    msgs = assembler.assemble(cfg, conv)

    indices = {m.content: i for i, m in enumerate(msgs)}
    # system(固定) < memory < knowledge < user(历史)
    assert indices[msgs[0].content] < indices["MEM:记忆"]
    assert indices["MEM:记忆"] < indices["KNOW:知识库段落"]
    user_idx = next(i for i, m in enumerate(msgs) if m.role == "user")
    assert indices["KNOW:知识库段落"] < user_idx


def test_default_hooks_inject_nothing():
    """默认 hook(无注入)时,assembled 仅含 system + history(+ trailing plan 若有)。"""
    cfg = _cfg()
    conv = _conv_with_user()

    assembler = LayeredContextAssembler()
    msgs = assembler.assemble(cfg, conv)

    # 2 条:system + user
    assert len(msgs) == 2


def test_memory_and_knowledge_hooks_with_plan():
    """hook + plan 综合:顺序 = system → mem → know → history → plan(tail)。"""
    cfg = _cfg()
    conv = _conv_with_user()
    plan_text = _plan_with_items(conv)

    mem_msg = Message(role="system", content="MEM")
    know_msg = Message(role="system", content="KNOW")
    assembler = LayeredContextAssembler(
        memory=lambda c, cv: [mem_msg],
        knowledge=lambda c, cv: [know_msg],
    )
    msgs = assembler.assemble(cfg, conv)

    # system → MEM → KNOW → user → plan
    contents = [m.content for m in msgs]
    mem_idx = contents.index("MEM")
    know_idx = contents.index("KNOW")
    user_idx = next(i for i, m in enumerate(msgs) if m.role == "user")
    plan_idx = len(msgs) - 1

    assert msgs[0].role == "system"
    assert mem_idx == 1
    assert know_idx == 2
    assert user_idx == 3
    assert plan_text in msgs[plan_idx].content


# ─── 5. 缺 user 消息保护 ──────────────────────────────────────────────────────

def test_guard_raises_on_no_user_message():
    """会话缺 user 消息 → raise ValueError(role-alternation 保护)。"""
    cfg = _cfg()
    conv = Conversation(thread_id="t")
    # 不 append 任何 user 消息

    assembler = LayeredContextAssembler()
    with pytest.raises(ValueError, match="user 消息"):
        assembler.assemble(cfg, conv)


# ─── 6. 集成 sanity:含非空 plan 的 loop run 仍正常完成 ──────────────────────

def test_loop_with_nonempty_plan_still_completes():
    """非空 plan 的 loop run 不因 assembler 变更而 crash;FakeModelCaller 完成一轮。"""
    cfg = LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=["echo"], budget=LoopBudget(max_iterations=5),
    )
    conv = Conversation(thread_id="sanity")
    conv.append(Message(role="user", content="开始"))
    # 给 plan 写入内容
    conv.plan.replace([{"id": "1", "content": "执行查询", "status": "doing"}])

    reg = LoopToolRegistry()
    reg.register(echo_tool())
    fake = FakeModelCaller([ModelTurn(content="完成", tool_calls=[])])
    budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    res = asyncio.run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "completed"
    assert res.final == "完成"
