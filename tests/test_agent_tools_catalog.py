"""V1:治理注册表 + 极瘦元数据(ToolSpec=capability_code ⊥ is_control / ToolCatalog 扁平含叶子)。"""
from __future__ import annotations

from agent_loop.llm import FakeModelCaller
from agent_loop.tools import LoopTool

from agent_tools.catalog import ToolCatalog, ToolSpec
from agent_tools.composition import build_tool_subsystem


def _tool(name: str, is_control: bool = False) -> LoopTool:
    async def h(args, ctx):  # pragma: no cover - not invoked here
        ...
    return LoopTool(name=name, description="d",
                    parameters={"type": "object", "properties": {}}, handler=h,
                    is_control=is_control)


def test_toolspec_carries_capability_code():
    s = ToolSpec(tool=_tool("x"), capability_code="device:read")
    assert s.name == "x" and s.capability_code == "device:read" and s.is_control is False


def test_capability_code_orthogonal_to_is_control():
    """两轴正交:propose 形态(非控制工具)也可要控制权限码。"""
    s = ToolSpec(tool=_tool("propose", is_control=False), capability_code="device:control")
    assert s.is_control is False and s.capability_code == "device:control"
    s2 = ToolSpec(tool=_tool("exec", is_control=True), capability_code="device:control")
    assert s2.is_control is True                        # is_control 以引擎契约为准


def test_catalog_register_query_and_to_registry():
    cat = ToolCatalog()
    cat.register(ToolSpec(tool=_tool("a"), capability_code="device:read"))
    cat.register(ToolSpec(tool=_tool("b", is_control=True), capability_code="device:control"))
    assert set(cat.names()) == {"a", "b"}
    assert cat.find("a").capability_code == "device:read"
    assert cat.find("zzz") is None                      # 未登记 → None(gate 据此 deny)
    reg = cat.to_registry()
    assert reg.get("a").name == "a" and reg.get("b").name == "b"
    sub = cat.to_registry(["a"])
    assert "a" in sub._tools and "b" not in sub._tools


def test_subsystem_catalog_includes_leaves_with_codes():
    """扁平 catalog:顶层 7 + facility 叶子(统一治理);capability_code 正确。"""
    sub = build_tool_subsystem(model_caller=FakeModelCaller([]))
    # 顶层
    assert sub.catalog.find("facility_agent").capability_code == "device:read"
    assert sub.catalog.find("execute_proposal").capability_code == "device:control"
    assert sub.catalog.find("execute_proposal").is_control is True
    # 叶子也在同一 catalog
    assert sub.catalog.find("device_status").capability_code == "device:read"
    assert sub.catalog.find("propose_control").capability_code == "device:control"   # 控制流起点
    assert sub.catalog.find("propose_control").is_control is False                    # 不弹确认(正交)
    # 顶层 toolset = 8(propose_control 多归属升顶层;device_status 仍只是叶子)
    assert len(sub.toolset) == 8 and "device_status" not in sub.toolset
    assert "propose_control" in sub.toolset                       # 多归属:既叶子又顶层
    assert len(sub.registry.schemas(sub.toolset)) == 8
