"""压缩 v2 · Phase 4:loop 集成(InMem + FakeModelCaller + FakeSummarizer)。

长请求超硬阈 → loop 触发压缩(独立 commit __compaction__ 对)→ 重组落阈下 → 正常完成;
压完仍超(摘要不缩)→ thrash 守卫 reason=compaction_thrash。
"""
from __future__ import annotations

import asyncio
import json

from agent_loop.budget import BudgetTracker
from agent_loop.codec import decode_messages, encode_messages
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.conversation import Boundary, Conversation, InMemoryConversationStore
from agent_loop.llm import FakeModelCaller, ModelTurn
from agent_loop.loop import run_loop
from agent_loop.messages import Message, ToolCallReq
from agent_loop.tools import LoopToolRegistry

from agent_context.assembler import ParkContextAssembler
from agent_context.compactor import ConversationCompactor, FakeSummarizer
from agent_context.history import _COMPACTION, derive_compaction


def _comp_msgs(summary, *, covers=0, head_keep=1, recent_turns=1, tid="cmp"):
    a = Message(role="assistant", tool_calls=[ToolCallReq(
        id=tid, name=_COMPACTION,
        arguments={"covers_through_seq": covers, "head_keep": head_keep, "recent_turns": recent_turns})])
    t = Message(role="tool", tool_call_id=tid, name=_COMPACTION, content=summary)
    return a, t


def _cfg():
    return LoopConfig(model="x", max_tokens=100, temperature=0.0, role="main",
                      toolset=[], budget=LoopBudget(max_iterations=10))


def _long_conv():
    """**单个长请求**(1 个 user 轮)内部很多 assistant 迭代步 + 大工具结果。
    这是压缩的真实场景:裁剪按 user 轮数(单请求只 1 轮)不触发、丢弃要文本答案(没给)也不触发,
    工具结果只增不减 → 视窗膨胀 → 压缩按**步**摘中段。"""
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="办一件需要很多步的复杂事"))
    for i in range(10):                                # 10 个迭代步,大工具结果
        conv.append(Message(role="assistant", content=f"第{i}步",
                            tool_calls=[ToolCallReq(id=f"d{i}", name="device_status", arguments={})]))
        conv.append(Message(role="tool", tool_call_id=f"d{i}", name="device_status",
                            content="读数详情" * 100))      # 大
    return conv


def _run(conv, model, compactor):
    return asyncio.run(run_loop(
        _cfg(), conv, LoopToolRegistry(), BudgetTracker(LoopBudget(max_iterations=10)),
        model, store=InMemoryConversationStore(),
        assembler=ParkContextAssembler(), compaction=compactor))


def test_compaction_fires_on_long_request():
    conv = _long_conv()
    res = _run(conv, FakeModelCaller([ModelTurn(content="最终答案")]),
               ConversationCompactor(FakeSummarizer("【摘要】中段已压"),
                                     hard_token_cap=800, tail_token_budget=20, keep_first=1))
    assert res.status == "completed" and res.final == "最终答案"
    # 提交了 __compaction__ 对(压缩发生)
    assert any(m.role == "tool" and m.name == "__compaction__" for m in conv.messages)
    assert any(m.role == "assistant" and any(tc.name == "__compaction__" for tc in m.tool_calls)
               for m in conv.messages)


def test_compaction_charges_budget():
    """压缩=一次 aux 模型调用 → 计预算(F-Comp3):压一次后迭代计数 = 主调用 + 压缩 ≥ 2。"""
    conv = _long_conv()
    budget = BudgetTracker(LoopBudget(max_iterations=10))
    res = asyncio.run(run_loop(
        _cfg(), conv, LoopToolRegistry(), budget,
        FakeModelCaller([ModelTurn(content="最终答案")]), store=InMemoryConversationStore(),
        assembler=ParkContextAssembler(),
        compaction=ConversationCompactor(FakeSummarizer("【摘要】中段已压"),
                                         hard_token_cap=800, tail_token_budget=20, keep_first=1)))
    assert res.status == "completed"
    assert budget.snapshot()["iters"] >= 2        # 压缩没"白嫖"预算


def test_no_compaction_when_under_cap():
    """短会话不超硬阈 → 不压缩。"""
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="你好"))
    res = _run(conv, FakeModelCaller([ModelTurn(content="答")]),
               ConversationCompactor(FakeSummarizer("x"), hard_token_cap=100000,
                                     tail_token_budget=20, keep_first=1))
    assert res.status == "completed"
    assert not any((m.name or "") == "__compaction__" for m in conv.messages)


def test_compaction_thrash_guard():
    """摘要比原文还大(不缩)→ 压完仍超 → 几次后 compaction_thrash 停。"""
    conv = _long_conv()
    res = _run(conv, FakeModelCaller([ModelTurn(content="答")]),
               ConversationCompactor(FakeSummarizer("巨" * 3000),   # 摘要巨大,缩不下来
                                     hard_token_cap=800, tail_token_budget=20, keep_first=1))
    assert res.status == "failed" and res.reason == "compaction_thrash"


# ── Phase 5:持久化 / 重载(Option D:摘要是普通消息对,随 codec/load 存活) ──────

def test_compaction_survives_codec_roundtrip():
    a, t = _comp_msgs("【摘要】Y", covers=3, head_keep=2, recent_turns=4)
    decoded = decode_messages(json.loads(json.dumps(
        encode_messages([Message(role="user", content="u"), a, t]))))
    c = derive_compaction(decoded)
    assert c is not None
    assert c.summary == "【摘要】Y" and c.covers_through_seq == 3
    assert c.head_keep == 2 and c.recent_turns == 4


def test_compaction_survives_store_load():
    store = InMemoryConversationStore()
    a, t = _comp_msgs("【摘要】X", covers=4)
    asyncio.run(store.commit("th", [Message(role="user", content="u"), a, t],
                             Boundary("iteration", "turn-1", 1, None, None)))
    conv = asyncio.run(store.load("th"))
    c = derive_compaction(conv.messages)
    assert c is not None and "X" in c.summary and c.covers_through_seq == 4


# ── Phase 6:滚动再压缩(latest-wins + 折叠旧摘要) ────────────────────────────

def test_rolling_recompaction_folds_prior():
    seen: list[str] = []

    class _Recording:
        async def summarize(self, *, head, middle, prior_summary, config):
            seen.append(prior_summary)
            return f"摘要{len(seen)}"

    cc = ConversationCompactor(_Recording(), hard_token_cap=0, tail_token_budget=5, keep_first=1)
    conv = _long_conv()
    pair1 = asyncio.run(cc.compact(conv, 5, None))
    assert pair1 is not None
    for m in pair1:
        conv.append(m)
    pair2 = asyncio.run(cc.compact(conv, 6, None))
    assert pair2 is not None
    for m in pair2:
        conv.append(m)
    assert seen[0] == ""                       # 1st:无 prior
    assert "摘要1" in seen[1]                    # 2nd:折叠了 1st(framed 摘要含"摘要1")
    c = derive_compaction(conv.messages)
    assert "摘要2" in c.summary and c.covers_through_seq == 6   # latest-wins
