"""Phase 3:域叶子 + record_query 扁平工具 + facility 子 agent(首证跨界 handle 路径 R1)。"""
from __future__ import annotations

import asyncio

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget
from agent_loop.llm import ModelTurn
from agent_loop.messages import ToolCallReq
from agent_loop.tools import ToolContext

from agent_tools.backend import BackendError, FakeBackendClient
from agent_tools.catalog import ToolCatalog
from agent_tools.domains.facility import (FACILITY_LEAVES, build_facility_agent,
                                          facility_leaf_specs)
from agent_tools.domains.knowledge import make_knowledge_query_tool
from agent_tools.domains.life import (make_meeting_query_tool, make_parking_query_tool,
                                      make_restaurant_query_tool)
from agent_tools.domains.records import make_record_query_tool
from agent_tools.proposal import ProposalStore


def _facility(model_caller, store):
    """V2:叶子进 catalog → 子 registry 从 catalog 派生(gate=None,本测不验权限)。"""
    cat = ToolCatalog()
    for s in facility_leaf_specs(store=store):
        cat.register(s)
    return build_facility_agent(model_caller=model_caller,
                                leaf_registry=cat.to_registry(list(FACILITY_LEAVES)))


def _ctx():
    return ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=12)), depth=0)


# ── record_query facade ─────────────────────────────────────────────────────
def test_record_query_dispatches_by_kind():
    """对齐工单统计域:工单=总览(分布)、报修/告警/事件=类型工单(附示例)、巡检/维保=计数。"""
    tool = make_record_query_tool()                       # 默认 FakeBackendClient(罐装行)
    for kind, marker in [("工单", "工单总览"), ("报修", "处理中"), ("告警", "待处理"),
                         ("事件", "电梯异响"), ("巡检", "921"), ("维保", "214")]:
        r = asyncio.run(tool.handler({"kind": kind}, _ctx()))
        assert r.ok and marker in r.content, (kind, r.content)


def test_record_query_inspect_maintain_are_workorder_counts_not_ledger():
    """回归 bug:巡检/维保是工单类型计数(921/214),不是设备台账(旧 bug 返 1877 同一份)。"""
    r_in = asyncio.run(make_record_query_tool().handler({"kind": "巡检"}, _ctx()))
    r_mt = asyncio.run(make_record_query_tool().handler({"kind": "维保"}, _ctx()))
    assert "设备巡检工单" in r_in.content and "921" in r_in.content
    assert "设备维保工单" in r_mt.content and "214" in r_mt.content
    assert r_in.content != r_mt.content                   # 不再是同一份台账


def test_record_query_overview_has_type_distribution():
    """工单总览=权威总数 + 按类型分布(各类型真实工单数,非旧的报修单 231)。"""
    r = asyncio.run(make_record_query_tool().handler({"kind": "工单"}, _ctx()))
    assert r.ok and "工单总览" in r.content and "按类型" in r.content and "设备巡检工单 921" in r.content


def test_record_query_time_window_scopes_and_labels():
    """时间窗:可解析的 NL 时间(本月)→ 标窗口口径 + 缩量(非把累计当区间)。"""
    r = asyncio.run(make_record_query_tool().handler({"kind": "报修", "time": "本月"}, _ctx()))
    assert r.ok and "本月" in r.content and "累计" not in r.content   # 标窗口、不标累计


def test_record_query_unparseable_time_falls_back_honest():
    """时间解析不出 → 诚实降级:累计口径 + 明确未解析提示(不冒充区间)。"""
    r = asyncio.run(make_record_query_tool().handler(
        {"kind": "报修", "time": "去年第三个礼拜左右"}, _ctx()))
    assert r.ok and "累计" in r.content and "未能解析" in r.content


def test_record_query_exposes_status_distribution():
    """状态:返回按状态分布(待调度/处理中/已完成…)→ 支持"待处理/已完成"类问题。"""
    r = asyncio.run(make_record_query_tool().handler({"kind": "报修"}, _ctx()))
    assert r.ok and "按状态" in r.content and "待调度" in r.content and "已完成" in r.content


def test_record_query_flat_returns_kind_data():
    """v8:record_query 是**扁平工具**(非子 agent)——单次调用返回该 kind 计数/分布;
    多 kind 综合(工单+告警)由**主** plan 编排多次调用,不再绕子循环。"""
    r = asyncio.run(make_record_query_tool().handler({"kind": "工单"}, _ctx()))
    assert r.ok and "工单" in r.content


def test_record_query_unknown_kind_is_business_error():
    r = asyncio.run(make_record_query_tool().handler({"kind": "天气"}, _ctx()))
    assert r.ok is False and "unknown record kind" in (r.error or "")


def test_record_query_is_read_only():
    assert make_record_query_tool().is_control is False


# ── 生活服务扁平(后端无接口 → 保留演练数据,强标记声明是演示)──────────────────
def test_life_service_flat_tools():
    mr = asyncio.run(make_meeting_query_tool().handler({"time": "明天"}, _ctx()))
    assert mr.ok and "会议室" in mr.content and "演示数据" in mr.content   # 无接口工具保留演练数据
    assert "车位" in asyncio.run(make_parking_query_tool().handler({}, _ctx())).content
    rr = asyncio.run(make_restaurant_query_tool().handler({}, _ctx()))
    assert rr.ok and "餐厅" in rr.content


# ── 设备管理叶子:device_health / energy(调 backend + 格式化 + 错误路径)─────────
def _facility_leaves(backend=None):
    return {s.tool.name: s.tool for s in facility_leaf_specs(backend=backend, store=ProposalStore())}


def test_facility_health_energy_leaves_format_backend_data():
    leaves = _facility_leaves()                            # 默认 FakeBackendClient(罐装健康/能耗)
    hr = asyncio.run(leaves["device_health"].handler({"system_no": "kt"}, _ctx()))
    assert hr.ok and "故障" in hr.content and "可靠率" in hr.content and "优秀" in hr.content
    er = asyncio.run(leaves["energy_query"].handler({}, _ctx()))
    assert er.ok and "电" in er.content and "水" in er.content


def test_facility_leaf_backend_error_is_ok_false_not_fabricated():
    class _Boom(FakeBackendClient):
        async def device_health(self, *, system_no=None, token=None):
            raise BackendError("健康服务挂了")
    r = asyncio.run(_facility_leaves(_Boom())["device_health"].handler({}, _ctx()))
    assert r.ok is False and "失败" in (r.error or "")     # 错误如实回、不臆造


# ── facility 子 agent:跨界 handle 路径(R1) ──────────────────────────────────
class _RelayModel:
    """脚本工具轮 + 末轮把最后一条 tool 结果当 content 回(模拟模型读结果再回报 handle)。"""
    def __init__(self, tool_turns):
        self._turns = list(tool_turns); self._i = 0

    async def __call__(self, config, messages, tool_schemas):
        if self._i < len(self._turns):
            t = self._turns[self._i]; self._i += 1; return t
        last_tool = next((m for m in reversed(messages) if m.role == "tool"), None)
        return ModelTurn(content=(last_tool.content if last_tool else "完成"), tool_calls=[])


def test_facility_agent_proposes_into_shared_store_without_leaking_handle():
    store = ProposalStore()
    facility = _facility(_RelayModel([
        ModelTurn(content="", tool_calls=[ToolCallReq(
            id="d1", name="device_status", arguments={"device": "3号楼空调"})]),
        ModelTurn(content="", tool_calls=[ToolCallReq(
            id="p1", name="propose_control",
            arguments={"target": "3号楼空调", "point_type_id": "3700", "point_type_no": "KTJZ",
                       "device_id": "30302", "param": "温度设定", "value": "24"})]),
    ]), store)

    res = asyncio.run(facility.handler({"task": "查3号楼空调温度,太热就提案调到24度"}, _ctx()))
    assert res.ok
    # 跨界证据①:子里的 propose_control 写进了**共享** store
    assert len(store._store) == 1
    prop = next(iter(store._store.values()))
    assert prop.action == "deviceCtrl" and prop.params.get("paramValue") == "24"  # grounded
    assert prop.reversibility == "可逆"
    # 跨界证据②(包1 后改写):子回报报告"已登记提案",但**不再泄露 handle**——
    # handle 不经模型,主控用 execute_proposal 取最近一条;共享 store(证据①)才是真值源。
    assert "提案已登记" in res.content and "execute_proposal" in res.content
    assert prop.handle not in res.content                  # 关键:handle 不进模型可见文本
