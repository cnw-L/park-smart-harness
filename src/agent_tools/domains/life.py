"""生活服务超域 —— **扁平 ×3**(会议室/停车/餐厅查询)。

参数发散(会议室=时间/人数,停车=位置,餐厅=菜单),facade 的 union 会坑弱模型 → 三个
自描述的扁平工具反而最省。预订(会议室)是写 → 走 propose_control / execute_proposal,不在此。

★**后端无对应接口、保持桩**(2026-06-22 勘探:prod-api 无会议室/餐厅接口,停车仅月卡支付非查车位)
 → 真实接口封装覆盖不了生活服务;demo 仍可演示桩。后端后续提供则按设备/事项同防腐模式接真。
"""
from __future__ import annotations

from agent_loop.tools import LoopTool, ToolContext, ToolResult


# ★生活服务后端无接口 → 返回的是占位演示数据(保留:无真实接口的工具可用演练数据)。用强标记让模型
#   **务必如实声明是演示数据**,别把"42个车位/红烧肉"当真实信息答出去(实测弱模型会吞掉"(桩)"小尾巴)。
_DEMO_TAG = "【演示数据·暂无真实后端接口,请向用户声明这是示例】"


def make_meeting_query_tool() -> LoopTool:
    async def h(args: dict, ctx: ToolContext) -> ToolResult:
        return ToolResult(ok=True, content=(
            f"{_DEMO_TAG} 会议室(时间={args.get('time', '今天')},"
            f"人数={args.get('capacity', '不限')}):A301/B205 可用"))
    return LoopTool(name="meeting_query", description="查询可用会议室(按时间/人数)。注:后端暂无接口,返回演示数据",
                    parameters={"type": "object", "properties": {
                        "time": {"type": "string"}, "capacity": {"type": "integer"}}},
                    handler=h)


def make_parking_query_tool() -> LoopTool:
    async def h(args: dict, ctx: ToolContext) -> ToolResult:
        return ToolResult(ok=True, content=(
            f"{_DEMO_TAG} 停车(区域={args.get('area', '全园')}):剩余车位 42"))
    return LoopTool(name="parking_query", description="查询停车位(按区域)。注:后端暂无接口,返回演示数据",
                    parameters={"type": "object", "properties": {"area": {"type": "string"}}},
                    handler=h)


def make_restaurant_query_tool() -> LoopTool:
    async def h(args: dict, ctx: ToolContext) -> ToolResult:
        return ToolResult(ok=True, content=(
            f"{_DEMO_TAG} 餐厅({args.get('meal', '午餐')}):今日menu 红烧肉/清蒸鱼"))
    return LoopTool(name="restaurant_query", description="查询餐厅/食堂菜单(按餐次)。注:后端暂无接口,返回演示数据",
                    parameters={"type": "object", "properties": {"meal": {"type": "string"}}},
                    handler=h)
