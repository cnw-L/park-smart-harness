from __future__ import annotations
from .tools import LoopTool, ToolContext, ToolResult

def device_ctrl_tool() -> LoopTool:
    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        # 此 handler 在正常路径下不应被内联调用:
        # executor 对 is_control=True 的工具拒绝内联执行,改由 control.freeze() 冻结。
        # 只有在 control=None(配置错误)或单元测试直接调用时才会走到这里。
        return ToolResult(ok=True, content=f"[device executed] {args}")
    return LoopTool(
        name="device_ctrl",
        description="下发设备控制(不可逆,需确认)",
        parameters={
            "type": "object",
            "properties": {
                "device": {"type": "string"},
                "action": {"type": "string"},
            },
            "required": ["device", "action"],
        },
        handler=handler,
        is_control=True,
    )

def echo_tool() -> LoopTool:
    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        return ToolResult(ok=True, content=str(args.get("text", "")))
    return LoopTool(name="echo", description="回显输入 text",
                    parameters={"type": "object", "properties": {"text": {"type": "string"}},
                                "required": ["text"]}, handler=handler)

def add_tool() -> LoopTool:
    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        return ToolResult(ok=True, content=str(int(args["a"]) + int(args["b"])))
    return LoopTool(name="add", description="返回 a+b",
                    parameters={"type": "object",
                                "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                                "required": ["a", "b"]}, handler=handler)
