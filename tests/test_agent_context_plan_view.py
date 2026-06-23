"""Task 4 — 任务层:plan.py(result/容错)+ 中圈 plan_view(渲染人话/排除两 case)。"""
from __future__ import annotations

from agent_loop.messages import Message, ToolCallReq
from agent_loop.plan import PlanItem, PlanState, make_plan_tool
from agent_loop.repair import repair_messages

from agent_context.plan_view import exclude_plan_calls, render_plan


# ── plan.py 改动 ──────────────────────────────────────────────────────────────

def test_planitem_has_result():
    assert PlanItem(id="1", content="查温度", status="done", result="26℃").result == "26℃"


def test_replace_tolerant():
    ps = PlanState()
    ps.replace([
        {"id": "1", "content": "查", "status": "done", "result": "26℃"},
        {"id": "2", "content": "调"},          # 缺 status → 默认 todo
        {"content": "无id跳过"},                # 缺 id → 跳过
        {"id": "4"},                            # 缺 content → 跳过
    ])
    assert len(ps.items) == 2
    assert ps.items[1].status == "todo"
    assert ps.items[0].result == "26℃"


def test_plan_tool_schema_has_result():
    tool = make_plan_tool(PlanState())
    props = tool.parameters["properties"]["items"]["items"]["properties"]
    assert "result" in props


# ── 中圈 render_plan(人话,无 spec dump) ──────────────────────────────────────

def test_render_plan_human():
    ps = PlanState()
    ps.replace([
        {"id": "1", "content": "查温度", "status": "done", "result": "26℃,偏高",
         "spec": {"device_id": "ac-301"}},
        {"id": "2", "content": "调24度", "status": "doing", "result": "待确认"},
        {"id": "3", "content": "汇总", "status": "todo"},
    ])
    s = render_plan(ps)
    assert "【当前计划】" in s
    assert "查温度" in s and "26℃,偏高" in s and "调24度" in s
    assert "ac-301" not in s and "device_id" not in s   # spec dict 不 dump


def test_render_plan_caps_long_result():
    """单步 result 过长 → 渲染截断(不撑大尾部近窗),不动 plan 本体。"""
    ps = PlanState()
    ps.replace([{"id": "1", "content": "查", "status": "done", "result": "详情" * 100}])
    s = render_plan(ps, max_result_chars=20)
    assert "…" in s
    result_line = [ln for ln in s.splitlines() if "详情" in ln][0]
    assert len(result_line) < 60                        # 截断生效
    assert ps.items[0].result == "详情" * 100           # 本体不动


def test_render_plan_long_fold():
    ps = PlanState()
    ps.replace([{"id": str(i), "content": f"步{i}", "status": "done"} for i in range(10)]
               + [{"id": "x", "content": "当前步", "status": "doing"}])
    s = render_plan(ps, max_items=5)
    assert "已完成" in s            # 远处 done 折成计数
    assert "当前步" in s


def test_render_plan_appends_execute_directive():
    """有未完成步 → 尾部带"执行下一步 / 别再调 plan"指令(防 qwen 见计划原地反复重列→stall)。
    plan 调用已从历史排除、模型看不到自己列过,故这条尾部指令是推它执行的唯一信号。"""
    ps = PlanState()
    ps.replace([
        {"id": "1", "content": "查温度", "status": "done", "result": "26℃"},
        {"id": "2", "content": "调到24度", "status": "todo"},
    ])
    s = render_plan(ps)
    assert "调到24度" in s                          # 点名下一个未完成步
    assert "不要再调用 plan" in s and "执行" in s    # 别重列计划 + 推执行


def test_render_plan_all_done_directive():
    """全 done → 尾部指令推"直接给文本总结、别再调工具"(防完成后还在重列计划)。"""
    ps = PlanState()
    ps.replace([{"id": "1", "content": "查", "status": "done", "result": "ok"}])
    s = render_plan(ps)
    assert "已完成" in s and "汇报" in s and "不要再调" in s


# ── 历史视图排除 plan 工具调用(两 case) ───────────────────────────────────────

def _plan_call(pid="p1"):
    return Message(role="assistant", tool_calls=[ToolCallReq(id=pid, name="plan", arguments={"items": []})])


def _plan_result(pid="p1"):
    return Message(role="tool", tool_call_id=pid, name="plan", content="plan updated")


def test_exclude_plan_only_case():
    msgs = [Message(role="user", content="hi"), _plan_call("p1"), _plan_result("p1"),
            Message(role="assistant", content="ok")]
    out = exclude_plan_calls(msgs)
    assert not any(m.role == "assistant" and any(tc.name == "plan" for tc in m.tool_calls) for m in out)
    assert not any(m.role == "tool" and m.name == "plan" for m in out)
    assert any(m.role == "user" for m in out) and any(m.content == "ok" for m in out)
    # 视图变换:入参不变
    assert any(tc.name == "plan" for m in msgs if m.role == "assistant" for tc in m.tool_calls)


def test_exclude_plan_mixed_case():
    mixed = Message(role="assistant", tool_calls=[
        ToolCallReq(id="p1", name="plan", arguments={"items": []}),
        ToolCallReq(id="d1", name="device_status", arguments={"device": "3号楼"}),
    ])
    msgs = [Message(role="user", content="hi"), mixed, _plan_result("p1"),
            Message(role="tool", tool_call_id="d1", name="device_status", content="26℃")]
    out = exclude_plan_calls(msgs)
    asst = [m for m in out if m.role == "assistant"][0]
    assert [tc.name for tc in asst.tool_calls] == ["device_status"]   # plan 摘掉、别的留
    tool_ids = [m.tool_call_id for m in out if m.role == "tool"]
    assert "d1" in tool_ids and "p1" not in tool_ids                   # plan result 丢、别的留


def test_exclude_keeps_role_pairing_valid():
    """排除后过 repair 无孤儿(不留悬空 tool_call、不留孤儿 result)。"""
    msgs = [Message(role="user", content="hi"), _plan_call("p1"), _plan_result("p1"),
            Message(role="assistant", content="done")]
    out = exclude_plan_calls(msgs)
    assert repair_messages(out) == 0
