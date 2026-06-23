"""完成判定:**模型给出文本答案(无工具调用 + 有正文)= 任务结束**,无论 plan 是否完成。

最简单也最稳(OpenAI/Anthropic 原生:停止调工具即结束);plan 是模型记账、不是完成权威。
空响应(无工具 + 无正文)→ 回滚重试;max_iterations 是真安全网。
"""
from __future__ import annotations

import asyncio

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.conversation import Conversation, InMemoryConversationStore
from agent_loop.llm import FakeModelCaller, ModelTurn
from agent_loop.loop import run_loop
from agent_loop.messages import Message, ToolCallReq
from agent_loop.plan import make_plan_tool
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolContext, ToolResult


def _status_tool() -> LoopTool:
    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        return ToolResult(ok=True, content="设备运行中(桩)")
    return LoopTool(name="device_status", description="查状态",
                    parameters={"type": "object", "properties": {}}, handler=handler)


def _plan_only(pid: str):
    return ModelTurn(content="", tool_calls=[ToolCallReq(
        id=pid, name="plan", arguments={"items": [{"id": "1", "content": "查", "status": "todo"}]})])


def _cfg(toolset):
    return LoopConfig(model="x", max_tokens=100, temperature=0.0, role="main",
                      toolset=toolset, budget=LoopBudget(max_iterations=8))


def _run(conv, reg, model):
    return asyncio.run(run_loop(
        _cfg(list(reg._tools.keys())), conv, reg, BudgetTracker(LoopBudget(max_iterations=8)),
        model, store=InMemoryConversationStore()))


def test_text_answer_completes():
    """无工具 + 有正文 → completed,final=正文。"""
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="做点事"))
    model = FakeModelCaller([ModelTurn(content="答案在此。", tool_calls=[])])
    res = _run(conv, LoopToolRegistry(), model)
    assert res.status == "completed" and res.final == "答案在此。"


def test_text_answer_completes_even_if_plan_unfinished():
    """关键:plan 还有 todo,但模型给了文本答案 → 照样结束(plan 不是完成权威)。"""
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="查并汇总"))
    reg = LoopToolRegistry()
    reg.register(make_plan_tool(conv.plan))
    model = FakeModelCaller([
        # 轮0:列 plan(2、3 还 todo)
        ModelTurn(content="开始", tool_calls=[ToolCallReq(id="p1", name="plan", arguments={"items": [
            {"id": "1", "content": "查", "status": "done"},
            {"id": "2", "content": "调", "status": "todo"},
            {"id": "3", "content": "汇总", "status": "todo"}]})]),
        # 轮1:直接给文本答案(plan 没全 done)
        ModelTurn(content="就到这,结论是一切正常。", tool_calls=[]),
    ])
    res = _run(conv, reg, model)
    assert res.status == "completed"
    assert res.final == "就到这,结论是一切正常。"     # plan 未完成也结束


def test_plan_only_spin_nudged_then_no_progress():
    """连续纯 plan-only(只改计划不执行)→ 先注入 nudge 怼回,仍不动手才以 no_progress 停。"""
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="办三步的事"))
    reg = LoopToolRegistry(); reg.register(make_plan_tool(conv.plan))
    seen: list = []

    class _Rec:
        async def __call__(self, config, messages, tool_schemas):
            seen.append(list(messages))
            return _plan_only(f"p{len(seen)}")

    res = _run(conv, reg, _Rec())
    assert res.status == "failed" and res.reason == "no_progress"
    # 空转后注入了动态 nudge(最后一次模型调用能看到怼回的 user 消息)
    assert any(m.role == "user" and "只更新了计划" in (m.content or "") for m in seen[-1])


def test_real_action_resets_no_progress_and_completes():
    """plan→真动作→plan→文本答案:真动作清零看门狗,交错不误停,正常 completed。"""
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="办事"))
    reg = LoopToolRegistry()
    reg.register(make_plan_tool(conv.plan)); reg.register(_status_tool())
    model = FakeModelCaller([
        _plan_only("p1"),                                                        # no_progress=1
        ModelTurn(content="", tool_calls=[ToolCallReq(id="d1", name="device_status", arguments={})]),  # 真动作→清零
        _plan_only("p2"),                                                        # no_progress=1(又一次,但没连超限)
        ModelTurn(content="完成,一切正常。", tool_calls=[]),                      # 文本答案→完成
    ])
    res = _run(conv, reg, model)
    assert res.status == "completed" and "正常" in res.final


def test_empty_response_does_not_complete():
    """无工具 + 无正文(空响应)→ 不算完成,回滚重试(最终 empty_response 失败)。"""
    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="做点事"))
    model = FakeModelCaller([ModelTurn(content="", tool_calls=[]) for _ in range(5)])
    res = _run(conv, LoopToolRegistry(), model)
    assert res.status == "failed" and res.reason == "empty_response"
