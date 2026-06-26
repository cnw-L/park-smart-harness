"""后端接入接缝(BackendClient)—— 把 prod-api 原料调用从工具里抽出来,可注入可假测。

**harness 风格、从接口文档新写、不碰旧 agent_runtime/assistant_core 代码**。grounding 源=
`后端接口情况与使用指南.md`(prod-api):后端是 CRUD/SCADA 后台、给"原料"不给"答案",故工具/
子 agent 经本接缝把原料 compose 成干净结果。

- `BackendClient`:协议(叶子工具调它)。
- `FakeBackendClient`:罐装,单测/桩 demo 用。
- `ProdApiBackendClient`:真 prod-api(httpx + bearer;基址/令牌从 env)。
  - `device_status` → `POST /common/device/getDevicePage`(既查状态、也作控制后读回)。

读/控分叉(指南§六):①可不可控=后端 isCtrl ②准不准控=后端权限(皆只读权威);
③要不要人确认=**harness 自己的 policy**(本仓的 gate/confirm)。本接缝只管"调原料",闸在 loop。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, replace
from typing import Any, Protocol

import httpx


class BackendError(Exception):
    def __init__(self, message: str, *, code: str = "backend_error") -> None:
        super().__init__(message)
        self.code = code


def _int(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _numf(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@dataclass
class DeviceHit:
    """getDevicePage 一行(harness 视角的精简设备态)。"""
    device_id: str
    name: str
    status: str = ""          # 在线/离线 等
    value: str = ""           # ★顶层 value 是聚合码(非读数!真读数在 readings),仅留兼容
    point_type_no: str = ""   # 点位类型编码(控制 grounding 用)
    point_type_name: str = ""
    region: str = ""
    point_type_id: str = ""   # 控制 grounding 查 sycPointParamType 的 key
    point_id: str = ""
    readings: list[tuple[str, str, str]] = field(default_factory=list)  # 每参数实时读数 (paramTypeNo, name, value)
    raw: dict[str, Any] = field(default_factory=dict)

    def reading_of(self, param_type_no: str) -> str | None:
        """按 paramTypeNo 取实时读数(读回对账用);无则 None。"""
        return next((v for no, _n, v in self.readings if no == param_type_no), None)


@dataclass
class ParamType:
    """sycPointParamType 一项(控制参数字典;grounding 的权威源)。"""
    param_type_no: str
    param_type_name: str = ""
    is_ctrl: bool = False                                  # ★可不可控(后端权威)
    input_type: str = ""
    unit: str = ""
    min_value: str = ""                                   # ★数值范围
    max_value: str = ""
    param_statuses: list[dict[str, Any]] = field(default_factory=list)  # ★枚举:[{status,paramValue,isAble}]
    param_type_id: str = ""
    point_type_id: str = ""
    param_type: str = ""                                  # ★paramType:1=模拟量 2=数字量(deviceCtrl 必带)
    param_sub_id: str = ""                                # ★paramSubId(deviceCtrl 透传)
    current_value: str = ""                               # ★该设备当前值(仅 getListByPointId 设备级有)
    decimal_places: str = ""                              # 小数位(模拟量精度)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecordHit:
    """事项记录一行(工单/告警/事件归一成同形,facade 统一呈现)。"""
    title: str = ""          # 标题/描述(工单标题 / 告警描述 / 事件标题)
    no: str = ""             # 单号/编号
    type_name: str = ""      # 类型(报修/告警类型/事件类型)
    status: str = ""         # 状态文案(已派单/待处理…)
    location: str = ""       # 点位/区域
    time: str = ""           # 发生/上报时间
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecordPage:
    """一页事项 + 工单口径计数。

    `total` = 权威工单数(来自 `/workOrder/statistics/getOrderTypeStatistics` 的类型计数或顶层 count);
    `type_label` = 该类型的后端名(如"设备巡检工单");`distribution` = 工单总览按类型分布 [(label,count)];
    `records` = 具体记录示例(仅报修/告警/事件有列表接口,巡检/维保等是统计计数→records 空)。
    `total_is_global` 已弃用(旧告警记录库口径);保留默认 False 仅为兼容。
    """
    total: int = 0
    records: list[RecordHit] = field(default_factory=list)
    total_is_global: bool = False
    type_label: str = ""
    distribution: list[tuple[str, int]] = field(default_factory=list)
    status_distribution: list[tuple[str, int]] = field(default_factory=list)  # 按状态分布(待调度/处理中/已完成…)
    window_label: str = ""             # 已生效的时间窗标签(如"本月");空=累计口径


@dataclass
class HealthInfo:
    """设备健康概览(`/pro/deviceHealth/healthOverview` 真机验:故障数/可靠率/可用率 + 优秀/良好标签)。"""
    fault_count: str = ""
    fault_rate: float | None = None
    reliability_rate: float | None = None
    availability_rate: float | None = None
    reliability_str: str = ""          # 优秀/良好/...
    availability_str: str = ""
    fault_by_type: list[tuple[str, int]] = field(default_factory=list)  # 按设备/点类型故障分布(faultPointType)
    raw: dict[str, Any] = field(default_factory=dict)


# 设备类型关键词 → systemNo(getDevicePage 必带 systemNo)。据真实设备清单(all_devices_getDevicePage.csv,
# 2026-06-22)覆盖全 14 系统;名字含关键词即解析,未命中再跨系统回退。env 可覆盖/补充(env 优先)。
# 顺序:具体在前(如"生活水泵"先于"水泵"、"排水"先于含水的)。
_DEFAULT_SYSTEM_BY_TYPE: dict[str, str] = {
    # 空调 kt
    "空调机组": "kt", "风机盘管": "kt", "新风机组": "kt", "新风": "kt", "空调": "kt",
    # 电气火灾 dq(注意:与"消防/信息发布 xf"不同系统)
    "电气火灾": "dq",
    # 电梯 dt
    "垂梯": "dt", "扶梯": "dt", "步梯": "dt", "电梯": "dt",
    # 视频监控 sp
    "摄像": "sp", "监控": "sp", "球机": "sp", "枪机": "sp",
    # 照明 zm
    "调光回路": "zm", "普通回路": "zm", "照明": "zm", "筒灯": "zm",
    # 电力仪表 dl(电表/电能表;勿与"能耗 ll"混)
    "电能表": "dl", "电表": "dl", "三相电": "dl", "单相电": "dl",
    # 信息发布/消防相关 xf
    "信息发布": "xf", "发布屏": "xf", "消防": "xf",
    # 停车 tc
    "充电桩": "tc", "停车": "tc", "车位": "tc", "车牌": "tc", "车辆": "tc",
    # 排水 ps(集水井/单泵/双泵)
    "排水": "ps", "集水井": "ps", "单泵": "ps", "双泵": "ps",
    # 广播 gb
    "广播": "gb",
    # 给水 gs(生活水泵)
    "生活水泵": "gs", "给水": "gs", "水泵": "gs",
    # 门禁 mj
    "门禁": "mj",
    # 热量仪表 rl
    "热量表": "rl", "热量": "rl",
    # 冷量/能耗 ll
    "冷量表": "ll", "冷量": "ll", "能耗": "ll",
}

# ★系统**伞词**:这些词是「系统名/类目」,**不出现在具体设备名里**(空调系统的设备叫"空调机组X/
# 新风机组X/风机盘管X";电梯系统的设备叫"垂梯X/扶梯X")。用它们按 deviceName 子串过滤会错:
#   "空调"→只命中"空调机组*"(漏新风机组/风机盘管);"电梯"→一台都匹配不到。
# 故伞词查询 = **查整个系统、不按名字过滤**,由格式化层按真实 pointTypeName 分组。
# (具体类型词"空调机组/垂梯/风机盘管"仍按 deviceName 子串过滤——它们就是设备名前缀。)
_SYSTEM_UMBRELLA: frozenset[str] = frozenset({
    "空调", "电梯", "照明", "监控", "停车", "排水", "给水",
})


def _norm_sep(s: str) -> str:
    """去掉分隔符(下划线/连字符/空格)做区域匹配——用户"南区2号楼"对真实"南区_2号楼_9F"。"""
    return re.sub(r"[_\-\s]+", "", s or "")


# 事项 kind → 后端工单类型码(getOrderTypeStatistics 的 orderType)。"工单"是总览,单列处理。
# 真机实测全 9 类(2026-06-22):repair/alarm/maintenance/inspect/inventory/patrol/goods/event/fitment。
# ★区分易混类型:巡检=inspect(设备巡检) vs 装修=fitment(装修巡检) vs 巡更=patrol(电子巡更);
#   盘点=inventory(设备盘点) vs 物资盘点=goods。漏掉会让模型就近误选(实测把"巡更"答成巡检数)。
_ORDER_TYPE_BY_KIND = {
    "报修": "repair", "告警": "alarm", "维保": "maintenance", "巡检": "inspect",
    "事件": "event", "巡更": "patrol", "装修": "fitment",
    "设备盘点": "inventory", "物资盘点": "goods", "盘点": "inventory",
}


@dataclass
class EnergyItem:
    name: str = ""                     # 分项名(电/水/...)
    value: float = 0.0


@dataclass
class EnergyStat:
    """能耗分项统计(`/ene/statistics/itemRate`,**能耗网关在不同前缀 /prod-api/energy**)。"""
    items: list[EnergyItem] = field(default_factory=list)
    raw: Any = None


# ── 接缝 ──────────────────────────────────────────────────────────────────────

class BackendClient(Protocol):
    async def device_status(self, *, name: str | None = None, region: str | None = None,
                            token: str | None = None) -> list[DeviceHit]: ...

    async def user_info(self, *, username: str, park_id: str | int,
                        token: str | None = None) -> tuple[str, ...]: ...

    async def point_param_types(self, *, point_type_id: str, is_ctrl: bool = True,
                                token: str | None = None) -> list[ParamType]: ...

    async def point_param_by_point_id(self, *, point_id: str, point_type_id: str = "",
                                      is_ctrl: bool = True, token: str | None = None) -> list[ParamType]: ...

    async def device_ctrl(self, *, payload: dict[str, Any],
                          token: str | None = None) -> bool: ...

    async def door_control(self, *, payload: dict[str, Any],
                           token: str | None = None) -> bool: ...

    async def records(self, *, kind: str, status: str | None = None,
                      record_type: str | None = None, point: str | None = None,
                      begin_time: str | None = None, end_time: str | None = None,
                      page_size: int = 10, token: str | None = None) -> RecordPage: ...

    async def device_health(self, *, system_no: str | None = None,
                            token: str | None = None) -> HealthInfo: ...

    async def energy(self, *, begin_time: str | None = None, end_time: str | None = None,
                     date_type: Any = None, token: str | None = None) -> EnergyStat: ...


# ── Fake(单测/桩 demo) ───────────────────────────────────────────────────────

# 默认全权限(桩 demo 看到全部工具);测 deny 时注入受限集。
_FAKE_PERMS = ("device:read", "device:control", "record:read", "life:read", "knowledge:read")


class FakeBackendClient:
    """罐装:不触网。可注入设备/权限返回值;默认给一行设备 + 全权限。"""

    def __init__(self, device_hits: list[DeviceHit] | None = None,
                 permissions: tuple[str, ...] = _FAKE_PERMS,
                 param_types: list[ParamType] | None = None, ctrl_ok: bool = True,
                 door_ok: bool = True) -> None:
        self._hits = device_hits
        self._perms = tuple(permissions)
        self._params = param_types
        self._ctrl_ok = ctrl_ok
        self._door_ok = door_ok
        self.ctrl_calls: list[dict[str, Any]] = []     # 记录下发(测试用,不触网)
        self.door_calls: list[dict[str, Any]] = []     # 记录门禁下发(走 doorControl,不混 ctrl_calls)

    async def device_status(self, *, name=None, region=None, token=None) -> list[DeviceHit]:
        if self._hits is not None:
            hits = list(self._hits)
            return [h for h in hits if region in (h.region or "")] if region else hits
        temp = "26" if name and "3" in name else "24"
        hits = [DeviceHit(device_id="ac-3f-2", name=name or "设备",
                          status="在线", value="5", point_type_no="KTJZ",
                          point_type_name="空调机组", region="南区_2号楼_9F",
                          point_type_id="3700", point_id="pt-1",
                          readings=[("temControl", "温度控制", temp), ("temperature", "送风温度", "26")])]
        return [h for h in hits if region in (h.region or "")] if region else hits

    async def user_info(self, *, username, park_id, token=None) -> tuple[str, ...]:
        return self._perms

    async def point_param_types(self, *, point_type_id, is_ctrl=True, token=None) -> list[ParamType]:
        if self._params is not None:
            return list(self._params)
        # 默认:一个数值(温度设定 16-30,可逆)+ 一个枚举(开关)+ 一个不可控(只读)
        return [
            ParamType(param_type_no="WD", param_type_name="温度设定", is_ctrl=True,
                      min_value="16", max_value="30", point_type_id=str(point_type_id),
                      param_type_id="p-wd"),
            ParamType(param_type_no="KG", param_type_name="开关", is_ctrl=True,
                      param_statuses=[{"status": "开", "paramValue": "1", "isAble": True},
                                      {"status": "关", "paramValue": "0", "isAble": True}],
                      point_type_id=str(point_type_id), param_type_id="p-kg"),
            ParamType(param_type_no="RO", param_type_name="只读量", is_ctrl=False,
                      point_type_id=str(point_type_id)),
        ]

    async def point_param_by_point_id(self, *, point_id, point_type_id="", is_ctrl=True, token=None) -> list[ParamType]:
        # 设备级:同类型字典 + 给模拟量补 paramType=1 + currentValue(getListByPointId 才有的设备级字段)
        params = await self.point_param_types(point_type_id=point_type_id or "fake-pt", is_ctrl=is_ctrl, token=token)
        if self._params is not None:
            return params
        out = []
        for p in params:
            if p.param_type_no == "WD":
                out.append(replace(p, param_type="1", current_value="26", param_sub_id="sub-wd"))
            elif p.param_type_no == "KG":
                out.append(replace(p, param_type="2"))
            else:
                out.append(p)
        return out

    async def device_ctrl(self, *, payload, token=None) -> bool:
        self.ctrl_calls.append(dict(payload))          # 记录、不触网
        return self._ctrl_ok

    async def door_control(self, *, payload, token=None) -> bool:
        self.door_calls.append(dict(payload))          # 门禁走独立通道,不混 deviceCtrl
        return self._door_ok

    async def records(self, *, kind, status=None, record_type=None, point=None,
                      begin_time=None, end_time=None, page_size=10, token=None) -> RecordPage:
        # 工单口径(对齐 getOrderTypeStatistics):total=权威工单数,type_label=后端类型名;
        # 巡检/维保等仅统计计数(records 空);报修/告警/事件附记录示例。时间窗→缩量 + 标 scoped。
        scoped = bool(begin_time and end_time)
        wl = "scoped" if scoped else ""
        if kind == "工单":
            dist = [("物业报修工单", 276), ("设备告警工单", 2152), ("设备巡检工单", 921),
                    ("设备维保工单", 214), ("电子巡更工单", 477)]
            if scoped:                                     # 罐装"窗内"小量,演示时间过滤生效
                dist = [("物业报修工单", 1), ("设备巡检工单", 1)]
            return RecordPage(total=(2 if scoped else 4695), type_label="工单总览",
                              distribution=dist, window_label=wl)
        _STATUS = [("待调度", 109), ("待指派", 55), ("待接单", 13), ("处理中", 26),
                   ("验收中", 13), ("已完成", 52), ("已关闭", 8)]
        canned = {
            "报修": RecordPage(total=276, type_label="物业报修工单", records=[RecordHit(
                title="空调不制冷", no="YWWBX202604180001", type_name="物业报修",
                status="处理中", location="南区_2号楼_9F", time="2026-06-18 09:12")]),
            "告警": RecordPage(total=2152, type_label="设备告警工单", records=[RecordHit(
                title="温度越限", no="AL20260618007", type_name="设备告警",
                status="待处理", location="南区_2号楼-机房", time="2026-06-18 10:30")]),
            "事件": RecordPage(total=54, type_label="事件上报工单", records=[RecordHit(
                title="电梯异响上报", no="EV20260618003", type_name="事件上报",
                status="处理中", location="2号楼", time="2026-06-18 08:45")]),
            "巡检": RecordPage(total=921, type_label="设备巡检工单"),
            "维保": RecordPage(total=214, type_label="设备维保工单"),
        }
        page = canned.get(kind, RecordPage())
        page.status_distribution = _STATUS
        page.window_label = wl
        if scoped:                                         # 窗内缩量(演示)
            page.total = 1
        return page

    async def device_health(self, *, system_no=None, token=None) -> HealthInfo:
        return HealthInfo(fault_count="71", fault_rate=4.63, reliability_rate=99.79,
                          availability_rate=96.81, reliability_str="优秀", availability_str="优秀",
                          fault_by_type=[("空调机组", 3), ("双泵", 2), ("步梯", 1)])

    async def energy(self, *, begin_time=None, end_time=None, date_type=None, token=None) -> EnergyStat:
        return EnergyStat(items=[EnergyItem("电", 12000.0), EnergyItem("水", 800.0)])


# ── 真 prod-api ───────────────────────────────────────────────────────────────

def _bearer(token: str) -> str:
    v = token.strip()
    return v if v.lower().startswith("bearer ") else f"Bearer {v}"


class ProdApiBackendClient:
    """真 prod-api 客户端。grounding 以 `后端接口情况与使用指南.md` 为准;瘦、自包含、httpx。"""

    def __init__(self, *, base_url: str, bearer_token: str | None = None,
                 timeout_seconds: float = 10.0, default_system_no: str = "kt",
                 system_by_type: dict[str, str] | None = None) -> None:
        self._base = base_url.rstrip("/")            # 形如 …/prod-api/project
        # ★能耗在不同网关前缀(真机实测 /prod-api/energy,非 /project)→ 由 project base 推导。
        # 只替**最后一段** `/project`(rsplit 1),避免主机名含 "project" 时 replace-all 损坏 host。
        self._energy_base = "/energy".join(self._base.rsplit("/project", 1))
        # 门禁通道控制在 /through(与 /project 平级,去掉末尾 /project)——deviceCtrl 控门是假成功。
        self._through_base = self._base.rsplit("/project", 1)[0]
        self._bearer = bearer_token
        self._client = httpx.AsyncClient(timeout=timeout_seconds)
        # getDevicePage **必须**带 systemNo(系统/设备大类码,如 kt=空调)。空则 COMMON_SYSTEM_IS_NOT_EXIST。
        self._default_system = default_system_no
        # 内置全系统映射(据真实清单)+ 传入覆盖;None=只用内置默认。
        self._system_by_type = {**_DEFAULT_SYSTEM_BY_TYPE, **(system_by_type or {})}

    @classmethod
    def from_env(cls) -> "ProdApiBackendClient":
        base = os.getenv("ASSISTANT_PROJECT_API_BASE_URL")
        if not base:
            raise BackendError("ASSISTANT_PROJECT_API_BASE_URL 未配置", code="not_configured")
        try:
            timeout = float(os.getenv("ASSISTANT_PROJECT_API_TIMEOUT_SECONDS") or "10")
        except ValueError:
            timeout = 10.0
        sysmap: dict[str, str] = {}
        for pair in (os.getenv("ASSISTANT_PROJECT_API_SYSTEM_NO_BY_DEVICE_TYPE") or "").split(","):
            if ":" in pair:
                k, v = pair.split(":", 1)
                if k.strip() and v.strip():
                    sysmap[k.strip()] = v.strip()
        return cls(base_url=base, bearer_token=os.getenv("ASSISTANT_PROJECT_API_BEARER_TOKEN"),
                   timeout_seconds=timeout,
                   default_system_no=(os.getenv("ASSISTANT_PROJECT_API_DEFAULT_SYSTEM_NO") or "kt"),
                   system_by_type=sysmap)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _resolve_system_no(self, name: str | None) -> str:
        """设备类型 → systemNo(grounding 第一跳的简版:名里命中类型关键词即取其码,否则默认)。"""
        if name:
            for dtype, sysno in self._system_by_type.items():
                if dtype in name:
                    return sysno
        return self._default_system

    async def device_status(self, *, name: str | None = None, region: str | None = None,
                            system_no: str | None = None, token: str | None = None) -> list[DeviceHit]:
        # POST /common/device/getDevicePage —— systemNo 必带(空则后端报错)。
        primary = system_no or self._resolve_system_no(name)
        # ★伞词(空调/电梯/…=系统名)→ 查整个系统、不按名字过滤(否则漏类型/零命中);类型词照常过滤。
        if name and not system_no and name in _SYSTEM_UMBRELLA:
            return await self._device_page(primary, None, region, token)
        hits = await self._device_page(primary, name, region, token)
        # 名字/区域给了但首选系统空 → 跨其它已配系统找(未映射类型/跨系统;区域查也常跨系统)。
        # 命中 / 无任何过滤(列全部)/ 显式 systemNo → 不回退。
        if hits or (not name and not region) or system_no:
            return hits
        for sysno in self._candidate_systems():
            if sysno == primary:
                continue
            hits = await self._device_page(sysno, name, region, token)
            if hits:
                return hits
        return []

    async def _device_page(self, system_no: str, name: str | None, region: str | None,
                           token: str | None) -> list[DeviceHit]:
        data_filter: dict[str, Any] = {"systemNo": system_no}
        if name:
            data_filter["deviceName"] = name
        # 区域无服务端过滤字段(getDevicePage 只认 regionId)→ 多取后按**接口实时 regionName** 客户端过滤
        # (不建静态区域索引:regionName 每次来自实时接口)。
        # ★page_size 一律 200:枚举/伞词查询(如"园区有哪些电梯")真实可达 35 台,旧 no-region=10
        #   会截断到 10 台、却被如实计数报成"共10台"(漏 25 台)。deviceName 在服务端过滤,大页无害。
        page_size = 200
        data = await self._post("/common/device/getDevicePage",
                                {"pageNum": 1, "pageSize": page_size, "data": data_filter}, token)
        rows = data.get("list") or data.get("records") or []
        hits = [self._to_hit(r) for r in rows if isinstance(r, dict)]
        if region:
            # ★分隔符无关匹配:用户打"南区2号楼",真实 regionName 是"南区_2号楼_9F_展厅"——
            #   去掉下划线/连字符/空格再子串比对,否则"南区2号楼"恒 0 命中(真机踩坑)。
            rq = _norm_sep(region)
            hits = [h for h in hits if rq in _norm_sep(h.region or "")]
        return hits

    def _candidate_systems(self) -> list[str]:
        """已配置的全部 systemNo(去重保序):默认 + 类型映射里的值。回退扫描用。"""
        return list(dict.fromkeys([self._default_system, *self._system_by_type.values()]))

    @staticmethod
    def _to_hit(r: dict[str, Any]) -> DeviceHit:
        def s(k):
            v = r.get(k)
            return "" if v is None else str(v)
        # ★真读数在 pointTypeParamVOList(每参数 paramValue),非顶层 value(那是聚合码)。
        readings = [(str(it.get("paramTypeNo") or ""), str(it.get("paramTypeName") or ""),
                     str(it.get("paramValue") if it.get("paramValue") is not None else ""))
                    for it in (r.get("pointTypeParamVOList") or []) if isinstance(it, dict)]
        return DeviceHit(
            device_id=s("deviceId"), name=s("deviceName"), status=s("status"),
            value=s("value"), point_type_no=s("pointTypeNo"),
            point_type_name=s("pointTypeName"), region=s("regionName"),
            point_type_id=s("pointTypeId"), point_id=s("pointId"), readings=readings, raw=r,
        )

    async def point_param_types(self, *, point_type_id: str, is_ctrl: bool = True,
                                token: str | None = None) -> list[ParamType]:
        # POST /syc/sycPointParamType/page —— 类型级控制参数字典(按 pointTypeId;无 currentValue)
        body = {"pageNum": 1, "pageSize": 50,
                "data": {"pointTypeId": point_type_id, "isCtrl": is_ctrl}}
        data = await self._post("/syc/sycPointParamType/page", body, token)
        rows = data.get("list") or data.get("records") or []
        return [self._to_param(r) for r in rows if isinstance(r, dict)]

    async def point_param_by_point_id(self, *, point_id: str, point_type_id: str = "",
                                      is_ctrl: bool = True, token: str | None = None) -> list[ParamType]:
        # POST /syc/sycPointParamType/getListByPointId —— **设备级权威控制发现**(带 currentValue +
        # 该设备模拟量边界 + 数字量枚举)。★实测:**必须 pointId + pointTypeId(int)一起传**才返参数,
        # 只给 pointId 返空(踩坑点)。
        body: dict[str, Any] = {"pointId": point_id, "isCtrl": is_ctrl, "isShow": "Y"}
        try:
            if point_type_id:
                body["pointTypeId"] = int(str(point_type_id).strip())
        except (TypeError, ValueError):
            pass
        data = await self._post_data("/syc/sycPointParamType/getListByPointId", body, token)  # data 是 list
        rows = data if isinstance(data, list) else (
            (data.get("list") or data.get("records") or []) if isinstance(data, dict) else [])
        return [self._to_param(r) for r in rows if isinstance(r, dict)]

    @staticmethod
    def _to_param(r: dict[str, Any]) -> ParamType:
        def s(k):
            v = r.get(k)
            return "" if v is None else str(v)
        return ParamType(
            param_type_no=s("paramTypeNo"), param_type_name=s("paramTypeName"),
            is_ctrl=bool(r.get("isCtrl")), input_type=s("inputType"), unit=s("unit"),
            min_value=s("minValue"), max_value=s("maxValue"),
            param_statuses=[x for x in (r.get("paramStatuses") or []) if isinstance(x, dict)],
            param_type_id=s("paramTypeId"), point_type_id=s("pointTypeId"),
            param_type=s("paramType"), param_sub_id=s("paramSubId"),
            current_value=s("currentValue"), decimal_places=s("decimalPlaces"), raw=r,
        )

    async def device_ctrl(self, *, payload: dict[str, Any], token: str | None = None) -> bool:
        # POST /common/device/deviceCtrl → RBoolean{data: bool}(**已受理 ≠ 已生效**,对账靠读回)
        try:
            resp = await self._client.post(f"{self._base}/common/device/deviceCtrl",
                                           json=payload, headers=self._headers(token))
        except httpx.HTTPError as exc:
            raise BackendError(f"deviceCtrl 失败: {exc}", code="request_failed") from exc
        return bool(self._parse(resp))                 # data 是裸布尔(非 dict),直接 bool

    async def door_control(self, *, payload: dict[str, Any], token: str | None = None) -> bool:
        # ★门禁通道控制 → POST /through/pt/ptDoor/doorControl(deviceCtrl 控门返200但门不动=假成功)。
        # body 照平台抓包:currentParamValue/status/deviceIds/pointIds/isAble,不发 paramType/paramSubId。
        try:
            resp = await self._client.post(f"{self._through_base}/through/pt/ptDoor/doorControl",
                                           json=payload, headers=self._headers(token))
        except httpx.HTTPError as exc:
            raise BackendError(f"doorControl 失败: {exc}", code="request_failed") from exc
        return bool(self._parse(resp))

    async def records(self, *, kind: str, status: str | None = None,
                      record_type: str | None = None, point: str | None = None,
                      begin_time: str | None = None, end_time: str | None = None,
                      page_size: int = 10, token: str | None = None) -> RecordPage:
        """事项查询(对齐工单统计域)。权威计数来自 `/workOrder/statistics/getOrderTypeStatistics`,
        **支持时间窗**(begin_time/end_time 真机实测生效:全量4695→6月2)。typed kind 另取
        `getOrderStatusStatistics`(同窗+orderType)拿**按状态分布**(待调度/处理中/已完成…),
        支持"待处理/已完成"等状态问题。报修/告警/事件再附记录示例。**不查 `/pro/deviceInfo/*`**(那是台账)。"""
        win = {k: v for k, v in (("beginTime", begin_time), ("endTime", end_time)) if v}
        stats = await self._post("/workOrder/statistics/getOrderTypeStatistics", dict(win), token)
        type_rows = [r for r in (stats.get("workOrderTypeCountVOS") or []) if isinstance(r, dict)]

        if kind == "工单":                                # 总览:(窗内)总数 + 按类型分布
            dist = [(str(r.get("orderTypeStr") or ""), _int(r.get("count"))) for r in type_rows]
            return RecordPage(total=_int(stats.get("count")), type_label="工单总览",
                              distribution=dist, window_label=("" if not win else "scoped"))

        code = _ORDER_TYPE_BY_KIND.get(kind)
        if code is None:
            raise BackendError(f"未知事项类型: {kind!r}", code="unknown_kind")
        row = next((r for r in type_rows if str(r.get("orderType")) == code), None)
        total = _int(row.get("count")) if row else 0     # (窗内)权威工单计数
        label = str(row.get("orderTypeStr") or "") if row else kind

        # 按状态分布(同窗 + orderType):支持"待处理/已完成"等状态问题(真机:repair 待调度109/已完成52…)
        sdata = await self._post("/workOrder/statistics/getOrderStatusStatistics",
                                 {"orderType": code, **win}, token)
        status_dist = [(str(v.get("orderStatusStr") or v.get("orderStatus") or ""), _int(v.get("count")))
                       for v in (sdata.get("workOrderStatusVOS") or []) if isinstance(v, dict)]
        if row is None:                                  # 类型统计没这行(被时间窗滤空)→ 用状态统计的 count 兜底
            total = _int(sdata.get("count"))

        # 报修/告警/事件有具体列表接口 → 附记录示例(报修带 deviceName/时间窗下传)
        records: list[RecordHit] = []
        if kind == "报修":
            data: dict[str, Any] = dict(win)
            if point:
                data["deviceName"] = point
            payload = await self._post("/pro/proRepairApply/page",
                                       {"pageNum": 1, "pageSize": page_size, "data": data}, token)
            rows = payload.get("list") or payload.get("records") or []
            records = [self._wo_hit(r) for r in rows if isinstance(r, dict)]
        elif kind == "告警":
            data = {}
            if record_type:
                data["typeName"] = record_type
            if point:
                data["pointName"] = point
            payload = await self._post("/sys/sysAlarmRecord/alarmPage",
                                       {"pageNum": 1, "pageSize": page_size, "data": data}, token)
            rows = payload.get("list") or payload.get("records") or []
            records = [self._alarm_hit(r) for r in rows if isinstance(r, dict)]
        elif kind == "事件":
            payload = await self._post("/pro/eventReport/page",
                                       {"pageNum": 1, "pageSize": page_size, "data": {}}, token)
            rows = payload.get("list") or payload.get("records") or []
            records = [self._event_hit(r) for r in rows if isinstance(r, dict)]

        return RecordPage(total=total, type_label=label, records=records,
                          status_distribution=status_dist, window_label=("" if not win else "scoped"))

    @staticmethod
    def _wo_hit(r: dict[str, Any]) -> RecordHit:
        def s(k): v = r.get(k); return "" if v is None else str(v)
        return RecordHit(title=s("repairContent") or s("repairTitle") or s("content"),
                         no=s("repairNo") or s("orderNo") or s("applyNo"),
                         type_name=s("orderTypeStr") or s("repairTypeStr") or s("orderType"),
                         status=s("repairStatusStr") or s("statusStr") or s("repairStatus"),
                         location=s("regionStr") or s("address"),
                         time=s("createTime") or s("applyTime"), raw=r)

    @staticmethod
    def _alarm_hit(r: dict[str, Any]) -> RecordHit:
        def s(k): v = r.get(k); return "" if v is None else str(v)
        return RecordHit(title=s("alarmDesc") or s("riseRemark"),
                         no=s("id") or s("alarmRecordId"),
                         type_name=s("typeName") or s("alarmTypeStr"),
                         status=s("alarmStatusStr") or s("alarmStatus"),
                         location=s("regionStr") or s("alarmAddress") or s("pointName"),
                         time=s("alarmTime"), raw=r)

    @staticmethod
    def _event_hit(r: dict[str, Any]) -> RecordHit:
        def s(k): v = r.get(k); return "" if v is None else str(v)
        return RecordHit(title=s("reportTitle"),
                         no=s("reportNo"),
                         type_name=s("reportTypeStr") or s("reportType"),
                         status=s("statusStr") or s("status"),
                         location=s("regionStr") or s("detailedLocation"),
                         time=s("reportTime") or s("createTime"), raw=r)

    async def device_health(self, *, system_no: str | None = None,
                            token: str | None = None) -> HealthInfo:
        # POST /pro/deviceHealth/healthOverview —— **全园区**概览(故障数/可靠率/可用率 + 优秀/良好标签)。
        # 再下钻 faultPointType 取**按设备/点类型故障分布**(问某类设备时给该类故障数,而非只有全园区总数)。
        body: dict[str, Any] = {}
        if system_no:
            body["systemNoList"] = [system_no]
        data = await self._post("/pro/deviceHealth/healthOverview", body, token)
        fault_by_type: list[tuple[str, int]] = []
        try:                                              # 下钻失败不致命 → 空表降级,概览照常返
            rows = await self._post_list("/pro/deviceHealth/faultPointType", {}, token)
            fault_by_type = [(str(r.get("label") or ""), _int(r.get("count")))
                             for r in rows if isinstance(r, dict) and r.get("label")]
        except BackendError:
            pass
        return HealthInfo(
            fault_count=str(data.get("faultCount") or ""),
            fault_rate=_numf(data.get("faultRate")),
            reliability_rate=_numf(data.get("reliabilityRate")),
            availability_rate=_numf(data.get("availabilityRate")),
            reliability_str=str(data.get("reliabilityRateStr") or ""),
            availability_str=str(data.get("availabilityRateStr") or ""),
            fault_by_type=fault_by_type,
            raw=data)

    async def energy(self, *, begin_time: str | None = None, end_time: str | None = None,
                     date_type: Any = None, token: str | None = None) -> EnergyStat:
        # POST /ene/statistics/itemRate —— ★能耗在**不同网关** `_energy_base`(/prod-api/energy);
        # 返回分项树 [{configName,value,children}],非 dict → 用 _client+_parse(非 _post)。
        # beginTime/endTime 须 **"yyyy-MM-dd HH:mm:ss"**(后端 java.util.Date,纯日期串解析错)。
        # ★live blocker(2026-06-22 真机):itemRate/areaRate/unitAreaEne **一律 SQL syntax error**
        #   (与参数无关,疑后端本环境无能耗配置/SQL 模板 bug);仅 eneAlarmType 通但返 null。
        #   → **客户端封装正确(MockTransport 验)、live 数据是后端侧 blocker**,非本层缺陷。
        body = {k: v for k, v in {"beginTime": begin_time, "endTime": end_time,
                                  "dateType": date_type}.items() if v is not None}
        try:
            resp = await self._client.post(f"{self._energy_base}/ene/statistics/itemRate",
                                           json=body, headers=self._headers(token))
        except httpx.HTTPError as exc:
            raise BackendError(f"能耗查询失败: {exc}", code="request_failed") from exc
        rows = self._parse(resp) or []
        items = [EnergyItem(name=str(r.get("configName") or ""), value=_numf(r.get("value")) or 0.0)
                 for r in rows if isinstance(r, dict)]
        return EnergyStat(items=items, raw=rows)

    async def user_info(self, *, username: str, park_id: str | int,
                        token: str | None = None) -> tuple[str, ...]:
        # GET /user/info/{username}/{parkId} → **能力级**权限码(permissions+apiPermissions)。
        # ★devicePermission/dataScope 是**资源级**(看哪些设备/数据)→ 委托后端 token 过滤,**不喂 gate**
        #   (设计 §六:harness gate 只判能力级;混轴喂 gate 是 bug)。
        data = await self._get(f"/user/info/{username}/{park_id}", token)
        out: list[str] = []
        for key in ("permissions", "apiPermissions"):
            v = data.get(key)
            if isinstance(v, list):
                out.extend(str(x) for x in v if x)
        return tuple(dict.fromkeys(out))                 # 去重保序(能力级)

    def _headers(self, token: str | None) -> dict[str, str]:
        tok = token or self._bearer
        return {"Authorization": _bearer(tok)} if tok else {}

    @staticmethod
    def _parse(resp: "httpx.Response") -> Any:
        if resp.status_code != 200:
            raise BackendError(f"prod-api HTTP {resp.status_code}", code="http_error")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise BackendError("prod-api 返回非 JSON", code="bad_response") from exc
        code = payload.get("code")
        if code not in (0, 200, "0", "200", None):
            raise BackendError(str(payload.get("msg") or f"backend code {code}"), code="backend_code")
        return payload.get("data")

    async def _post(self, path: str, body: dict[str, Any], token: str | None) -> dict[str, Any]:
        data = await self._post_data(path, body, token)
        return data if isinstance(data, dict) else {}

    async def _post_data(self, path: str, body: dict[str, Any], token: str | None) -> Any:
        """同 _post 但返回 _parse 的原始 data(可为 list/bool,如 getListByPointId 返 list)。"""
        try:
            resp = await self._client.post(f"{self._base}{path}", json=body, headers=self._headers(token))
        except httpx.HTTPError as exc:
            raise BackendError(f"prod-api 请求失败: {exc}", code="request_failed") from exc
        return self._parse(resp)

    async def _post_list(self, path: str, body: dict[str, Any], token: str | None) -> list[Any]:
        """data 是裸列表的端点(如 faultPointType)用这个;非列表降级成空表。"""
        try:
            resp = await self._client.post(f"{self._base}{path}", json=body, headers=self._headers(token))
        except httpx.HTTPError as exc:
            raise BackendError(f"prod-api 请求失败: {exc}", code="request_failed") from exc
        data = self._parse(resp)
        return data if isinstance(data, list) else []

    async def _get(self, path: str, token: str | None) -> dict[str, Any]:
        try:
            resp = await self._client.get(f"{self._base}{path}", headers=self._headers(token))
        except httpx.HTTPError as exc:
            raise BackendError(f"prod-api 请求失败: {exc}", code="request_failed") from exc
        data = self._parse(resp)
        return data if isinstance(data, dict) else {}
