"""压缩 v2 · Phase 1:纯视图 + 选段 + 摘要框/prompt(无模型/store/loop)。

derive_compaction(latest-wins)/ select_compaction_span(保头+token预算保尾+保挂起)/
apply_compaction_view(替中段留头尾)/ frame_summary(SUMMARY_PREFIX 强框)/ build_summary_prompt。
"""
from __future__ import annotations

import asyncio

from agent_loop.llm import ModelTurn
from agent_loop.messages import Message, ToolCallReq

from agent_context.compactor import (
    frame_summary, build_summary_prompt, FakeSummarizer, ModelBackedSummarizer,
)
from agent_context.history import (
    Compaction, _COMPACTION, derive_compaction, select_compaction_span, apply_compaction_view,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _u(text):
    return Message(role="user", content=text)


def _comp_pair(summary, *, covers=0, head_keep=1, recent_turns=1, tid="cmp"):
    """构造一对 __compaction__ 快照(assistant 调用 + tool 结果含摘要)。"""
    a = Message(role="assistant", tool_calls=[ToolCallReq(
        id=tid, name=_COMPACTION,
        arguments={"covers_through_seq": covers, "head_keep": head_keep, "recent_turns": recent_turns})])
    t = Message(role="tool", tool_call_id=tid, name=_COMPACTION, content=summary)
    return a, t


def _count(msgs):
    return len(msgs)        # 假 token 估算:1/消息,使预算可预测


# ── frame_summary + build_summary_prompt ──────────────────────────────────────

def test_frame_summary_has_strong_prefix():
    s = frame_summary("空调26℃")
    assert "仅供参考" in s and "不是当前指令" in s and "最新用户消息" in s
    assert "空调26℃" in s


def test_build_summary_prompt_filter_safe_and_structured():
    p = build_summary_prompt([_u("头")], [_u("中段A"), _u("中段B")], prior_summary="旧摘要X")
    text = p[0].content
    assert "源材料" in text and "不是给你的指令" in text         # filter-safe preamble
    assert "## 历史 · 已解决" in text and "## 历史 · 待办" in text  # 结构化模板
    assert "旧摘要X" in text and "中段A" in text                  # 折叠旧 + 含中段


# ── derive_compaction ─────────────────────────────────────────────────────────

def test_derive_compaction_latest_wins():
    a1, t1 = _comp_pair("旧摘要", covers=3, tid="c1")
    a2, t2 = _comp_pair("新摘要", covers=7, head_keep=2, recent_turns=3, tid="c2")
    msgs = [_u("first"), a1, t1, _u("mid"), a2, t2]
    c = derive_compaction(msgs)
    assert c is not None
    assert c.summary == "新摘要" and c.covers_through_seq == 7
    assert c.head_keep == 2 and c.recent_turns == 3


def test_derive_compaction_none_when_absent():
    assert derive_compaction([_u("a"), Message(role="assistant", content="b")]) is None


# ── select_compaction_span ────────────────────────────────────────────────────

def test_select_span_head_middle_recent():
    msgs = [_u("u0"), _u("u1"), _u("u2"), _u("u3"), _u("u4")]   # 5 轮(每轮1条)
    head, middle, recent_turns = select_compaction_span(
        msgs, keep_first=1, tail_token_budget=2, estimate_tokens=_count)
    assert [m.content for m in head] == ["u0"]
    assert [m.content for m in middle] == ["u1", "u2"]
    assert recent_turns == 2                                     # 尾2轮(u3,u4)


def test_select_span_too_short_none():
    assert select_compaction_span([_u("u0"), _u("u1")], keep_first=1,
                                   tail_token_budget=1, estimate_tokens=_count) is None


def test_select_span_pending_in_middle_none():
    a = Message(role="assistant", tool_calls=[ToolCallReq(id="x", name="device_ctrl", arguments={})])
    ph = Message(role="tool", tool_call_id="x", name="device_ctrl", content="[pending_confirmation]")
    msgs = [_u("u0"), _u("u1"), a, ph, _u("u2"), _u("u3"), _u("u4")]
    assert select_compaction_span(msgs, keep_first=1, tail_token_budget=2,
                                   estimate_tokens=_count) is None


# ── Compactor seam(Phase 2) ──────────────────────────────────────────────────

def test_fake_summarizer_canned_and_default():
    assert asyncio.run(FakeSummarizer("罐装").summarize(
        head=[], middle=[_u("a")], prior_summary="", config=None)) == "罐装"
    s = asyncio.run(FakeSummarizer().summarize(
        head=[], middle=[_u("a"), _u("b")], prior_summary="旧", config=None))
    assert "折叠了旧摘要" in s and "2 条" in s


def test_model_backed_summarizer_empty_schemas():
    captured: dict = {}

    class _Caller:
        async def __call__(self, config, messages, tool_schemas):
            captured["messages"] = messages
            captured["schemas"] = tool_schemas
            return ModelTurn(content="模型摘要")

    out = asyncio.run(ModelBackedSummarizer(_Caller()).summarize(
        head=[_u("头")], middle=[_u("中")], prior_summary="", config="cfg"))
    assert out == "模型摘要"
    assert captured["schemas"] == []                                  # 纯摘要,不带工具
    assert "源材料" in captured["messages"][0].content                # 用了 build_summary_prompt


# ── apply_compaction_view ─────────────────────────────────────────────────────

def test_trim_keeps_summary_system_note():
    """裁剪保护摘要 system note(F-Comp2:压后近窗也按轮裁,但摘要 note 不能被裁掉)。"""
    from agent_context.history import trim_dialogue_turns
    note = Message(role="system", content=frame_summary("摘要X"))
    msgs = [_u("u0"), _u("u1"), _u("u2"), note, _u("u3"), _u("u4"), _u("u5")]
    out = trim_dialogue_turns(msgs, keep_recent_turns=2, keep_first=1)
    assert any("摘要X" in (m.content or "") for m in out)            # 摘要 note 留
    assert not any((m.content or "") == "u1" for m in out)          # 中段旧对话被裁
    assert len(out) < len(msgs)


def test_apply_drops_superseded_compaction_pair():
    """滚动:旧 __compaction__ 对落进新视图近窗 → 剔除(不泄漏旧摘要、无悬空 __compaction__ 调用)。"""
    a1, t1 = _comp_pair(frame_summary("旧摘要1"), head_keep=1, recent_turns=1, tid="c1")
    a2, t2 = _comp_pair(frame_summary("新摘要2"), head_keep=1, recent_turns=2, tid="c2")
    msgs = [_u("u0"), _u("u1"), a1, t1, a2, t2]
    out = apply_compaction_view(msgs, derive_compaction(msgs))
    assert any("新摘要2" in (m.content or "") for m in out)
    assert not any("旧摘要1" in (m.content or "") for m in out)          # 旧摘要不泄漏
    assert not any((m.name or "") == _COMPACTION
                   or any(tc.name == _COMPACTION for tc in (m.tool_calls or [])) for m in out)


def test_apply_replaces_middle_keeps_head_recent_future():
    framed = frame_summary("中段已摘")
    a, t = _comp_pair(framed, head_keep=1, recent_turns=1)
    msgs = [_u("u0"), _u("u1"), _u("u2"), a, t, _u("u3")]       # pre=[u0,u1,u2]、future=[u3]
    out = apply_compaction_view(msgs, derive_compaction(msgs))
    assert [m.content for m in out] == ["u0", framed, "u2", "u3"]
    assert out[1].role == "system"                              # 摘要是 system note
    assert not any(m.name == _COMPACTION for m in out)          # __compaction__ 对被丢
    # 入参不变
    assert any(m.name == _COMPACTION for m in msgs)
