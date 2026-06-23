"""Task 0 — 身份脊柱 principal:经 Conversation → ToolContext → 工具 handler 透传。

身份在会话入口解析后 set 到 Conversation 上(不从日志加载),run_loop 构造 ToolContext
时透传给工具。这是记忆/知识/权限闸共用的同一身份;也是 rag-permission-not-wired 的修法。
"""
from __future__ import annotations

import asyncio

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.conversation import Conversation, InMemoryConversationStore
from agent_loop.llm import FakeModelCaller, ModelTurn
from agent_loop.loop import run_loop
from agent_loop.messages import Message, ToolCallReq
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolContext, ToolResult

from agent_context.principal import Principal


def _cfg(toolset: list[str]) -> LoopConfig:
    return LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=toolset,
        budget=LoopBudget(max_iterations=10, max_tool_failures=5),
    )


def _principal() -> Principal:
    return Principal(id="u1", name="张三", role="员工", dept="园区运维部",
                     koujing="内部,可列技术细节", token="tok-abc")


def test_principal_dataclass():
    p = _principal()
    assert p.name == "张三"
    assert p.role == "员工"
    assert p.token == "tok-abc"


def test_principal_threaded_to_tool():
    """principal set 到 Conversation 后,run_loop 透传给工具 handler 的 ctx.principal。"""
    seen: dict = {}

    async def capture(args: dict, ctx: ToolContext) -> ToolResult:
        seen["principal"] = ctx.principal
        return ToolResult(ok=True, content="ok")

    tool = LoopTool(name="cap", description="cap",
                    parameters={"type": "object", "properties": {}}, handler=capture)
    reg = LoopToolRegistry()
    reg.register(tool)

    conv = Conversation(thread_id="t")
    conv.append(Message(role="user", content="hi"))
    p = _principal()
    conv.principal = p   # 调用方在会话入口 set

    model = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="cap", arguments={})]),
        ModelTurn(content="done"),
    ])
    res = asyncio.run(run_loop(
        _cfg(["cap"]), conv, reg,
        BudgetTracker(LoopBudget(max_iterations=10)), model,
        store=InMemoryConversationStore(),
    ))
    assert res.status == "completed"
    assert seen["principal"] is p   # 同一身份对象透传到工具


def test_principal_default_none_ok():
    """缺省 principal=None 不崩(匿名/未登录)。"""
    conv = Conversation(thread_id="t")
    assert conv.principal is None
    ctx = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=1)), depth=0)
    assert ctx.principal is None
