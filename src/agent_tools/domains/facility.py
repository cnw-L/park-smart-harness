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
            # ★查无 = 业务否(ok=False)→ 执行器渲成 [error],**无进展看门狗据此 3 次内停**(防 qwen
            #   反复换名空转吃满步数);消息明确"后端正常·别重试·直接回报无此设备"。
            return ToolResult(ok=False, content="", error=(
                f"未查到匹配「{scope}」的设备(后端正常,只是在册设备里没有这个名字)。"
                f"别用相近名字反复重试(会空耗步数)——直接如实回报「无此设备」让用户确认,别臆断成后端故障。"))
        # 0/1/N 候选都回(N 时交子 agent 消歧;真区域树消歧后续接)。
        # ★摘要优先:首行给**可直接作答**的类型/状态计数——小模型(qwen)对长列表会空转/re-call(实测
        #   40 台明细 1819 字 → qwen 不作答反复重查触 stall)。明细后置且短(示例,真实总数以首行计数为准,
        #   仿 record_query 的"示例N条")。"空调"=系统含多类机组,首行类型计数让模型据此分组、不再幻觉。
        type_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        for d in hits:
            t = d.point_type_name or d.point_type_no or "其他"
            type_counts[t] = type_counts.get(t, 0) + 1
            s = d.status or "未知"
            status_counts[s] = status_counts.get(s, 0) + 1
        DETAIL = 12
        shown = hits[:DETAIL]
        lines = []
        for d in shown:
            tag = d.point_type_name or d.point_type_no
            # 真读数来自 readings(pointTypeParamVOList),非顶层 value(聚合码)
            reads = "、".join(f"{nm}={v}" for _no, nm, v in d.readings if v) if d.readings else ""
            lines.append(" ".join(p for p in [
                f"{d.name}(id={d.device_id})", d.status,
                f"[{tag}]" if tag else "", d.region, reads] if p))
        if len(hits) == 1:
            return ToolResult(ok=True, content=lines[0])                       # 单台:直接列,无需摘要
        by_type = "、".join(f"{t}{c}台" for t, c in type_counts.items())
        by_status = "、".join(f"{s}{c}台" for s, c in status_counts.items())
        more = len(hits) - len(shown)
        tail = (f"\n…明细仅列前 {len(shown)} 台示例,其余 {more} 台已计入上方分类计数(要控制请指定设备编号)"
                if more > 0 else "")
        # 首行=权威总数+按类型+按状态(可直接作答);控制须唯一目标、绝不替用户选。
        head = (f"共 {len(hits)} 台。按类型:{by_type}。按状态:{by_status}。"
                f"(若要控制/调节须先指定具体设备编号,绝不替用户选)\n明细:\n")
        return ToolResult(ok=True, content=head + "\n".join(lines) + tail)
    return LoopTool(name="device_status",
                    description=("查询设备的实时状态(在线/读数);可按设备名(device)和/或区域(region)过滤。"
                                 "**关键:系统名≠设备类型**——「空调」是系统(含空调机组/新风机组/风机盘管等多类),"
                                 "「电梯」是系统(含垂梯/扶梯)。用户说「所有空调/有哪些空调」就**原样传「空调」**"
                                 "(工具会返回全系统并按真实类型分组),**绝不要自作主张缩成「空调机组」**;"
                                 "只有用户明确点某类型(如「空调机组」「垂梯」)才传该具体类型。"),
                    parameters={"type": "object", "properties": {
                        "device": {"type": "string", "description": (
                            "设备名/类型/系统名。系统名(空调/电梯/照明/监控/停车/排水/给水)=查整个系统并按类型分组;"
                            "具体类型(空调机组/垂梯/充电桩)=只查该类;具体设备(空调机组106)=单台。"
                            "**用户说什么类目就传什么,别擅自换成更具体的词**")},
                        "region": {"type": "string", "description": "区域关键词,如 2号楼/南区/9F(分隔符无关,按实时 regionName 过滤)"}}},
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
            CAP = 12
            top = "、".join(f"{label} {cnt}起" for label, cnt in hi.fault_by_type[:CAP] if label)
            tail = f"(等共 {len(hi.fault_by_type)} 类)" if len(hi.fault_by_type) > CAP else ""
            head += f"\n按设备类型故障分布:{top}{tail}"     # 截断也如实标"等共N类",不静默丢
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
        toolset=list(FACILITY_LEAVES), budget=LoopBudget(max_iterations=5),  # 当工具用:有界,够查1-2次+综合,不够则返回需澄清
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
