"""`execute_proposal` 工具:主会话发起执行此前登记的控制提案。

`is_control=True` → gate 判 `ask` → loop 调 `ProposalControlCapability.freeze`(把提案还原成
精确动作)→ 挂起确认 → 用户确认后执行。

★handle 不经模型(M5 铁律:模型不写治理对象)。**主模型不传 handle**——freeze 取 store 里
**最近一条未消解提案**;handle 只在确认卡(frozen_action)+ /api/confirm(tool_call_id)round-trip,
走前端不走模型(对齐行业 operation_ticket_id 范式,根治 qwen 抄错/编造 handle)。

handler 是防御桩:正常路径下 gate 拦在 freeze 前,不会内联走到这里(双保险:executor 对
is_control 也拒绝内联)。
"""
from __future__ import annotations

from agent_loop.tools import LoopTool, ToolContext, ToolResult


def make_execute_proposal_tool() -> LoopTool:
    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        return ToolResult(ok=False, content="",
                          error="execute_proposal must route through the confirmation gate")

    return LoopTool(
        name="execute_proposal",
        description=(
            "发起执行**刚登记、尚未确认**的设备控制提案(不可逆)。"
            "**你不需要传 handle/提案号**——系统自动取最近一条提案;**也不要在文本里反问「是否确认」**:"
            "调用本工具就会自动弹确认卡给用户,用户在卡上确认后才真正下发。"
            "用法:propose_control 登记提案后,直接调用 execute_proposal 即可(无参数)。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "handle": {"type": "string",
                           "description": "可选,通常不填;留空=执行最近登记的提案"},
            },
        },
        handler=handler,
        is_control=True,
    )
