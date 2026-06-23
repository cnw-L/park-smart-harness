"""事项处理超域 —— **子 agent**(工单/告警/事件…的查询 + 多记录综合)。

判据(v4):事项需要"自己的一条 ReAct 循环"——综合多记录(查工单→看结果→关联告警→汇总)+ 隔离
(长列表留子上下文、只回吐摘要)。这跟 facility 同构:**同一个 `run_loop`、同一套动态逻辑**,
查几次/查哪些/怎么综合由子模型动态决定,**非写死流水线**;只是叶子换成 record 查询。

叶子 `record_query(kind, status?, time?, type?)`:按 `kind` 派发到真后端
(`BackendClient.records` → proRepairApply/alarmPage/eventReport,见 backend.py)。
"""
from __future__ import annotations

from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.gate import Gate
from agent_loop.llm import ModelCaller
from agent_loop.subagent import make_subagent_tool
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolContext, ToolResult

from ..backend import BackendClient, BackendError, FakeBackendClient, RecordPage
from ..catalog import ToolSpec
from ..timewin import parse_time_window

# 真机 9 类工单(2026-06-22):工单=总览;其余对应一个 orderType。区分巡检/装修/巡更、设备盘点/物资盘点。
_KINDS = ("工单", "报修", "告警", "事件", "巡检", "维保", "巡更", "装修", "设备盘点", "物资盘点")

# 运行管理 agent 暴露的叶子(组织,非元数据)。
RECORDS_LEAVES = ("record_query",)


def _format(kind: str, page: RecordPage, win_label: str = "") -> str:
    scope = f"【{win_label}】" if win_label else ""
    caliber = win_label or "累计"                          # 有时间窗→标窗口;否则标"累计"防误读成区间
    # 工单总览:(窗内)总数 + 按类型分布
    if page.distribution:
        dist = " / ".join(f"{label} {cnt}" for label, cnt in page.distribution if label)
        return f"{scope}工单总览({caliber}口径):共 {page.total} 单。按类型:{dist}"
    label = page.type_label or kind
    head = f"{scope}{label}:{caliber}共 {page.total} 单"
    if page.status_distribution:                          # 按状态分布 → 支持"待处理/已完成"等状态问题
        sd = " / ".join(f"{s} {c}" for s, c in page.status_distribution if s)
        head += f"。按状态:{sd}"
    if page.records:                                      # 报修/告警/事件附记录示例
        body = "\n".join(
            f"- {r.title or '(无标题)'}[{r.no}] 类型={r.type_name or '—'} "
            f"状态={r.status or '—'} 位置={r.location or '—'} 时间={r.time or '—'}"
            for r in page.records)
        head += f"\n示例 {len(page.records)} 条:\n{body}"
    return head


def make_record_query_tool(backend: BackendClient | None = None) -> LoopTool:
    backend = backend or FakeBackendClient()

    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        kind = str(args.get("kind", ""))
        if kind not in _KINDS:
            return ToolResult(ok=False, content="",
                              error=f"unknown record kind: {kind!r}(应为 {'/'.join(_KINDS)})")
        token = getattr(getattr(ctx, "principal", None), "token", None)
        begin, end, win_label = parse_time_window(args.get("time"))  # NL 时间 → beginTime/endTime
        try:
            page = await backend.records(
                kind=kind, status=args.get("status") or None,
                record_type=args.get("type") or None,
                point=args.get("device") or None,
                begin_time=begin, end_time=end, token=token)
        except BackendError as exc:
            return ToolResult(ok=False, content="", error=f"事项查询失败: {exc}")
        content = _format(kind, page, win_label=win_label)
        # 用户点名了时间但解析不出 → 诚实降级(累计口径,不冒充区间)
        if args.get("time") and not win_label:
            content += f"\n⚠ 未能解析时间「{args.get('time')}」,以上为累计口径(非该区间数)。"
        elif win_label and page.total == 0:
            # 功能覆盖:窗内 0 单,但本园数据可能集中在更早时段(工单时间全生效、数据偏旧)→ 补查累计,
            # 让用户看到该类目**确有数据**,而非误以为功能坏了。
            try:
                allp = await backend.records(
                    kind=kind, status=args.get("status") or None,
                    record_type=args.get("type") or None,
                    point=args.get("device") or None, token=token)
                if allp.total > 0:
                    content += (f"\n(注:{win_label}内 0 单;不限时间累计共 {allp.total} 单"
                                f"——数据可能集中在更早时段)")
            except BackendError:
                pass
        return ToolResult(ok=True, content=content)

    return LoopTool(
        name="record_query",
        description=("查询园区运行事项(工单口径)。kind 必填:工单=总览(总数+按类型分布);"
                     "其余=该类型工单数 + 按状态分布(报修/告警/事件附记录示例)。"
                     "kind 选:工单|报修|告警|事件|巡检|维保|巡更|装修|设备盘点|物资盘点(区分:"
                     "巡检=设备巡检、装修=装修巡检、巡更=电子巡更)。"
                     "支持时间窗:time 传自然语言(今天/本周/本月/最近7天…)→ 后端按时间过滤;"
                     "状态(待处理/已完成…)看返回的「按状态」分布作答。"),
        parameters={
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": list(_KINDS),
                         "description": "工单=总览;其余=对应类型工单"},
                "status": {"type": "string", "description": "状态词(可选);也可直接读返回的按状态分布"},
                "time": {"type": "string", "description": "自然语言时间窗,如 今天/本周/本月/最近7天"},
                "type": {"type": "string", "description": "告警类型名等(细分过滤)"},
                "device": {"type": "string", "description": "设备名(报修按设备过滤;告警按点位)"},
            },
            "required": ["kind"],
        },
        handler=handler,
        is_control=False,
    )


def records_leaf_specs(*, backend: BackendClient | None = None) -> list[ToolSpec]:
    """事项域叶子的 ToolSpec(进同一 ToolCatalog,统一治理)。capability_code=`record:read`。"""
    return [ToolSpec(tool=make_record_query_tool(backend), capability_code="record:read")]


def build_records_agent(*, model_caller: ModelCaller, leaf_registry: LoopToolRegistry,
                        gate: Gate | None = None, assembler=None) -> LoopTool:
    """组装事项处理子 agent(与 facility 同构:同一 `run_loop`、动态 ReAct)。leaf_registry 由组合根
    从同一 catalog 派生;`gate` 下沉子 loop(叶子同等受 deny-first 闸查)。"""
    cfg = LoopConfig(
        model="chat", max_tokens=512, temperature=0.2, role="leaf",
        toolset=list(RECORDS_LEAVES), budget=LoopBudget(max_iterations=8),
    )
    return make_subagent_tool(
        name="records_agent",
        description=(
            "【运行管理】查询/综合工单、告警、事件。用自然语言描述要查/要理的运行事项,"
            "如「今天的报修工单和告警」「3号楼最近的工单和告警理一下」。"
            "需要创建报修等写操作时**登记控制提案**(返回 handle)回报主控、不自行执行。"
        ),
        sub_config=cfg, sub_registry=leaf_registry, model_caller=model_caller,
        assembler=assembler, gate=gate,
    )
