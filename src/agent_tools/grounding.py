"""控制 grounding(设计 §五 + 三道闸①)—— 把模型意图变成**已校验、已分可逆性**的可执行动作。

铁律(grounding doc §五.1):**LLM 只产意图,规则查权威字典(`sycPointParamType`)解析、不编 id/值**。
`ground_control` 是闸①(可不可控 + 范围 + 可逆性)的落点:模型推不动越权/越界/误分类的控制。

可逆性(承重):
- 能解析出 paramValue 的(枚举状态 或 数值范围)= 后端 **`paramValue` 绝对写** = **状态型 = 可逆**(读回可验)。
- **非状态型**(相对调节/触发脉冲/扣费)结构上**解析不出**(无枚举/无范围)→ 在解析步就被拒(genuinely unknown→拒)。
- `reversibility_map` 是**非状态型 denylist**:已知"长得像绝对写、实则非状态型"(扣费金额/相对量)的例外标"不可逆"。**上线前必须把已知非状态型登进来**(R4b 安全旋钮)。
- **★硬依赖**:后端 `deviceCtrl` 无幂等键 → **不可逆当场拒、降级人工**(崩溃重发会双发)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .backend import BackendClient, BackendError, ParamType

Reversibility = Literal["可逆", "不可逆"]

# 非状态型 denylist:key=paramTypeNo 或 (pointTypeNo,paramTypeNo) → "不可逆"。v1 空(空调调温=可逆);
# 接道闸/扣费/相对调节前**必须**把它们登进来。
DEFAULT_REVERSIBILITY_MAP: dict = {}


@dataclass(frozen=True)
class Intent:
    """模型给的控制意图(设备坐标从 device_status 候选抬来、非编造;param/value 是人话)。"""
    point_type_id: str
    point_type_no: str = ""
    device_id: str = ""
    point_id: str = ""
    system_no: str = ""
    param: str = ""           # 要控参数:paramTypeNo 或 paramTypeName 关键词(如 "温度设定"/"开关")
    value: str = ""           # 期望值:枚举状态("开")或数值("24")


@dataclass(frozen=True)
class Grounded:
    device_id: str
    point_id: str
    point_type_id: str
    point_type_no: str
    param_type_id: str
    param_type_no: str
    param_type_name: str
    param_value: str
    param_status: str
    system_no: str
    reversibility: Reversibility
    param_type: str = ""          # paramType:1=模拟量 2=数字量(deviceCtrl 必带)
    param_sub_id: str = ""        # paramSubId(透传)
    current_value: str = ""       # 该设备当前值(getListByPointId 设备级;供读回/展示)

    def payload(self) -> dict:
        """deviceCtrl 下发体 = 完整 `DeviceControlEvent`(对齐生产 `_device_ctrl_payload` + 接口文档):
        deviceId/pointId 既给单值又给**数组**;deviceId 转 int;带 paramType/paramSubId。只放非空字段。"""
        out: dict = {}
        did = _int_or_none(self.device_id)
        if did is not None:
            out["deviceId"] = did                     # int(接口要求)
            out["deviceIds"] = [did]                  # ★数组(生产/接口都发)
        if self.point_id:
            out["pointId"] = self.point_id
            out["pointIds"] = [self.point_id]         # ★数组
        pairs = [("pointTypeId", self.point_type_id), ("pointTypeNo", self.point_type_no),
                 ("paramTypeId", self.param_type_id), ("paramTypeNo", self.param_type_no),
                 ("paramTypeName", self.param_type_name), ("paramType", self.param_type),
                 ("paramValue", self.param_value), ("paramStatus", self.param_status),
                 ("paramSubId", self.param_sub_id), ("systemNo", self.system_no)]
        for k, v in pairs:
            if v not in (None, ""):
                out[k] = v
        return out


@dataclass(frozen=True)
class Rejection:
    reason: str               # 给模型/用户看的人话
    code: str                 # 机器码:not_controllable/out_of_range/value_not_in_enum/ungroundable/
                              #         param_not_found/no_point_type/bad_device_id/irreversible_no_idem


def _match_param(params: list[ParamType], key: str) -> ParamType | None:
    key = (key or "").strip()
    if not key:
        return None
    for p in params:                                   # 精确 paramTypeNo(唯一,最具体)
        if p.param_type_no and p.param_type_no == key:
            return p
    # 名字含关键词 —— **控制场景优先可控参数**:真机同设备常有只读"送风温度"与可控"温度控制"并存,
    # 关键词"温度"若取到只读项会误判"不可控"。控制 grounding 找的是可控参数,故 is_ctrl 优先。
    name_hits = [p for p in params if key in (p.param_type_name or "")]
    if name_hits:
        return next((p for p in name_hits if p.is_ctrl), name_hits[0])
    for p in params:                                   # 关键词命中某枚举状态(如 "运行")
        if any(key == str(s.get("status") or "") for s in p.param_statuses):
            return p
    return None


def _resolve_value(p: ParamType, value: str) -> tuple[str, str] | Rejection:
    """→ (paramValue, paramStatus) 或 Rejection。枚举:匹配 status/paramValue;数值:范围校验。"""
    value = (value or "").strip()
    if p.param_statuses:                               # 枚举:绝对写到某状态
        for s in p.param_statuses:
            status, pv = str(s.get("status") or ""), str(s.get("paramValue") or "")
            if value in (status, pv) and s.get("isAble") not in (False, 0, "0"):
                return pv, status
        return Rejection(f"取值「{value}」不在可选状态内", "value_not_in_enum")
    lo, hi = _num(p.min_value), _num(p.max_value)
    if lo is not None or hi is not None:               # 数值:范围内绝对写
        v = _num(value)
        if v is None:
            return Rejection(f"取值「{value}」不是数值", "out_of_range")
        if (lo is not None and v < lo) or (hi is not None and v > hi):
            return Rejection(f"取值 {value} 超范围 [{p.min_value},{p.max_value}]", "out_of_range")
        # ★模拟量(温度等):deviceCtrl 要 **paramStatus 也填目标值**(实测:只给 paramValue 后端 param_exception)。
        return value, value
    return Rejection(f"参数「{p.param_type_name}」取值无法校验(无枚举/无范围)", "ungroundable")


def _classify(point_type_no: str, param_type_no: str, rmap: dict) -> Reversibility:
    # 命中非状态型 denylist → 不可逆;否则(能解析出=绝对写=状态型)→ 可逆
    if (point_type_no, param_type_no) in rmap or param_type_no in rmap:
        return "不可逆"
    return "可逆"


async def ground_control(intent: Intent, *, backend: BackendClient, reversibility_map: dict | None = None,
                         token: str | None = None, backend_has_idempotency: bool = False
                         ) -> Grounded | Rejection:
    rmap = reversibility_map or {}
    if not intent.point_type_id and not intent.point_id:
        return Rejection("缺少设备点位坐标,请先查设备(device_status)", "no_point_type")
    if intent.device_id and _int_or_none(intent.device_id) is None:
        # deviceCtrl 的 deviceId 必须是数字(payload 转 int)。非数字 = 坐标抬错 → 当场拒,
        # 别静默产出缺 deviceId 的残缺 payload(否则下发时后端报错、用户看不出真因)。
        return Rejection(f"设备 id「{intent.device_id}」非数字,无法下发——请先用 device_status 取正确设备坐标",
                         "bad_device_id")
    try:
        # ★设备级权威发现优先:有 pointId 用 getListByPointId(带 currentValue + 该设备边界);
        #   退化才用类型级 sycPointParamType/page(仅 pointTypeId)。
        if intent.point_id:
            params = await backend.point_param_by_point_id(point_id=intent.point_id,
                                                           point_type_id=intent.point_type_id,
                                                           is_ctrl=True, token=token)
        else:
            params = await backend.point_param_types(point_type_id=intent.point_type_id,
                                                     is_ctrl=True, token=token)
    except BackendError as exc:
        return Rejection(f"读取参数字典失败:{exc}", "dict_error")

    p = _match_param(params, intent.param)
    if p is None:
        return Rejection(f"找不到可控参数「{intent.param}」", "param_not_found")
    if not p.is_ctrl:
        return Rejection(f"参数「{p.param_type_name}」不可控(isCtrl=false)", "not_controllable")

    resolved = _resolve_value(p, intent.value)
    if isinstance(resolved, Rejection):
        return resolved
    param_value, param_status = resolved

    rev = _classify(intent.point_type_no, p.param_type_no, rmap)
    if rev == "不可逆" and not backend_has_idempotency:    # ★硬依赖:无幂等键不让不可逆上线
        return Rejection("识别为不可逆操作(非状态型),后端暂不支持安全下发,已降级人工",
                         "irreversible_no_idem")

    return Grounded(
        device_id=intent.device_id, point_id=intent.point_id,
        point_type_id=intent.point_type_id, point_type_no=intent.point_type_no,
        param_type_id=p.param_type_id, param_type_no=p.param_type_no,
        param_type_name=p.param_type_name, param_value=param_value,
        param_status=param_status, system_no=intent.system_no, reversibility=rev,
        param_type=p.param_type, param_sub_id=p.param_sub_id, current_value=p.current_value,
    )


def _num(v) -> float | None:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _int_or_none(v) -> int | None:
    """deviceId 转 int(接口要求 int + deviceIds:[int]);解析不出返 None(payload 就不带该字段)。"""
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None
