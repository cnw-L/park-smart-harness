import asyncio
from agent_loop.plan import PlanState, make_plan_tool, derive_plan
from agent_loop.tools import ToolContext
from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget
from agent_loop.messages import Message, ToolCallReq

def test_plan_tool_replaces_snapshot():
    state = PlanState()
    tool = make_plan_tool(state)
    ctx = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=9)), depth=0)
    asyncio.run(tool.handler({"items": [
        {"id": "1", "content": "查状态", "status": "doing"},
        {"id": "2", "content": "汇总", "status": "todo"}]}, ctx))
    assert [i.status for i in state.items] == ["doing", "todo"]
    assert state.render().startswith("当前计划")


def test_plan_item_carries_spec_faithfully():
    """§2.2 status + spec,结构化、保真不压缩;spec 拼回上下文(§2.1 任务层)。"""
    state = PlanState()
    tool = make_plan_tool(state)
    ctx = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=9)), depth=0)
    spec = {"capability": "device_ctrl",
            "grounded": {"deviceId": "d-3-ac", "pointTypeNo": "AC", "paramValue": 1}}
    asyncio.run(tool.handler({"items": [
        {"id": "1", "content": "开3号楼空调", "status": "todo", "spec": spec}]}, ctx))
    item = state.items[0]
    assert item.spec == spec                       # 保真:结构化、不压缩
    rendered = state.render()
    assert "device_ctrl" in rendered and "d-3-ac" in rendered   # spec 渲染进上下文


def test_plan_item_spec_optional():
    """向后兼容:无 spec 的 item 不报错,spec 为 None。"""
    state = PlanState()
    state.replace([{"id": "1", "content": "查状态", "status": "doing"}])
    assert state.items[0].spec is None
    # render 不应因缺 spec 报错或渲染空 spec 噪声
    assert "查状态" in state.render()


# ---------------------------------------------------------------------------
# derive_plan 单元测试（offline，无网络/Redis 依赖）
# ---------------------------------------------------------------------------

def test_derive_plan_empty_messages_returns_empty():
    """无任何 plan 工具调用 → derive_plan 返回空 PlanState。"""
    ps = derive_plan([])
    assert ps.items == []


def test_derive_plan_no_plan_calls_returns_empty():
    """消息中无 plan 工具调用（有其他 tool_call）→ 返回空 PlanState。"""
    msgs = [
        Message(role="user", content="帮我查状态"),
        Message(role="assistant", content="",
                tool_calls=[ToolCallReq(id="c1", name="get_status", arguments={"device_id": "d1"})]),
        Message(role="tool", content='{"ok": true}', tool_call_id="c1", name="get_status"),
    ]
    ps = derive_plan(msgs)
    assert ps.items == []


def test_derive_plan_single_plan_call_rebuilds_items():
    """单条 plan tool_call → derive_plan 重建 items（含 spec 保真）。"""
    spec = {"capability": "device_ctrl", "grounded": {"deviceId": "d-3-ac"}}
    plan_args = {
        "items": [
            {"id": "1", "content": "开空调", "status": "doing", "spec": spec},
            {"id": "2", "content": "汇报", "status": "todo"},
        ]
    }
    msgs = [
        Message(role="user", content="帮我开空调"),
        Message(role="assistant", content="",
                tool_calls=[ToolCallReq(id="p1", name="plan", arguments=plan_args)]),
        Message(role="tool", content="plan updated", tool_call_id="p1", name="plan"),
    ]
    ps = derive_plan(msgs)
    assert len(ps.items) == 2
    assert ps.items[0].id == "1"
    assert ps.items[0].content == "开空调"
    assert ps.items[0].status == "doing"
    assert ps.items[0].spec == spec   # spec 保真
    assert ps.items[1].id == "2"
    assert ps.items[1].spec is None


def test_derive_plan_multiple_plan_calls_takes_latest():
    """多次 plan 调用 → derive_plan 取最后一次（覆盖式），而非第一次或合并。"""
    first_plan = {
        "items": [{"id": "1", "content": "旧步骤", "status": "done"}]
    }
    latest_plan = {
        "items": [
            {"id": "2", "content": "新步骤A", "status": "doing"},
            {"id": "3", "content": "新步骤B", "status": "todo"},
        ]
    }
    msgs = [
        Message(role="user", content="开始"),
        Message(role="assistant", content="",
                tool_calls=[ToolCallReq(id="p1", name="plan", arguments=first_plan)]),
        Message(role="tool", content="plan updated", tool_call_id="p1", name="plan"),
        Message(role="assistant", content="",
                tool_calls=[ToolCallReq(id="p2", name="plan", arguments=latest_plan)]),
        Message(role="tool", content="plan updated", tool_call_id="p2", name="plan"),
    ]
    ps = derive_plan(msgs)
    assert len(ps.items) == 2
    assert ps.items[0].id == "2"
    assert ps.items[0].content == "新步骤A"
    assert ps.items[1].id == "3"


def test_derive_plan_skips_malformed_no_items_falls_back():
    """arguments 缺 items 的 plan 调用视为畸形，跳过；回退到更早的有效调用。"""
    valid_plan = {
        "items": [{"id": "v1", "content": "有效步骤", "status": "todo"}]
    }
    malformed_plan = {"note": "missing items field"}  # 故意缺 items
    msgs = [
        Message(role="user", content="hi"),
        Message(role="assistant", content="",
                tool_calls=[ToolCallReq(id="p1", name="plan", arguments=valid_plan)]),
        Message(role="tool", content="plan updated", tool_call_id="p1", name="plan"),
        # 后面的 plan 调用畸形（无 items）
        Message(role="assistant", content="",
                tool_calls=[ToolCallReq(id="p2", name="plan", arguments=malformed_plan)]),
        Message(role="tool", content="plan updated", tool_call_id="p2", name="plan"),
    ]
    ps = derive_plan(msgs)
    # 畸形调用被跳过，回退到更早的有效调用
    assert len(ps.items) == 1
    assert ps.items[0].id == "v1"


def test_derive_plan_ignores_tool_result_messages():
    """derive_plan 仅读 assistant tool_call arguments；tool 角色的 result 消息不被误读。"""
    plan_args = {
        "items": [{"id": "1", "content": "真实计划", "status": "doing"}]
    }
    msgs = [
        Message(role="user", content="开始"),
        Message(role="assistant", content="",
                tool_calls=[ToolCallReq(id="p1", name="plan", arguments=plan_args)]),
        # tool 结果消息：内容带"plan"字样，但不是 assistant tool_call
        Message(role="tool", content="plan updated", tool_call_id="p1", name="plan"),
    ]
    # 再追加一条 tool 消息，伪装成含 plan 数据（实际不该被读）
    fake_result = Message(role="tool", content='{"items":[{"id":"fake","content":"fake","status":"todo"}]}',
                          tool_call_id="x1", name="plan")
    ps = derive_plan(msgs + [fake_result])
    # 只有 assistant tool_call 那条被采纳，fake tool 消息被忽略
    assert len(ps.items) == 1
    assert ps.items[0].id == "1"
    assert ps.items[0].content == "真实计划"
