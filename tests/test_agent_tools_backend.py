"""真后端接入:ProdApiBackendClient(请求构造/解析 用 MockTransport 确定性验,无需 token)+
gated live(真 prod-api,需 token)。grounding=后端接口情况与使用指南.md getDevicePage。"""
from __future__ import annotations

import asyncio
import json
import os

import httpx
import pytest

from agent_tools.backend import (BackendError, FakeBackendClient, ProdApiBackendClient)


def test_fake_backend_device_status():
    hits = asyncio.run(FakeBackendClient().device_status(name="3号楼空调"))
    assert hits and hits[0].value and hits[0].point_type_no


def test_prodapi_device_status_falls_back_across_systems():
    """未映射类型(如充电桩默认落 kt 查空)→ 跨其它已配系统回退,直到命中。"""
    seen: list = []

    def handler(req: httpx.Request) -> httpx.Response:
        sysno = json.loads(req.content)["data"]["systemNo"]
        seen.append(sysno)
        if sysno == "tc":                                       # 仅 tc 有充电桩
            return httpx.Response(200, json={"code": 0, "data": {"list": [
                {"deviceId": 9, "deviceName": "充电桩001", "status": "在线"}]}})
        return httpx.Response(200, json={"code": 0, "data": {"list": []}})

    c = ProdApiBackendClient(base_url="http://x/prod-api/project", bearer_token="t")
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    hits = asyncio.run(c.device_status(name="XYZ001"))          # 无任何映射关键词 → 默认 kt 空 → 回退
    assert len(hits) == 1 and hits[0].name == "充电桩001"
    assert seen[0] == "kt" and "tc" in seen                     # 先默认、后回退扫到 tc


def test_prodapi_device_status_no_fallback_when_primary_hits():
    """首选系统命中即返,不做多余回退扫描。"""
    seen: list = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(json.loads(req.content)["data"]["systemNo"])
        return httpx.Response(200, json={"code": 0, "data": {"list": [
            {"deviceId": 1, "deviceName": "空调机组106", "status": "在线"}]}})

    c = ProdApiBackendClient(base_url="http://x/prod-api/project", bearer_token="t",
                             system_by_type={"空调": "kt", "停车": "tc"})
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    asyncio.run(c.device_status(name="空调机组106"))
    assert seen == ["kt"]                                       # 只查一次,无回退


def test_prodapi_builds_getdevicepage_request_and_parses():
    """确定性:断言 URL/body/Authorization + 解析 list → DeviceHit。无网络、无 token。"""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"code": 0, "data": {"list": [{
            "deviceId": 123, "deviceName": "3号楼空调", "status": "在线", "value": "26.0",
            "pointTypeNo": "KTJZ", "pointTypeName": "空调机组", "regionName": "3号楼"}]}})

    client = ProdApiBackendClient(base_url="http://x/prod-api/project", bearer_token="svc")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    hits = asyncio.run(client.device_status(name="空调", token="utok"))

    assert captured["url"].endswith("/common/device/getDevicePage")     # 指南§三.1 端点
    assert captured["body"] == {"pageNum": 1, "pageSize": 10,            # systemNo 必带(否则后端拒)
                                "data": {"systemNo": "kt", "deviceName": "空调"}}
    assert captured["auth"] == "Bearer utok"                            # 按用户 token(身份脊柱透传)
    assert len(hits) == 1
    h = hits[0]
    assert h.device_id == "123" and h.name == "3号楼空调" and h.value == "26.0"
    assert h.point_type_no == "KTJZ" and h.region == "3号楼"


def test_prodapi_backend_code_error_raises():
    def handler(request):
        return httpx.Response(200, json={"code": 401, "msg": "认证失败"})
    client = ProdApiBackendClient(base_url="http://x/prod-api/project")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(BackendError):
        asyncio.run(client.device_status(name="空调"))


_ORDER_CATALOG = {"code": 0, "data": {"count": 4695, "workOrderTypeCountVOS": [
    {"orderType": "repair", "orderTypeStr": "物业报修工单", "count": 276},
    {"orderType": "alarm", "orderTypeStr": "设备告警工单", "count": 2152},
    {"orderType": "inspect", "orderTypeStr": "设备巡检工单", "count": 921},
    {"orderType": "maintenance", "orderTypeStr": "设备维保工单", "count": 214},
    {"orderType": "event", "orderTypeStr": "事件上报工单", "count": 54},
]}}


def test_prodapi_records_aligns_to_workorder_statistics():
    """对齐工单统计域:计数来自 getOrderTypeStatistics;报修/告警/事件再附具体列表(计数仍用工单统计)。"""
    seen: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        seen.append(path)
        if path.endswith("/workOrder/statistics/getOrderTypeStatistics"):
            return httpx.Response(200, json=_ORDER_CATALOG)
        if path.endswith("/workOrder/statistics/getOrderStatusStatistics"):
            return httpx.Response(200, json={"code": 0, "data": {"count": 276, "workOrderStatusVOS": [
                {"orderStatus": "1", "orderStatusStr": "待调度", "count": 109},
                {"orderStatus": "6", "orderStatusStr": "已完成", "count": 52}]}})
        if path.endswith("/pro/proRepairApply/page"):
            return httpx.Response(200, json={"code": 0, "data": {"total": 231, "list": [
                {"repairContent": "空调不制冷", "repairNo": "WX1", "orderTypeStr": "报修",
                 "repairStatusStr": "处理中", "regionStr": "2号楼", "createTime": "2026-06-18"}]}})
        if path.endswith("/sys/sysAlarmRecord/alarmPage"):
            return httpx.Response(200, json={"code": 0, "data": {"total": 2098, "list": [
                {"alarmDesc": "温度越限", "id": "A7", "typeName": "环境告警",
                 "alarmStatusStr": "待处理", "regionStr": "机房", "alarmTime": "2026-06-18"}]}})
        if path.endswith("/pro/eventReport/page"):
            return httpx.Response(200, json={"code": 0, "data": {"total": 54, "list": [
                {"reportTitle": "电梯异响", "reportNo": "EV3", "reportTypeStr": "设施",
                 "statusStr": "处理中", "regionStr": "2号楼", "reportTime": "2026-06-18"}]}})
        return httpx.Response(404)

    client = ProdApiBackendClient(base_url="http://x/prod-api/project", bearer_token="svc")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    ov = asyncio.run(client.records(kind="工单"))                # 总览=权威总数+按类型分布
    assert ov.total == 4695 and ("设备巡检工单", 921) in ov.distribution

    wo = asyncio.run(client.records(kind="报修"))                # 计数=276(工单统计),记录来自 proRepairApply
    assert wo.total == 276 and wo.type_label == "物业报修工单" and wo.records[0].title == "空调不制冷"
    assert ("待调度", 109) in wo.status_distribution            # 按状态分布(来自 getOrderStatusStatistics)
    assert any(p.endswith("/pro/proRepairApply/page") for p in seen)

    al = asyncio.run(client.records(kind="告警"))                # 计数=2152(工单统计,非告警库 2098)
    assert al.total == 2152 and al.records[0].type_name == "环境告警"

    ev = asyncio.run(client.records(kind="事件"))
    assert ev.total == 54 and ev.records[0].title == "电梯异响" and ev.records[0].no == "EV3"


def test_prodapi_records_passes_time_window_to_backend():
    """时间窗:begin/end 下传 getOrderTypeStatistics(真机实测后端按时间过滤 → 计数随之变)。"""
    bodies: list = []

    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        body = json.loads(req.content)
        bodies.append((path, body))
        if path.endswith("/workOrder/statistics/getOrderTypeStatistics"):
            scoped = body.get("beginTime") == "2026-06-01 00:00:00"
            return httpx.Response(200, json={"code": 0, "data": {
                "count": 2 if scoped else 4695, "workOrderTypeCountVOS": [
                    {"orderType": "repair", "orderTypeStr": "物业报修工单", "count": 1 if scoped else 276}]}})
        if path.endswith("/workOrder/statistics/getOrderStatusStatistics"):
            return httpx.Response(200, json={"code": 0, "data": {"count": 1, "workOrderStatusVOS": []}})
        return httpx.Response(404)

    c = ProdApiBackendClient(base_url="http://x/prod-api/project", bearer_token="t")
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scoped = asyncio.run(c.records(kind="巡检", begin_time="2026-06-01 00:00:00",
                                   end_time="2026-06-30 23:59:59"))   # 计数路径(无列表接口,聚焦时间窗)
    assert scoped.window_label == "scoped"
    type_body = next(b for p, b in bodies if p.endswith("getOrderTypeStatistics"))
    assert type_body["beginTime"] == "2026-06-01 00:00:00"     # 时间窗确实下传后端


def test_prodapi_records_inspect_maintain_are_workorder_counts_not_ledger():
    """回归 bug:巡检/维保=工单类型计数(921/214),不再查 /pro/deviceInfo/* 设备台账(旧 bug 返同一份 1877)。"""
    seen: list = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req.url.path)
        if req.url.path.endswith("/workOrder/statistics/getOrderTypeStatistics"):
            return httpx.Response(200, json=_ORDER_CATALOG)
        if req.url.path.endswith("/workOrder/statistics/getOrderStatusStatistics"):
            return httpx.Response(200, json={"code": 0, "data": {"count": 0, "workOrderStatusVOS": []}})
        return httpx.Response(404)

    c = ProdApiBackendClient(base_url="http://x/prod-api/project", bearer_token="t")
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    ins = asyncio.run(c.records(kind="巡检"))
    mnt = asyncio.run(c.records(kind="维保"))
    assert ins.total == 921 and ins.type_label == "设备巡检工单" and ins.records == []
    assert mnt.total == 214 and mnt.type_label == "设备维保工单"
    assert not any("deviceInfo" in p for p in seen)             # 不再碰设备台账


def test_prodapi_records_unknown_kind_raises():
    client = ProdApiBackendClient(base_url="http://x/prod-api/project")
    with pytest.raises(BackendError):
        asyncio.run(client.records(kind="天气"))


def test_prodapi_device_health_parses_overview_and_fault_by_type():
    """device_health → healthOverview(全园区概览)+ faultPointType(按设备类型故障分布)。"""
    seen: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        if path.endswith("/pro/deviceHealth/healthOverview"):
            seen["overview_body"] = json.loads(req.content)
            return httpx.Response(200, json={"code": 0, "data": {
                "faultCount": "71", "faultRate": 4.63, "reliabilityRate": 99.79,
                "availabilityRate": 96.81, "reliabilityRateStr": "优秀", "availabilityRateStr": "优秀"}})
        if path.endswith("/pro/deviceHealth/faultPointType"):
            seen["fault_called"] = True
            return httpx.Response(200, json={"code": 0, "data": [
                {"label": "空调机组", "count": 3, "ratio": 21.43},
                {"label": "双泵", "count": 2, "ratio": 28.57}]})
        return httpx.Response(404)

    c = ProdApiBackendClient(base_url="http://x/prod-api/project", bearer_token="t")
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    hi = asyncio.run(c.device_health(system_no="kt"))
    assert seen["overview_body"] == {"systemNoList": ["kt"]} and seen.get("fault_called")
    assert hi.fault_count == "71" and hi.reliability_rate == 99.79 and hi.reliability_str == "优秀"
    assert ("空调机组", 3) in hi.fault_by_type                  # 按类型故障(非全园区总数)


def test_prodapi_device_health_overview_survives_fault_breakdown_failure():
    """faultPointType 下钻失败不致命:概览照常返、fault_by_type 空。"""
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/pro/deviceHealth/healthOverview"):
            return httpx.Response(200, json={"code": 0, "data": {"faultCount": "71"}})
        return httpx.Response(500)                              # 下钻 500

    c = ProdApiBackendClient(base_url="http://x/prod-api/project", bearer_token="t")
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    hi = asyncio.run(c.device_health())
    assert hi.fault_count == "71" and hi.fault_by_type == []


def test_prodapi_energy_uses_energy_gateway_and_parses_items():
    """W1:★能耗走**不同网关** /prod-api/energy(非 /project),解析分项树 → EnergyItem。"""
    cap: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        cap["url"] = str(req.url)
        return httpx.Response(200, json={"code": 0, "data": [
            {"configName": "电", "value": 12000.5}, {"configName": "水", "value": 800.0}]})

    c = ProdApiBackendClient(base_url="http://x/prod-api/project", bearer_token="t")
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    stat = asyncio.run(c.energy(begin_time="2026-06-01", end_time="2026-06-22", date_type="3"))
    assert "/prod-api/energy/ene/statistics/itemRate" in cap["url"]        # 不同网关前缀
    assert [(i.name, i.value) for i in stat.items] == [("电", 12000.5), ("水", 800.0)]


@pytest.mark.skipif(os.getenv("AGENT_TOOLS_LIVE_BACKEND") != "1",
                    reason="set AGENT_TOOLS_LIVE_BACKEND=1 (+ 有效 prod-api token) 跑真后端")
def test_live_getdevicepage():
    """真 prod-api(需 ASSISTANT_PROJECT_API_BASE_URL + 有效 ASSISTANT_PROJECT_API_BEARER_TOKEN)。"""
    client = ProdApiBackendClient.from_env()
    try:
        hits = asyncio.run(client.device_status(name="空调"))
        assert isinstance(hits, list)        # 通即可(数量随真数据)
    finally:
        asyncio.run(client.aclose())
