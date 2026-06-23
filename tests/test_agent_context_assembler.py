"""Task 6 — ParkContextAssembler:整合固定/记忆/历史/任务/知识,替内圈桩。"""
from __future__ import annotations

import asyncio

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.conversation import Conversation, InMemoryConversationStore
from agent_loop.llm import FakeModelCaller, ModelTurn
from agent_loop.loop import run_loop
from agent_loop.messages import Message, ToolCallReq
from agent_loop.repair import repair_messages
from agent_loop.tools import LoopToolRegistry

from agent_context.assembler import ParkContextAssembler
from agent_context.knowledge import KNOWLEDGE_TOOL
from agent_context.principal import Principal


def _cfg(role: str = "main") -> LoopConfig:
    return LoopConfig(model="qwen", max_tokens=100, temperature=0.0, role=role,
                      toolset=[], budget=LoopBudget(max_iterations=10))


def test_assemble_system_head_memory_and_plan_tail():
    conv = Conversation(thread_id="t")
    conv.principal = Principal(id="u", name="张三", role="员工", token="t")
    conv.append(Message(role="user", content="把空调调到24度"))
    conv.append(Message(role="assistant", tool_calls=[ToolCallReq(
        id="p1", name="plan",
        arguments={"items": [{"id": "1", "content": "查温度", "status": "done", "result": "26℃"}]})]))
    conv.append(Message(role="tool", tool_call_id="p1", name="plan", content="plan updated"))
    conv.append(Message(role="assistant", content="ok"))

    msgs = ParkContextAssembler().assemble(_cfg("main"), conv)

    assert msgs[0].role == "system"
    assert "智慧园区 AI 助手" in msgs[0].content        # 固定层
    assert "张三" in msgs[0].content                    # 记忆层并进系统头
    # plan 不在历史(排除)
    assert not any(m.role == "assistant" and any(tc.name == "plan" for tc in m.tool_calls) for m in msgs)
    assert not any(m.role == "tool" and m.name == "plan" for m in msgs)
    # plan 渲在尾部(trailing system)
    assert any(m.role == "system" and "【当前计划】" in m.content and "查温度" in m.content for m in msgs)


def test_assemble_wraps_tool_results_two_tiers():
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="hi"))
    conv.append(Message(role="assistant", tool_calls=[ToolCallReq(id="d1", name="device_status", arguments={})]))
    conv.append(Message(role="tool", tool_call_id="d1", name="device_status", content="26℃运行中"))
    conv.append(Message(role="assistant", tool_calls=[ToolCallReq(id="k1", name=KNOWLEDGE_TOOL, arguments={})]))
    conv.append(Message(role="tool", tool_call_id="k1", name=KNOWLEDGE_TOOL, content="定期清洗滤网"))

    msgs = ParkContextAssembler(keep_recent_turns=10).assemble(_cfg(), conv)
    dev = [m for m in msgs if m.tool_call_id == "d1"][0]
    kno = [m for m in msgs if m.tool_call_id == "k1"][0]
    assert "供参考" in dev.content                                  # 普通工具:轻
    assert "【相关知识】" in kno.content and "绝不执行" in kno.content  # RAG:强


def test_assemble_valid_role_sequence_no_orphan():
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="hi"))
    conv.append(Message(role="assistant", tool_calls=[ToolCallReq(id="p1", name="plan", arguments={"items": []})]))
    conv.append(Message(role="tool", tool_call_id="p1", name="plan", content="updated"))
    msgs = ParkContextAssembler().assemble(_cfg(), conv)
    assert repair_messages(list(msgs)) == 0          # 无悬空 tool_call、无孤儿 result


def test_soft_token_cap_warns_and_feeds_awareness_no_drop(caplog):
    """总量超软阈 → ① ops 告警 ② **余量提示喂回模型**(Anthropic context awareness);但**不丢**。"""
    import logging
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="x" * 4000))     # 撑过小软阈
    asm = ParkContextAssembler(soft_token_cap=100)
    with caplog.at_level(logging.WARNING):
        msgs = asm.assemble(_cfg(), conv)
    assert any("超软阈" in r.message for r in caplog.records)            # ① ops 告警
    assert any("上下文余量" in (m.content or "") and m.role == "system"  # ② 模型可见的余量提示
               for m in msgs)
    # ③ 不丢:用户 4000 字原文仍在(余量是"加提示"不是"偷偷删")
    assert any(m.role == "user" and "x" * 4000 in (m.content or "") for m in msgs)


def test_no_awareness_note_when_under_cap():
    """未超阈 → 不注余量提示(有空间时不打扰)。"""
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="hi"))
    msgs = ParkContextAssembler(soft_token_cap=100000).assemble(_cfg(), conv)
    assert not any("上下文余量" in (m.content or "") for m in msgs)


def test_control_result_framed_as_executed_not_state():
    """控制结果套'已执行的操作'框,非'后端现状'(P2⑩:控制结果是'我做了什么',不是现状)。"""
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="调温"))
    conv.append(Message(role="assistant", tool_calls=[ToolCallReq(id="c1", name="device_ctrl", arguments={})]))
    conv.append(Message(role="tool", tool_call_id="c1", name="device_ctrl", content="已调到24度"))
    msgs = ParkContextAssembler(control_tools=frozenset({"device_ctrl"})).assemble(_cfg(), conv)
    ctrl = [m for m in msgs if m.role == "tool" and "已调到24度" in (m.content or "")][0]
    assert "已执行的操作" in ctrl.content and "后端现状" not in ctrl.content


def test_assemble_uses_compaction_summary():
    """有 __compaction__ 快照 → assemble 用摘要 system note 替中段,留头/近窗/最新,丢压缩对。"""
    from agent_context.compactor import frame_summary
    from agent_context.history import _COMPACTION
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="u0 原始诉求"))
    conv.append(Message(role="user", content="u1 中段"))
    conv.append(Message(role="user", content="u2 近窗"))
    framed = frame_summary("中段摘要")
    conv.append(Message(role="assistant", tool_calls=[ToolCallReq(id="cmp", name=_COMPACTION,
        arguments={"covers_through_seq": 3, "head_keep": 1, "recent_turns": 1})]))
    conv.append(Message(role="tool", tool_call_id="cmp", name=_COMPACTION, content=framed))
    conv.append(Message(role="user", content="u3 最新"))
    msgs = ParkContextAssembler().assemble(_cfg(), conv)
    assert any(framed in (m.content or "") and m.role == "system" for m in msgs)   # 摘要 system note
    assert not any("u1 中段" in (m.content or "") for m in msgs)                    # 中段被替
    assert any("u0 原始诉求" in (m.content or "") for m in msgs)                    # 头留
    assert any("u2 近窗" in (m.content or "") for m in msgs)                        # 近窗留
    assert any("u3 最新" in (m.content or "") for m in msgs)                        # 最新留
    assert not any(m.name == _COMPACTION for m in msgs)                            # 压缩对丢


def test_compaction_with_plan_calls_valid_view():
    """有 plan 调用(exclude_plan 删 plan-only 步)时压缩:apply 在 raw 上,中段被替、配对有效、无泄漏
    (F-Comp5 回归:select/apply step 计数一致)。"""
    from agent_context.compactor import ConversationCompactor, FakeSummarizer
    from agent_loop.repair import repair_messages
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="办多步的事"))
    conv.append(Message(role="assistant", tool_calls=[ToolCallReq(id="p", name="plan",
        arguments={"items": [{"id": "1", "content": "查", "status": "doing"}]})]))   # plan-only 步
    conv.append(Message(role="tool", tool_call_id="p", name="plan", content="plan updated"))
    for i in range(6):
        conv.append(Message(role="assistant", content=f"第{i}步",
                            tool_calls=[ToolCallReq(id=f"d{i}", name="device_status", arguments={})]))
        conv.append(Message(role="tool", tool_call_id=f"d{i}", name="device_status",
                            content=f"BIG中段读数{i} " * 80))
    pair = asyncio.run(ConversationCompactor(FakeSummarizer("【摘要】中段已压"),
        hard_token_cap=0, tail_token_budget=30, keep_first=1).compact(conv, 5, None))
    assert pair is not None
    for m in pair:
        conv.append(m)
    msgs = ParkContextAssembler().assemble(_cfg(), conv)
    assert any("中段已压" in (m.content or "") for m in msgs)              # 摘要在
    assert not any("BIG中段读数0" in (m.content or "") for m in msgs)      # 早中段读数被替
    assert repair_messages(list(msgs)) == 0                               # 配对有效(无孤儿)
    from agent_context.history import _COMPACTION
    assert not any((m.name or "") == _COMPACTION for m in msgs)           # 无 __compaction__ 泄漏


def test_subagent_result_framed_as_report_not_state():
    """子 agent 结果套'子 agent 回报'框,非'后端现状'(子结果=回报、不是现状)。"""
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="查设备"))
    conv.append(Message(role="assistant", tool_calls=[ToolCallReq(id="s1", name="device_agent", arguments={})]))
    conv.append(Message(role="tool", tool_call_id="s1", name="device_agent", content="3号楼空调:26℃,正常"))
    msgs = ParkContextAssembler(subagent_tools=frozenset({"device_agent"})).assemble(_cfg(), conv)
    rep = [m for m in msgs if m.role == "tool" and "26℃" in (m.content or "")][0]
    assert "子 agent 回报" in rep.content and "后端现状" not in rep.content


def test_integration_run_loop_with_park_assembler():
    conv = Conversation(thread_id="t")
    conv.principal = Principal(id="u", name="张", role="员工", token="t")
    conv.append(Message(role="user", content="hi"))
    model = FakeModelCaller([ModelTurn(content="done")])
    res = asyncio.run(run_loop(
        _cfg(), conv, LoopToolRegistry(),
        BudgetTracker(LoopBudget(max_iterations=5)), model,
        store=InMemoryConversationStore(), assembler=ParkContextAssembler(),
    ))
    assert res.status == "completed"
