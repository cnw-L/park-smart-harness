import asyncio
from agent_loop.loop import run_loop
from agent_loop.dispatch import ToolExecOutcome
from agent_loop.config import LoopConfig, LoopBudget
from agent_loop.conversation import Conversation, InMemoryConversationStore
from agent_loop.tools import LoopToolRegistry, LoopTool, ToolResult
from agent_loop.budget import BudgetTracker
from agent_loop.stubs import echo_tool
from agent_loop.llm import ModelTurn, FakeModelCaller
from agent_loop.messages import Message, ToolCallReq


def _cfg(max_iter=5, max_fail=3):
    return LoopConfig(model="m", max_tokens=100, temperature=0.0, role="main",
                      toolset=["echo"], budget=LoopBudget(max_iterations=max_iter, max_tool_failures=max_fail))


def test_loop_delegates_to_injected_subsystems_and_persists():
    calls = {"assemble": 0, "execute": 0}

    class SpyAssembler:
        def assemble(self, config, conversation):
            calls["assemble"] += 1
            return [Message(role="system", content="sys"), *conversation.messages]

    class SpyExecutor:
        async def execute_one(self, call, registry, ctx):
            calls["execute"] += 1
            r = await registry.get(call.name).handler(call.arguments, ctx)
            return ToolExecOutcome(
                disposition="executed",
                message=Message(role="tool", content=r.content, tool_call_id=call.id, name=call.name),
                ok=r.ok)

        async def execute(self, tcalls, registry, ctx):
            outs = []
            for c in tcalls:
                outs.append(await self.execute_one(c, registry, ctx))
            return outs

    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="先查", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "hi"})]),
        ModelTurn(content="完成", tool_calls=[])])
    conv = Conversation(thread_id="t"); conv.append(Message(role="user", content="开始"))
    cfg = _cfg(); budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()
    res = asyncio.run(run_loop(cfg, conv, reg, budget, fake,
                               assembler=SpyAssembler(), executor=SpyExecutor(), store=store))
    assert res.status == "completed"
    assert calls["assemble"] == 2 and calls["execute"] == 1   # 都走了注入的子系统
    persisted = asyncio.run(store.load("t"))
    assert len(conv.messages) == 4              # seed user + assistant + tool + assistant
    assert len(persisted.messages) == 3         # 持久化子系统收到引擎 append 的 3 条(seed 由调用方负责)


def test_failures_reset_on_success():
    def boom():
        async def h(a, c):
            return ToolResult(ok=False, content="", error="x")
        return LoopTool(name="boom", description="", parameters={"type": "object", "properties": {}}, handler=h)

    reg = LoopToolRegistry(); reg.register(boom()); reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="1", name="boom", arguments={})]),
        ModelTurn(content="", tool_calls=[ToolCallReq(id="2", name="echo", arguments={"text": "ok"})]),
        ModelTurn(content="", tool_calls=[ToolCallReq(id="3", name="boom", arguments={})]),
        ModelTurn(content="done", tool_calls=[])])
    cfg = LoopConfig(model="m", max_tokens=100, temperature=0.0, role="main",
                     toolset=["boom", "echo"], budget=LoopBudget(max_iterations=9, max_tool_failures=2))
    conv = Conversation(thread_id="t2"); conv.append(Message(role="user", content="开始"))
    budget = BudgetTracker(cfg.budget)
    res = asyncio.run(run_loop(cfg, conv, reg, budget, fake, store=InMemoryConversationStore()))
    # 两次失败但非连续(中间有成功),不应触发 max_tool_failures=2 的停机
    assert res.status == "completed" and res.final == "done"


def test_reasoning_passes_into_assistant_message():
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([ModelTurn(content="答案", reasoning="想了想", tool_calls=[])])
    conv = Conversation(thread_id="r"); conv.append(Message(role="user", content="问"))
    cfg = _cfg(); budget = BudgetTracker(cfg.budget)
    res = asyncio.run(run_loop(cfg, conv, reg, budget, fake, store=InMemoryConversationStore()))
    # 隐=thought 存进 assistant.reasoning,与 content 分开(Hermes 同款)
    assert any(m.role == "assistant" and m.reasoning == "想了想" for m in conv.messages)
