"""P5:控制真执行 —— `_execute` 发 grounded payload + 读回对账(已受理 ≠ 已生效)。

**真 deviceCtrl 绝不进自动化测试**:这里全注 `FakeBackendClient`(记录、不触网)/
`MockTransport`(确定性 URL/body/RBoolean)。真发只经 demo 人工确认 UI。
"""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from agent_loop.messages import ToolCallReq

from agent_tools.backend import BackendError, DeviceHit, FakeBackendClient, ProdApiBackendClient
from agent_tools.proposal import ControlProposal, ProposalStore
from agent_tools.proposal_control import ProposalControlCapability, _INVALID


def _seed(store: ProposalStore, *, reversibility="可逆", token="utok",
          device_id="30302", value="24") -> str:
    return store.put(ControlProposal(
        target="3号楼空调", action="deviceCtrl",
        params={"deviceId": device_id, "paramValue": value, "paramTypeNo": "WD"},
        reversibility=reversibility, token=token))


def _approve(cap: ProposalControlCapability, handle: str):
    call = ToolCallReq(id="e1", name="execute_proposal", arguments={"handle": handle})
    pending = cap.freeze(call)
    return pending, asyncio.run(cap.resolve(pending, "approve"))


# ── 真执行 + 读回对账 ─────────────────────────────────────────────────────────
def test_execute_fires_devicectrl_and_reads_back_effective():
    """读回**被控参数读数**=目标 paramValue → effective=True;后端确实收到 grounded payload。"""
    store = ProposalStore()
    backend = FakeBackendClient(device_hits=[DeviceHit(
        device_id="30302", name="3号楼空调", status="在线", value="5",   # 顶层 value 是聚合码
        readings=[("WD", "温度设定", "24")])])                            # 真读数在 readings
    cap = ProposalControlCapability(store, backend=backend, execution_mode="real")
    handle = _seed(store)

    _, res = _approve(cap, handle)
    assert res.ok and cap.execute_count == 1
    assert len(backend.ctrl_calls) == 1                       # 恰下发一次
    assert backend.ctrl_calls[0]["paramValue"] == "24"        # grounded payload(非模型重打)
    assert "effective=True" in res.content


def test_readback_uses_param_readings_not_aggregate_value():
    """回归 bug:对账必须比**被控参数读数**,不能比顶层 value(聚合码)。value=5、读数WD=24 → effective=True。"""
    store = ProposalStore()
    backend = FakeBackendClient(device_hits=[DeviceHit(
        device_id="30302", name="x", status="在线", value="5",
        readings=[("WD", "温度设定", "24"), ("temperature", "送风温度", "30")])])
    cap = ProposalControlCapability(store, backend=backend, execution_mode="real")
    _, res = _approve(cap, _seed(store))
    assert "effective=True" in res.content and "WD读回=24" in res.content


def test_readback_setpoint_absent_is_unknown_not_false():
    """设定值型常不在读数列表(读回的是测量量)→ 诚实标 unknown(无即时读回),非冒充 True/False。"""
    store = ProposalStore()
    backend = FakeBackendClient(device_hits=[DeviceHit(
        device_id="30302", name="x", status="在线", value="5",
        readings=[("temperature", "送风温度", "30")])])      # 无 WD 设定值读回
    cap = ProposalControlCapability(store, backend=backend, execution_mode="real")
    _, res = _approve(cap, _seed(store))
    assert "effective=unknown" in res.content and "无即时读回" in res.content


def test_accepted_but_offline_is_not_effective():
    """已受理但设备离线/读数不符 → effective=False(已受理 ≠ 已生效,对账兜住)。"""
    store = ProposalStore()
    backend = FakeBackendClient(device_hits=[DeviceHit(
        device_id="30302", name="3号楼空调", status="离线", value="")])
    cap = ProposalControlCapability(store, backend=backend, execution_mode="real")

    _, res = _approve(cap, _seed(store))
    assert res.ok and cap.execute_count == 1
    assert "effective=False" in res.content and "未生效" in res.content


def test_backend_rejects_acceptance():
    """deviceCtrl 返 False(后端未受理)→ readback 标 accepted=False,不读回。"""
    store = ProposalStore()
    backend = FakeBackendClient(ctrl_ok=False)
    cap = ProposalControlCapability(store, backend=backend, execution_mode="real")

    _, res = _approve(cap, _seed(store))
    assert "accepted=False" in res.content


class _CtrlRaiseBackend(FakeBackendClient):
    async def device_ctrl(self, *, payload, token=None):
        raise BackendError("认证失败,无法访问系统资源", code="backend_code")


def test_devicectrl_failure_is_graceful_not_crash():
    """★真下发抛(token 失效/网络/超时)→ resolve **接住**、返回 ok=False + 真因,
    **绝不让异常炸穿确认流**(否则前端只看到 network error、看不到真原因)。"""
    store = ProposalStore()
    cap = ProposalControlCapability(store, backend=_CtrlRaiseBackend(), execution_mode="real")
    pending = cap.freeze(ToolCallReq(id="e1", name="execute_proposal", arguments={"handle": _seed(store)}))
    res = asyncio.run(cap.resolve(pending, "approve"))
    assert res.ok is False and "控制下发失败" in (res.error or "") and "认证失败" in (res.error or "")
    assert cap.execute_count == 0 and len(store._store) == 0   # 失败不计执行、清提案


# ── 幂等:无后端幂等键,harness 内账本防重发 ──────────────────────────────────
def test_idempotent_resolve_executes_once():
    store = ProposalStore()
    backend = FakeBackendClient(device_hits=[DeviceHit(
        device_id="30302", name="x", status="在线", value="24.0℃")])
    cap = ProposalControlCapability(store, backend=backend, execution_mode="real")
    handle = _seed(store)

    call = ToolCallReq(id="e1", name="execute_proposal", arguments={"handle": handle})
    pending = cap.freeze(call)
    r1 = asyncio.run(cap.resolve(pending, "approve"))
    r2 = asyncio.run(cap.resolve(pending, "approve"))          # 同 idem_key 重入
    assert r1.content == r2.content                            # 返缓存
    assert cap.execute_count == 1 and len(backend.ctrl_calls) == 1   # 后端只被打一次


# ── ★门栓 F3:执行端独立重断可逆,不可逆硬拦(纵深防御) ──────────────────────
def test_irreversible_blocked_at_execute_F3():
    """不可逆本该在 grounding 当场被拒;即便旁路到这,F3 门栓硬拦,绝不下发。"""
    store = ProposalStore()
    backend = FakeBackendClient()
    cap = ProposalControlCapability(store, backend=backend, execution_mode="real")
    handle = _seed(store, reversibility="不可逆")

    _, res = _approve(cap, handle)
    assert res.ok is False and "F3" in (res.error or "")
    assert cap.execute_count == 0 and backend.ctrl_calls == []   # 一次都没发
    assert store.get(handle) is None                            # 提案已清


# ── ★simulated 默认:确认后不真下发(硬依赖未就绪的安全缺省) ──────────────────
def test_simulated_mode_skips_devicectrl():
    """默认 simulated:确认后**不调 device_ctrl**,只读回当前态、标[模拟]未真实下发。"""
    store = ProposalStore()
    backend = FakeBackendClient(device_hits=[DeviceHit(
        device_id="30302", name="x", status="在线", value="5",
        readings=[("WD", "温度设定", "23")])])
    cap = ProposalControlCapability(store, backend=backend)    # 默认 simulated
    _, res = _approve(cap, _seed(store))
    assert res.ok and backend.ctrl_calls == []                # 绝不真下发
    assert "[模拟]" in res.content and "未真实下发" in res.content


# ── ★handle 不经模型:execute 不传 handle → 取最近未消解提案 ───────────────────
def test_execute_latest_unresolved_when_no_handle():
    store = ProposalStore()
    h = _seed(store, value="24")
    cap = ProposalControlCapability(store)
    pending = cap.freeze(ToolCallReq(id="e1", name="execute_proposal", arguments={}))  # 无 handle
    assert pending.handle == h                                # 取到 store 最近那条
    assert pending.frozen_action["name"] == "deviceCtrl"      # 非 __invalid_proposal__(冻的是真提案)
    # ★模型乱填 handle(qwen 抄错/编造,如 "742")也回落到最近一条 —— C8 根治
    p2 = cap.freeze(ToolCallReq(id="e2", name="execute_proposal", arguments={"handle": "742"}))
    assert p2.handle == h and p2.frozen_action["name"] == "deviceCtrl"


def test_freeze_invalid_only_when_store_empty():
    """store 真空(从没登记过提案)→ 才铸 __invalid_proposal__ 哨兵(demo 友好卡)。"""
    cap = ProposalControlCapability(ProposalStore())
    p = cap.freeze(ToolCallReq(id="e1", name="execute_proposal", arguments={"handle": "x"}))
    assert p.frozen_action["name"] == _INVALID


# ── backend=None echo 回归(旧测/无后端路径不动) ────────────────────────────
def test_backend_none_echo_regression():
    store = ProposalStore()
    cap = ProposalControlCapability(store, execution_mode="real")   # 无后端 → echo "ok"
    _, res = _approve(cap, _seed(store))
    assert res.ok and "readback=ok" in res.content and cap.execute_count == 1


# ── reject 不下发 ─────────────────────────────────────────────────────────────
def test_reject_does_not_fire():
    store = ProposalStore()
    backend = FakeBackendClient()
    cap = ProposalControlCapability(store, backend=backend, execution_mode="real")
    handle = _seed(store)

    call = ToolCallReq(id="e1", name="execute_proposal", arguments={"handle": handle})
    pending = cap.freeze(call)
    res = asyncio.run(cap.resolve(pending, "reject"))
    assert res.ok and "rejected" in res.content.lower()
    assert backend.ctrl_calls == [] and cap.execute_count == 0


# ── ProdApiBackendClient.device_ctrl:MockTransport 确定性(URL/body/RBoolean) ──
def test_prodapi_device_ctrl_posts_payload_and_unpacks_rbool():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"code": 200, "data": True})   # RBoolean 受理

    client = ProdApiBackendClient(base_url="http://x/prod-api/project", bearer_token="svc")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    payload = {"deviceId": "30302", "paramTypeNo": "WD", "paramValue": "24"}
    ok = asyncio.run(client.device_ctrl(payload=payload, token="utok"))

    assert ok is True
    assert captured["url"].endswith("/common/device/deviceCtrl")       # 指南端点
    assert captured["body"] == payload                                 # 透传 grounded payload
    assert captured["auth"] == "Bearer utok"                           # 用户 token 透传


def test_prodapi_device_ctrl_backend_code_error_raises():
    def handler(request):
        return httpx.Response(200, json={"code": 401, "msg": "认证失败"})
    client = ProdApiBackendClient(base_url="http://x/prod-api/project")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(BackendError):
        asyncio.run(client.device_ctrl(payload={"deviceId": "x"}))


def test_execute_routes_doorcontrol_to_door_endpoint():
    """门禁提案(action=doorControl)→ 走 backend.door_control,绝不误走 deviceCtrl(假成功)。"""
    store = ProposalStore()
    backend = FakeBackendClient(device_hits=[DeviceHit(device_id="30302", name="大门", status="在线", value="")])
    cap = ProposalControlCapability(store, backend=backend, execution_mode="real")
    h = store.put(ControlProposal(target="大门", action="doorControl",
        params={"deviceIds":[30302],"pointId":"p","status":"开门","currentParamValue":"2","isAble":True},
        reversibility="可逆", token="t"))
    res = asyncio.run(cap.resolve(cap.freeze(ToolCallReq(id="e", name="execute_proposal", arguments={"handle": h})), "approve"))
    assert backend.door_calls and backend.door_calls[0]["status"] == "开门"   # 走了 door
    assert backend.ctrl_calls == []                                          # 没误走 deviceCtrl


# ── Part3 控制幂等批A:确定性 idem + WAL + in_flight 消解 ──────────────────────

class _SpyLedger:
    """可持久化账本桩(镜像 PgIdempotencyLedger get/put_if_absent/update),记录事件顺序。"""
    def __init__(self): self.rows = {}; self.events = []
    async def get(self, k): return self.rows.get(k)
    async def put_if_absent(self, k, status, result):
        self.events.append(("put", status))
        if k in self.rows: return False
        self.rows[k] = {"status": status, **result}; return True
    async def update(self, k, status, result):
        self.events.append(("update", status)); self.rows[k] = {"status": status, **result}


def test_idem_key_is_deterministic_per_proposal():
    """确定性 idem_key:同提案两次 freeze → 同 key(uuid4 会每次不同→WAL 永远 miss→重发)。"""
    store = ProposalStore()
    cap = ProposalControlCapability(store)
    h = store.put(ControlProposal(target="x", action="deviceCtrl",
        params={"deviceId": 1, "paramValue": "24"}, reversibility="可逆"))
    call = ToolCallReq(id="e", name="execute_proposal", arguments={"handle": h})
    assert cap.freeze(call).idem_key == cap.freeze(call).idem_key


def test_wal_writes_in_flight_before_done():
    """WAL:先 put(in_flight) 后 update(done);成功路径正常返回。"""
    store = ProposalStore()
    backend = FakeBackendClient(device_hits=[DeviceHit(device_id="1", name="x", status="在线",
        value="5", readings=[("WD", "温度", "24")])])
    led = _SpyLedger()
    cap = ProposalControlCapability(store, backend=backend, execution_mode="real", ledger=led)
    h = store.put(ControlProposal(target="x", action="deviceCtrl",
        params={"deviceId": 1, "paramValue": "24", "paramTypeNo": "WD"}, reversibility="可逆", token="t"))
    res = asyncio.run(cap.resolve(cap.freeze(ToolCallReq(id="e", name="execute_proposal", arguments={"handle": h})), "approve"))
    assert led.events[0] == ("put", "in_flight") and ("update", "done") in led.events
    assert res.ok and len(backend.ctrl_calls) == 1


def test_in_flight_irreversible_returns_unknown_no_resend():
    """崩溃窗口 in_flight + 不可逆 → 状态未知、绝不重发(at-most-once 核心)。"""
    store = ProposalStore()
    backend = FakeBackendClient()
    led = _SpyLedger()
    cap = ProposalControlCapability(store, backend=backend, execution_mode="real", ledger=led)
    h = store.put(ControlProposal(target="阀", action="deviceCtrl", params={"deviceId": 1, "paramValue": "1"},
        reversibility="不可逆", token="t"))
    p = cap.freeze(ToolCallReq(id="e", name="execute_proposal", arguments={"handle": h}))
    led.rows[p.idem_key] = {"status": "in_flight", "content": ""}      # 模拟上次发了一半崩
    res = asyncio.run(cap.resolve(p, "approve"))
    assert res.ok is False and "状态未知" in (res.error or "")
    assert backend.ctrl_calls == []                                   # 不可逆绝不重发


def test_wal_done_returns_cached_no_refire():
    """账本已 done(同 idem)→ 返缓存、绝不二次下发。"""
    store = ProposalStore()
    backend = FakeBackendClient(device_hits=[DeviceHit(device_id="1", name="x", status="在线", value="24")])
    led = _SpyLedger()
    cap = ProposalControlCapability(store, backend=backend, execution_mode="real", ledger=led)
    h = store.put(ControlProposal(target="x", action="deviceCtrl", params={"deviceId": 1, "paramValue": "24"},
        reversibility="可逆", token="t"))
    p = cap.freeze(ToolCallReq(id="e", name="execute_proposal", arguments={"handle": h}))
    led.rows[p.idem_key] = {"status": "done", "content": "[executed] cached"}
    res = asyncio.run(cap.resolve(p, "approve"))
    assert res.ok and "cached" in res.content and backend.ctrl_calls == []


def test_freeze_scopes_latest_to_thread_no_cross_user_leak():
    """★跨用户串提案防护:用户B 无 handle execute,绝不能取到用户A 的提案。"""
    store = ProposalStore()
    store.put(ControlProposal(target="甲设备", action="deviceCtrl",
        params={"deviceId": 1, "paramValue": "24"}, reversibility="可逆", thread_id="userA"))
    cap = ProposalControlCapability(store)
    pB = cap.freeze(ToolCallReq(id="e", name="execute_proposal", arguments={}), thread_id="userB")
    assert pB.frozen_action["name"] == "__invalid_proposal__"     # B 本会话无提案 → 哨兵,不串甲
    pA = cap.freeze(ToolCallReq(id="e2", name="execute_proposal", arguments={}), thread_id="userA")
    assert pA.frozen_action["name"] == "deviceCtrl"               # A 取到自己的
