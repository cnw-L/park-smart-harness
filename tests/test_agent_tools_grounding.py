"""P4:grounding 闸 —— ground_control(isCtrl/范围/枚举/可逆性,不可逆当场拒)+ propose_control。"""
from __future__ import annotations

import asyncio

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget
from agent_loop.tools import ToolContext

from agent_tools.backend import BackendError, DeviceHit, FakeBackendClient
from agent_tools.grounding import Grounded, Intent, Rejection, ground_control
from agent_tools.propose import make_propose_control_tool
from agent_tools.proposal import ProposalStore


def _be():
    return FakeBackendClient()      # 默认:温度设定(数值16-30)+开关(枚举)+只读量(不可控)


def _intent(**kw):
    base = dict(point_type_id="3700", point_type_no="KTJZ", device_id="1001",  # 数字 id(真实 deviceId 是数字)
                param="温度设定", value="24")
    base.update(kw)
    return Intent(**base)


def _g(intent, **kw):
    return asyncio.run(ground_control(intent, backend=_be(), **kw))


# ── ground_control ────────────────────────────────────────────────────────────
def test_numeric_in_range_grounds_reversible():
    g = _g(_intent(value="24"))
    assert isinstance(g, Grounded) and g.reversibility == "可逆"
    assert g.param_value == "24" and g.param_type_no == "WD" and g.device_id == "1001"


def test_numeric_out_of_range_rejected():
    r = _g(_intent(value="80"))
    assert isinstance(r, Rejection) and r.code == "out_of_range"


def test_non_numeric_device_id_rejected():
    """deviceId 必须数字(payload 转 int)→ 非数字当场拒,不静默产出缺 deviceId 的残缺 payload。"""
    r = _g(_intent(device_id="abc"))
    assert isinstance(r, Rejection) and r.code == "bad_device_id"


def test_enum_match_resolves_paramvalue():
    g = _g(_intent(param="开关", value="开"))
    assert isinstance(g, Grounded) and g.param_value == "1" and g.param_status == "开"


def test_enum_no_match_rejected():
    r = _g(_intent(param="开关", value="半开"))
    assert isinstance(r, Rejection) and r.code == "value_not_in_enum"


def test_pure_trigger_no_enum_no_range_is_ungroundable():
    """V6 真机结构信号:可控但无枚举无范围(纯触发,如门禁脉冲)→ 解析不出绝对值 → 拒(fail-safe)。
    实测可控全集(暖通)无此类,纯防御:门禁若纳入即在此被结构性拦下,不靠手工 denylist。"""
    from agent_tools.backend import FakeBackendClient, ParamType
    be = FakeBackendClient(param_types=[
        ParamType(param_type_no="PULSE", param_type_name="开闸脉冲", is_ctrl=True,
                  input_type="button")])   # is_ctrl 但无 paramStatuses、无 min/max
    r = asyncio.run(ground_control(_intent(param="开闸脉冲", value="1"), backend=be))
    assert isinstance(r, Rejection) and r.code == "ungroundable"


def test_not_controllable_rejected():
    r = _g(_intent(param="只读量", value="1"))
    assert isinstance(r, Rejection) and r.code == "not_controllable"


def test_match_prefers_controllable_param_over_readonly_namesake():
    """真机回归:同设备只读「送风温度」与可控「温度控制」并存,关键词「温度」须取可控项(否则误判不可控)。"""
    from agent_tools.backend import FakeBackendClient, ParamType
    be = FakeBackendClient(param_types=[
        ParamType(param_type_no="sendTem", param_type_name="送风温度", is_ctrl=False),  # 只读,排在前
        ParamType(param_type_no="temControl", param_type_name="温度控制", is_ctrl=True,
                  min_value="18", max_value="30")])
    g = asyncio.run(ground_control(_intent(param="温度", value="24"), backend=be))
    assert isinstance(g, Grounded) and g.param_type_no == "temControl" and g.param_value == "24"


def test_param_not_found_and_no_point_type():
    assert _g(_intent(param="不存在的参数")).code == "param_not_found"
    assert _g(_intent(point_type_id="")).code == "no_point_type"


def test_irreversible_in_map_rejected_no_idem():
    """★安全降级:非状态型(denylist)+ 后端无幂等 → 当场拒。"""
    r = _g(_intent(value="24"), reversibility_map={"WD": "不可逆"})
    assert isinstance(r, Rejection) and r.code == "irreversible_no_idem"


def test_irreversible_passes_only_with_backend_idempotency():
    g = _g(_intent(value="24"), reversibility_map={"WD": "不可逆"}, backend_has_idempotency=True)
    assert isinstance(g, Grounded) and g.reversibility == "不可逆"


# ── propose_control(= grounding 闸落点) ──────────────────────────────────────
def _ctx():
    return ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=5)), depth=0)


def test_propose_control_is_read_only_and_grounds():
    store = ProposalStore()
    tool = make_propose_control_tool(store, _be())
    assert tool.is_control is False                         # grounding 只读 → 可进子 agent
    res = asyncio.run(tool.handler(
        {"point_type_id": "3700", "point_type_no": "KTJZ", "device_id": "1001",
         "param": "温度设定", "value": "24", "target": "3号楼空调"}, _ctx()))
    assert res.ok and "提案已登记" in res.content
    assert next(iter(store._store)) not in res.content     # handle 不进模型可见文本(execute 取最近一条)
    assert len(store._store) == 1
    p = next(iter(store._store.values()))
    assert p.action == "deviceCtrl" and p.reversibility == "可逆"
    # ★完整 DeviceControlEvent:deviceId 转 int + deviceIds 数组
    assert p.params.get("paramValue") == "24" and p.params.get("deviceId") == 1001
    assert p.params.get("deviceIds") == [1001]
    assert p.params.get("paramStatus") == "24"             # ★模拟量:paramStatus 也填目标值(否则后端 param_exception)
    assert p.params.get("paramTypeNo") == "WD"             # 解析自字典,非模型编


def test_propose_control_rejection_writes_nothing():
    store = ProposalStore()
    res = asyncio.run(make_propose_control_tool(store, _be()).handler(
        {"point_type_id": "3700", "param": "温度设定", "value": "80"}, _ctx()))    # 越界
    assert res.ok is False and "被拒" in (res.error or "")
    assert len(store._store) == 0                          # 拒 → 不写 store


class _AuthFailBackend(FakeBackendClient):
    async def device_status(self, *, name=None, region=None, token=None):
        raise BackendError("认证失败,无法访问系统资源", code="backend_code")


def test_propose_by_name_auth_failure_is_not_blamed_on_device_name():
    """真机回归:token 失效 → device_status 抛 BackendError。错误必须如实说是**系统/认证**问题,
    **不能**说成"设备名解析失败"(否则模型让用户反复换设备名,换名也没用)。"""
    store = ProposalStore()
    res = asyncio.run(make_propose_control_tool(store, _AuthFailBackend()).handler(
        {"device": "空调机组101", "param": "温度", "value": "24"}, _ctx()))
    assert res.ok is False
    err = res.error or ""
    assert "认证" in err or "token" in err.lower()          # 如实暴露认证/系统因
    assert "不是设备名问题" in err and "不要让用户改用更精确的设备名" in err
    assert len(store._store) == 0


def test_propose_by_name_ambiguous_multiple_matches_blocks():
    """★控制歧义硬闸:用户给类别名(空调机组)匹配到多台 → **拒绝、不替用户选第一台**,
    让模型回去问用户具体哪台。控错设备是事故。"""
    store = ProposalStore()
    backend = FakeBackendClient(device_hits=[
        DeviceHit(device_id="d106", name="空调机组106", status="在线", value="1",
                  point_type_id="3700", point_type_no="KTJZ", point_id="p1"),
        DeviceHit(device_id="d101", name="空调机组101", status="在线", value="1",
                  point_type_id="3700", point_type_no="KTJZ", point_id="p2"),
    ])
    res = asyncio.run(make_propose_control_tool(store, backend).handler(
        {"device": "空调机组", "param": "温度", "value": "24"}, _ctx()))
    assert res.ok is False
    err = res.error or ""
    assert "匹配到 2 台" in err                              # 数量
    assert "空调机组106" in err and "空调机组101" in err    # ★完整候选列给用户(不只是"例如…")
    assert "怎么回复" in err and "设备编号" in err           # ★明确告诉用户怎么回复
    assert len(store._store) == 0                          # 歧义 → 不登记任何提案


def test_propose_by_exact_name_among_multiple_proceeds():
    """精确全名命中唯一(空调机组106 在 [106,101] 里精确匹配)→ 放行,不算歧义。"""
    store = ProposalStore()
    backend = FakeBackendClient(device_hits=[
        DeviceHit(device_id="106", name="空调机组106", status="在线", value="1",
                  point_type_id="3700", point_type_no="KTJZ", point_id="p1",
                  readings=[("WD", "温度设定", "26")]),
        DeviceHit(device_id="101", name="空调机组101", status="在线", value="1",
                  point_type_id="3700", point_type_no="KTJZ", point_id="p2"),
    ])
    res = asyncio.run(make_propose_control_tool(store, backend).handler(
        {"device": "空调机组106", "param": "温度设定", "value": "24"}, _ctx()))
    assert res.ok and "提案已登记" in res.content           # 唯一精确匹配 → 正常登记
    p = next(iter(store._store.values()))
    assert p.params.get("deviceId") == 106                  # 用的是 106 那台(int)
    assert p.params.get("paramSubId") == "sub-wd" and p.params.get("paramType") == "1"  # 设备级字段流入


def test_propose_by_name_not_found_asks_for_name():
    """后端正常但确实查无此设备 → 这才是真正的"名字问题",可请用户给准确名。"""
    store = ProposalStore()
    res = asyncio.run(make_propose_control_tool(store, FakeBackendClient(device_hits=[])).handler(
        {"device": "并不存在的设备", "param": "温度", "value": "24"}, _ctx()))
    assert res.ok is False and "未找到" in (res.error or "")
    assert len(store._store) == 0
