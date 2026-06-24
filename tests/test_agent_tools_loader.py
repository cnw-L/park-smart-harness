"""V4:ToolLoader —— 按有效能力集过滤顶层 toolset(可见性,减选择 + 第一道安全)。"""
from __future__ import annotations

from agent_loop.llm import FakeModelCaller

from agent_tools.composition import TOP_TOOLS, build_tool_subsystem
from agent_tools.loader import select_toolset


def test_full_permissions_load_all_top():
    sub = build_tool_subsystem(model_caller=FakeModelCaller([]))
    perms = ("device:read", "device:control", "record:read", "life:read", "knowledge:read")
    assert set(select_toolset(sub.catalog, sub.toolset, perms)) == set(TOP_TOOLS)


def test_missing_control_drops_execute_proposal():
    """无 device:control → execute_proposal 不加载(看不见 → 减选择 + 第一道安全)。"""
    sub = build_tool_subsystem(model_caller=FakeModelCaller([]))
    loaded = select_toolset(sub.catalog, sub.toolset,
                            ("device:read", "record:read", "life:read", "knowledge:read"))
    assert "execute_proposal" not in loaded and "facility_agent" in loaded


def test_only_knowledge_loads_one():
    sub = build_tool_subsystem(model_caller=FakeModelCaller([]))
    assert select_toolset(sub.catalog, sub.toolset, ("knowledge:read",)) == ["knowledge_query"]


def test_anonymous_loads_nothing():
    sub = build_tool_subsystem(model_caller=FakeModelCaller([]))
    assert select_toolset(sub.catalog, sub.toolset, ()) == []


def test_pure_leaves_not_in_top_toolset():
    """纯 facility 叶子(device_status/energy_query/device_health)不在顶层 toolset;
    但 propose_control 多归属、record_query 已扁平化——都升顶层。"""
    sub = build_tool_subsystem(model_caller=FakeModelCaller([]))
    assert "device_status" not in sub.toolset and "device_health" not in sub.toolset
    assert "propose_control" in sub.toolset and "record_query" in sub.toolset   # 升顶层
