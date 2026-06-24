"""P2:输出预算 enforce —— catalog 把 ToolSpec.output_budget 接进引擎 OutputBudget;读可截/控不截。"""
from __future__ import annotations

from agent_loop.llm import FakeModelCaller
from agent_loop.tools import LoopTool, OutputBudget

from agent_tools.catalog import ToolCatalog, ToolSpec
from agent_tools.composition import build_tool_subsystem


def _tool(name: str, is_control: bool = False) -> LoopTool:
    async def h(args, ctx):  # pragma: no cover
        ...
    return LoopTool(name=name, description="d",
                    parameters={"type": "object", "properties": {}}, handler=h,
                    is_control=is_control)


def test_read_spec_budget_wired_into_engine_tool():
    cat = ToolCatalog()
    cat.register(ToolSpec(tool=_tool("r"), capability_code="x:read", output_budget=500))
    t = cat.to_registry().get("r")
    assert isinstance(t.output_budget, OutputBudget) and t.output_budget.max_chars == 500
    # 截断生效(引擎 executor 认这个 seam)
    assert t.output_budget.apply("x" * 600).endswith("…") and len(t.output_budget.apply("x" * 600)) == 501


def test_control_spec_budget_skipped():
    """控制类不静默截:即便给了 output_budget 也不接进引擎。"""
    cat = ToolCatalog()
    cat.register(ToolSpec(tool=_tool("c", is_control=True), capability_code="x:control", output_budget=500))
    assert cat.to_registry().get("c").output_budget is None


def test_no_budget_means_no_truncation():
    cat = ToolCatalog()
    cat.register(ToolSpec(tool=_tool("r2"), capability_code="x:read"))      # 没给 budget
    assert cat.to_registry().get("r2").output_budget is None


def test_subsystem_reads_budgeted_control_not():
    sub = build_tool_subsystem(model_caller=FakeModelCaller([]))
    reg = sub.registry
    for name in ["facility_agent", "record_query", "meeting_query", "knowledge_query"]:
        assert isinstance(reg.get(name).output_budget, OutputBudget), name
    assert reg.get("execute_proposal").output_budget is None       # 控不截
