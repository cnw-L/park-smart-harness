"""事项处理域 —— **扁平工具** `record_query`(工单/告警/事件…查询)。

判据(v8 收敛):运行事项**只一个工具**(record_query),无可"组织"、返回是计数+短样本无需隔离 →
**不够格当子 agent**(Agent-as-Tool=用组织对抗规模)。故升顶层扁平工具,主用 plan 直接编排——
多 kind 综合(查工单+查告警+汇总)由**主**多次调用 + 汇总,不再绕子循环(去掉一层最薄、最易空转的子)。

`record_query(kind, status?, time?, type?)`:按 `kind` 派发到真后端
(`BackendClient.records` → proRepairApply/alarmPage/eventReport,见 backend.py)。
"""
from __future__ import annotations

from agent_loop.tools import LoopTool, ToolContext, ToolResult

from ..backend import BackendClient, BackendError, FakeBackendClient, RecordPage
from ..timewin import parse_time_window

# 真机 9 类工单(2026-06-22):工单=总览;其余对应一个 orderType。区分巡检/装修/巡更、设备盘点/物资盘点。
_KINDS = ("工单", "报修", "告警", "事件", "巡检", "维保", "巡更", "装修", "设备盘点", "物资盘点")


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
