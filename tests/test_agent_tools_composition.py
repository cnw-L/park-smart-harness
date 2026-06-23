"""Phase 4:组合根 —— 7 顶层入口 + 共享 store 单例 + gate 裁决。"""
from __future__ import annotations

import asyncio

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget
from agent_loop.gate import DefaultGate
from agent_loop.llm import FakeModelCaller, ModelTurn
from agent_loop.messages import ToolCallReq
from agent_loop.tools import ToolContext
from agent_context.principal import Principal

from agent_tools.composition import build_tool_subsystem

# 子 loop 现在受同一 CatalogGate(deny-first)→ 调叶子需带权限的 principal(device:read+control)。
_ADMIN = Principal(id="u", name="x", role="管理员",
                   permissions=("device:read", "device:control", "record:read",
                                "life:read", "knowledge:read"))


def _ctx(principal=_ADMIN):
    return ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=12)), depth=0,
                       principal=principal)


def test_top_level_is_eight_entries():
    sub = build_tool_subsystem(model_caller=FakeModelCaller([]))
    schemas = sub.registry.schemas(sub.toolset)
    assert len(schemas) == 8                                   # 7 域 + propose_control 多归属升顶层
    names = {s["function"]["name"] for s in schemas}
    assert {"facility_agent", "records_agent", "propose_control", "execute_proposal"} <= names


def test_control_shares_the_singleton_store():
    """父侧 control 与组合根 store 是同一对象(handle 跨界还原的桥)。"""
    sub = build_tool_subsystem(model_caller=FakeModelCaller([]))
    assert sub.control._store is sub.store


def test_gate_verdicts():
    sub = build_tool_subsystem(model_caller=FakeModelCaller([]))
    gate = DefaultGate()
    reg = sub.registry

    def verdict(name):
        return gate.classify(ToolCallReq(id="x", name=name, arguments={}), reg.get(name), _ctx())

    assert verdict("execute_proposal") == "ask"               # 控制 → 确认
    assert verdict("facility_agent") == "allow"
    assert verdict("record_query") == "allow"
    assert verdict("knowledge_query") == "allow"


def test_facility_proposal_resolvable_by_parent_control():
    """端到端(组合层):facility 子里 propose → 父侧 control 凭 handle 还原同一精确动作。"""
    class _Relay:
        def __init__(self, turns): self._t = list(turns); self._i = 0
        async def __call__(self, config, messages, schemas):
            if self._i < len(self._t):
                t = self._t[self._i]; self._i += 1; return t
            last = next((m for m in reversed(messages) if m.role == "tool"), None)
            return ModelTurn(content=(last.content if last else "done"), tool_calls=[])

    sub = build_tool_subsystem(model_caller=_Relay([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="p1", name="propose_control",
            arguments={"target": "3号楼空调", "point_type_id": "3700", "device_id": "ac-3f-2",
                       "param": "温度设定", "value": "24"})]),
    ]))
    facility = sub.registry.get("facility_agent")
    asyncio.run(facility.handler({"task": "提案把3号楼空调调到24度"}, _ctx()))
    # 父侧 control 凭 store 里的 handle freeze → 拿到提案的精确(grounded)动作
    handle = next(iter(sub.store._store))
    pending = sub.control.freeze(ToolCallReq(id="e1", name="execute_proposal",
                                             arguments={"handle": handle}))
    assert pending.frozen_action["name"] == "deviceCtrl"
    assert pending.frozen_action["arguments"].get("paramValue") == "24"     # 解析自字典
