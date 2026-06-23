import asyncio
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolContext, OutputBudget
from agent_loop.stubs import echo_tool, add_tool
from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget

def _ctx():
    return ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=9)), depth=0)

def test_registry_only_exposes_toolset_schemas():
    reg = LoopToolRegistry()
    reg.register(echo_tool()); reg.register(add_tool())
    names = [s["function"]["name"] for s in reg.schemas(["echo"])]
    assert names == ["echo"]

def test_echo_and_add_handlers():
    reg = LoopToolRegistry(); reg.register(echo_tool()); reg.register(add_tool())
    r1 = asyncio.run(reg.get("echo").handler({"text": "hi"}, _ctx()))
    assert r1.ok and r1.content == "hi"
    r2 = asyncio.run(reg.get("add").handler({"a": 2, "b": 3}, _ctx()))
    assert r2.content == "5"

def test_output_budget_truncates():
    ob = OutputBudget(max_chars=4)
    assert ob.apply("123456") == "1234…"
