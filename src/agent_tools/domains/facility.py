"""设施运行超域 —— **agent-as-tool**(消歧重:楼→具体设备;多子能力内部路由)。

子 agent **只读**:查 device_status/energy/health;需要控制时调 `propose_control` 登记提案
(非控制、可进子),把 handle 随 final 文本回报主控。真执行在主会话的 `execute_proposal`。

v1 叶子全为桩,真后端(接 agent_runtime device/energy gateway)是下一个 plan。
"""
from __future__ import annotations

from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.gate import Gate
from agent_loop.llm import ModelCaller
from agent_loop.subagent import make_subagent_tool
from agent_loop.tools import LoopTool, ToolContext, ToolResult, LoopToolRegistry

from ..backend import BackendClient, BackendError, FakeBackendClient
from ..catalog import ToolSpec
from ..propose import make_propose_control_tool
from ..proposal import ProposalStore

# facility 叶子的 toolset 名单(组织,非元数据)——子 agent 暴露这几个叶子。
FACILITY_LEAVES = ("device_status", "energy_query", "device_health", "propose_control")


def _device_status_tool(backend: BackendClient) -> LoopTool:
    """查设备实时态 —— 经 BackendClient 调真 prod-api `getDevicePage`(指南§三.1)。
    token 从身份脊柱 `ctx.principal.token` 透传(按用户权限查)。"""
    async def h(args: dict, ctx: ToolContext) -> ToolResult:
        device = str(args.get("device", "")).strip()
        region = str(args.get("region", "")).strip()
        token = getattr(ctx.principal, "token", None)
        try:
            hits = await backend.device_status(name=device or None, region=region or None, token=token)
        except BackendError as exc:
            return ToolResult(ok=False, content="", error=f"设备查询失败:{exc}")
        if not hits:
            scope = "、".join(p for p in [device, region] if p) or "条件"
            return ToolResult(ok=True, content=f"未查到匹配「{scope}」的设备")
        # 0/1/N 候选都回(N 时交子 agent 消歧;真区域树消歧后续接)
        lines = []
        for d in hits[:10]:
            tag = d.point_type_name or d.point_type_no
            # 真读数来自 readings(pointTypeParamVOList),非顶层 value(聚合码)
            reads = "、".join(f"{nm}={v}" for _no, nm, v in d.readings if v) if d.readings else ""
            lines.append(" ".join(p for p in [
                f"{d.name}(id={d.device_id})", d.status,
                f"[{tag}]" if tag else "", d.region, reads] if p))
        head = "" if len(hits) <= 1 else f"匹配到 {len(hits)} 台,候选:\n"
        return ToolResult(ok=True, content=head + "\n".join(lines))
    return LoopTool(name="device_status",
                    description="查询设备的实时状态(在线/读数);可按设备名(device)和/或区域(region,如「2号楼」「南区」)过滤",
                    parameters={"type": "object", "properties": {
                        "device": {"type": "string", "description": "设备名/类型,如 空调机组、充电桩、生活水泵"},
                        "region": {"type": "string", "description": "区域关键词,如 2号楼/南区/9F(按实时 regionName 过滤)"}}},
                    handler=h)


def _energy_query_tool(backend: BackendClient) -> LoopTool:
    """园区能耗分项 —— 经 `BackendClient.energy`(真:`/prod-api/energy/ene/statistics/itemRate`)。"""
    async def h(args: dict, ctx: ToolContext) -> ToolResult:
        token = getattr(getattr(ctx, "principal", None), "token", None)
        try:
            stat = await backend.energy(begin_time=args.get("begin_time"),
                                        end_time=args.get("end_time"),
                                        date_type=args.get("date_type"), token=token)
        except BackendError as exc:
            return ToolResult(ok=False, content="", error=f"能耗查询失败:{exc}")
        if not stat.items:
            return ToolResult(ok=True, content="能耗:无数据")
        body = "、".join(f"{it.name} {it.value}" for it in stat.items)
        return ToolResult(ok=True, content=f"能耗分项:{body}")
    return LoopTool(name="energy_query", description="查询园区能耗分项(电/水/…,按时间)",
                    parameters={"type": "object", "properties": {
                        "begin_time": {"type": "string"}, "end_time": {"type": "string"},
                        "date_type": {"type": "string"}}},
                    handler=h)


def _device_health_tool(backend: BackendClient) -> LoopTool:
    """**全园区**设备健康概览 + 按设备类型故障分布 —— `BackendClient.device_health`
    (`/pro/deviceHealth/healthOverview` + `faultPointType` 下钻)。故障数/可靠率是**全园区**口径,
    不是某台设备;问某类设备时给该类故障分布(如空调机组 3 起),别把全园区总数挂到单设备名下。"""
    async def h(args: dict, ctx: ToolContext) -> ToolResult:
        token = getattr(getattr(ctx, "principal", None), "token", None)
        try:
            hi = await backend.device_health(system_no=args.get("system_no") or None, token=token)
        except BackendError as exc:
            return ToolResult(ok=False, content="", error=f"设备健康查询失败:{exc}")
        parts = [f"全园区故障 {hi.fault_count} 起" if hi.fault_count else ""]
        if hi.reliability_rate is not None:
            parts.append(f"可靠率 {hi.reliability_rate}%({hi.reliability_str})")
        if hi.availability_rate is not None:
            parts.append(f"可用率 {hi.availability_rate}%({hi.availability_str})")
        head = "(全园区)设备健康概览:" + "、".join(p for p in parts if p)
        if hi.fault_by_type:
            top = "、".join(f"{label} {cnt}起" for label, cnt in hi.fault_by_type[:8] if label)
            head += f"\n按设备类型故障分布:{top}"
        return ToolResult(ok=True, content=head)
    return LoopTool(name="device_health",
                    description="查询全园区设备健康概览(故障数/可靠率/可用率)+ 按设备类型故障分布",
                    parameters={"type": "object", "properties": {"system_no": {"type": "string"}}},
                    handler=h)


def facility_leaf_specs(*, backend: BackendClient | None = None, store: ProposalStore,
                        reversibility_map: dict | None = None) -> list[ToolSpec]:
    """设施域叶子的 ToolSpec(进同一 ToolCatalog,统一治理)。capability_code 显式:
    读叶子=`device:read`;**propose_control=`device:control`**(控制流起点,起草也要控制权,
    且与 is_control=False 正交——不弹确认但卡权限)。"""
    backend = backend or FakeBackendClient()
    return [
        ToolSpec(tool=_device_status_tool(backend), capability_code="device:read"),
        ToolSpec(tool=_energy_query_tool(backend), capability_code="device:read"),
        ToolSpec(tool=_device_health_tool(backend), capability_code="device:read"),
        ToolSpec(tool=make_propose_control_tool(store, backend, reversibility_map),
                 capability_code="device:control"),
    ]


def build_facility_agent(*, model_caller: ModelCaller, leaf_registry: LoopToolRegistry,
                         gate: Gate | None = None, assembler=None) -> LoopTool:
    """组装设施运行子 agent(读叶子 + propose_control=grounding 闸)。leaf_registry 由组合根从
    **同一 catalog** 派生(统一治理);`gate` 下沉子 loop → 叶子调用同等受 deny-first 闸查
    (propose_control 据此被 device:control 卡)。"""
    cfg = LoopConfig(
        model="chat", max_tokens=512, temperature=0.2, role="leaf",
        toolset=list(FACILITY_LEAVES), budget=LoopBudget(max_iterations=8),
    )
    return make_subagent_tool(
        name="facility_agent",
        description=(
            "【设备管理】查询设备运行状态/健康/能耗 + 控制提案。需要控制设备时,**登记控制提案**"
            "(返回 handle)回报主控、不自行执行。用自然语言描述要查/要控的设备,"
            "如「查3号楼空调温度」「3号楼空调太热,提案调到24度」「本月能耗」。"
        ),
        sub_config=cfg, sub_registry=leaf_registry, model_caller=model_caller,
        assembler=assembler, gate=gate,
    )
