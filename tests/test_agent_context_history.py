"""Task 3 — 历史层缩减(设计 §五,v1 零模型)。

历史层 = 正常用户/模型对话 + 普通工具结果。两个缩减操作(v1):
- ① **丢弃**(`drop_answered_tool_results`):**任务已交付(模型给文本答案)→ 丢其前的工具结果**。
  与 loop 完成判定一致(文本答案=结束,无论 plan);最后一个答案之后(当前任务)/无答案时的
  结果保留。挂起占位 `[pending_confirmation]` 永不丢(恢复锚点)。**不依赖 plan**。
- ② **裁剪**(`trim_dialogue_turns`):按**对话轮数**,保最近 N 轮对话,旧对话整轮丢、留占位
  `[旧对话 N 轮已省略]`。三不丢:① 首轮 ② 近窗 ③ 挂起占位。
- ③ **压缩=摘要**:要模型,**v2 不实现**。v1 不加任何 token fail-safe 冒充压缩。
"""
from __future__ import annotations

from agent_loop.messages import Message, ToolCallReq
from agent_loop.repair import repair_messages

from agent_context.tokens import estimate_tokens
from agent_context.history import drop_answered_tool_results, trim_dialogue_turns


# ── helpers ───────────────────────────────────────────────────────────────────

def _plan_call(items, tid="p1"):
    asst = Message(role="assistant", tool_calls=[ToolCallReq(id=tid, name="plan", arguments={"items": items})])
    tool = Message(role="tool", tool_call_id=tid, name="plan", content="plan updated")
    return asst, tool


def _tool(name, tid, content):
    asst = Message(role="assistant", tool_calls=[ToolCallReq(id=tid, name=name, arguments={})])
    tool = Message(role="tool", tool_call_id=tid, name=name, content=content)
    return asst, tool


def _items(*statuses):
    # statuses like ("done","done","todo") for steps 查温度/调温/汇总
    names = ["查温度", "调温", "汇总"]
    return [{"id": str(i + 1), "content": names[i] if i < len(names) else f"步{i}", "status": s}
            for i, s in enumerate(statuses)]


# ── token 估算器(保留组件,只为单调性) ────────────────────────────────────────

def test_estimate_tokens_monotonic():
    few = [Message(role="user", content="hi")]
    many = [Message(role="user", content="x" * 4000)]
    assert estimate_tokens(many) > estimate_tokens(few)


# ── ① 丢弃:任务交付(文本答案)即丢其前工具结果 ────────────────────────────────

def test_no_text_answer_keeps_all_readings():
    """还没有文本答案(任务进行中)→ 工具结果全留。"""
    rd_a, rd_t = _tool("device_status", "d1", "3号楼3层:当前28.5℃")
    msgs = [Message(role="user", content="查温度")] + [rd_a, rd_t]
    out = drop_answered_tool_results(msgs)
    assert "28.5℃" in [m for m in out if m.tool_call_id == "d1"][0].content


def test_text_answer_drops_prior_readings():
    """文本答案出现 → 其前的工具结果缩成标记(保配对)。"""
    rd_a, rd_t = _tool("device_status", "d1", "3号楼3层:当前28.5℃")
    msgs = [Message(role="user", content="查温度")] + [rd_a, rd_t] + \
           [Message(role="assistant", content="温度28.5℃,正常。")]      # 文本答案=交付
    out = drop_answered_tool_results(msgs)
    reading = [m for m in out if m.tool_call_id == "d1"][0]
    assert "28.5℃" not in reading.content and "已省略" in reading.content
    assert reading.tool_call_id == "d1"                              # 配对保住


def test_unfinished_plan_with_answer_still_drops():
    """关键:plan 还有 todo,但给了文本答案 → 照样丢(丢弃不依赖 plan)。"""
    a, t = _plan_call(_items("done", "todo", "todo"))                # plan 没完成
    rd_a, rd_t = _tool("device_status", "d1", "28.5℃")
    msgs = [Message(role="user", content="q")] + [a, t] + [rd_a, rd_t] + \
           [Message(role="assistant", content="就到这,结论给你。")]      # 文本答案
    out = drop_answered_tool_results(msgs)
    assert "28.5℃" not in [m for m in out if m.tool_call_id == "d1"][0].content


def test_current_task_readings_after_last_answer_kept():
    """多任务:最后一个文本答案之后(当前任务)的读数保留;之前(已答任务)的丢。"""
    rd1_a, rd1_t = _tool("device_status", "d1", "任务1:26℃")
    ans1 = Message(role="assistant", content="任务1答案。")
    rd2_a, rd2_t = _tool("device_status", "d2", "任务2:30℃")          # 当前任务,还没答
    msgs = ([Message(role="user", content="t1")] + [rd1_a, rd1_t] + [ans1]
            + [Message(role="user", content="t2")] + [rd2_a, rd2_t])
    out = drop_answered_tool_results(msgs)
    assert "26℃" not in [m for m in out if m.tool_call_id == "d1"][0].content   # 已答任务→丢
    assert "30℃" in [m for m in out if m.tool_call_id == "d2"][0].content       # 当前任务→留


def test_pending_never_blanked_before_answer():
    """挂起占位即使在文本答案之前,也永不缩(恢复锚点)。"""
    ph_a = Message(role="assistant", tool_calls=[ToolCallReq(id="c1", name="device_ctrl", arguments={})])
    ph_t = Message(role="tool", tool_call_id="c1", name="device_ctrl", content="[pending_confirmation]")
    msgs = [Message(role="user", content="调温")] + [ph_a, ph_t] + \
           [Message(role="assistant", content="已发起,待确认。")]
    out = drop_answered_tool_results(msgs)
    assert [m for m in out if m.tool_call_id == "c1"][0].content == "[pending_confirmation]"


def test_propose_result_protected_from_drop():
    """★控制提案是延迟动作:propose_control 结果在被执行前**不丢**(即便后面已给文本答案),
    否则模型忘了已提案→重复提案。四不丢之一。"""
    pr_a, pr_t = _tool("propose_control", "p1", "控制提案已登记(对「空调机组106」温度=24）。")
    msgs = [Message(role="user", content="把106调到24")] + [pr_a, pr_t] + \
           [Message(role="assistant", content="好的,正在为你发起确认。")]   # 已给文本
    out = drop_answered_tool_results(msgs)
    kept = [m for m in out if m.tool_call_id == "p1"][0]
    assert "空调机组106" in kept.content and "已省略" not in kept.content    # 未被缩


def test_drop_preserves_pairing():
    """丢弃后过 repair_messages 无孤儿。"""
    rd_a, rd_t = _tool("device_status", "d1", "28.5℃" * 30)
    msgs = [Message(role="user", content="first")] + [rd_a, rd_t] + \
           [Message(role="assistant", content="答案。")]
    out = drop_answered_tool_results(msgs)
    assert repair_messages(list(out)) == 0


# ── ② 裁剪:对话轮数 ───────────────────────────────────────────────────────────

def test_trim_keeps_recent_turns_drops_older():
    """超过 keep_recent_turns 的旧对话整轮丢,留占位;首轮+近窗保留。"""
    msgs = [Message(role="user", content="FIRST"), Message(role="assistant", content="a0")]
    for i in range(6):
        msgs.append(Message(role="user", content=f"u{i}"))
        msgs.append(Message(role="assistant", content=f"a{i}"))
    msgs.append(Message(role="user", content="RECENT"))
    out = trim_dialogue_turns(msgs, keep_recent_turns=2, keep_first=1)
    assert out[0].content == "FIRST"                     # 首轮头保护
    assert any(m.content == "RECENT" for m in out)       # 近窗保留
    assert any("旧对话" in (m.content or "") and "省略" in (m.content or "") for m in out)
    # 被丢的中段旧对话不再出现
    assert not any((m.content or "").startswith("u1") for m in out)


def test_trim_short_dialogue_unchanged():
    """轮数没超阈 → 原样不动。"""
    msgs = [Message(role="user", content="hi"), Message(role="assistant", content="ok"),
            Message(role="user", content="again")]
    out = trim_dialogue_turns(msgs, keep_recent_turns=5, keep_first=1)
    assert out == msgs


def test_trim_keeps_pending_placeholder():
    """三不丢之三:挂起占位即使落在旧轮也不丢。"""
    a = Message(role="assistant", tool_calls=[ToolCallReq(id="c1", name="device_ctrl", arguments={})])
    ph = Message(role="tool", tool_call_id="c1", name="device_ctrl", content="[pending_confirmation]")
    msgs = [Message(role="user", content="FIRST")]
    for i in range(5):
        msgs.append(Message(role="user", content=f"u{i}"))
        msgs.append(Message(role="assistant", content=f"a{i}"))
    # 挂起占位埋在旧轮里
    msgs[2:2] = [a, ph]
    msgs.append(Message(role="user", content="RECENT"))
    out = trim_dialogue_turns(msgs, keep_recent_turns=2, keep_first=1)
    assert any((m.content or "") == "[pending_confirmation]" for m in out)   # 占位 survive


def test_trim_does_not_truncate_long_single_message():
    """裁剪是按轮数,不是按单条长度——长单条对话内容**不**被截断。"""
    long_msg = Message(role="assistant", content="详情" * 2000)
    msgs = [Message(role="user", content="hi"), long_msg, Message(role="user", content="again")]
    out = trim_dialogue_turns(msgs, keep_recent_turns=5, keep_first=1)
    kept = [m for m in out if m.role == "assistant"][0]
    assert kept.content == "详情" * 2000 and "截断" not in kept.content


def _orphan_tool_count(messages):
    """统计孤儿 tool 结果(tool_call_id 不匹配任何前置 assistant tool_call)。"""
    known: set[str] = set()
    orphans = 0
    for m in messages:
        if m.role == "assistant":
            known = {tc.id for tc in (m.tool_calls or [])}
        elif m.role == "tool":
            if not (m.tool_call_id and m.tool_call_id in known):
                orphans += 1
        elif m.role == "user":
            known = set()
    return orphans


def test_trim_preserves_pairing():
    """裁剪后无孤儿 tool 结果(不破工具配对)。

    注:裁剪占位是 role=user,可能与相邻 user 连续 → assembler 末尾的 repair_messages
    会合并(那是合法 merge、非孤儿)。这里只钉**配对**:没有孤儿 tool。
    """
    msgs = [Message(role="user", content="FIRST")]
    a, t = _tool("device_status", "d1", "26℃")
    for i in range(5):
        msgs.append(Message(role="user", content=f"u{i}"))
        msgs.append(Message(role="assistant", content=f"a{i}"))
    msgs[2:2] = [a, t]
    msgs.append(Message(role="user", content="RECENT"))
    out = trim_dialogue_turns(msgs, keep_recent_turns=2, keep_first=1)
    assert _orphan_tool_count(out) == 0
    # 过一遍 repair(模拟 assembler)后仍无孤儿
    repaired = list(out)
    repair_messages(repaired)
    assert _orphan_tool_count(repaired) == 0


# ── 综合 acceptance 例 ─────────────────────────────────────────────────────────

def test_worked_example_kept_while_running_dropped_after_answer():
    """acceptance:任务进行中读数全留;给出文本答案后读数被丢。"""
    rd_a, rd_t = _tool("device_status", "d1", "3号楼3层:当前28.5℃")
    base = [Message(role="user", content="查并调")] + [rd_a, rd_t]
    # 进行中:最后一条是带 tool_call 的 assistant(非文本答案)→ 读数留
    running = base + [Message(role="assistant", content="",
                              tool_calls=[ToolCallReq(id="y", name="device_ctrl", arguments={})])]
    assert "28.5℃" in [m for m in drop_answered_tool_results(running) if m.tool_call_id == "d1"][0].content
    # 给出文本答案后 → 读数被丢
    done = base + [Message(role="assistant", content="已处理,28.5℃偏高已调。")]
    assert "28.5℃" not in [m for m in drop_answered_tool_results(done) if m.tool_call_id == "d1"][0].content
