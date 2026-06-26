from __future__ import annotations
from uuid import uuid4
from .config import LoopConfig
from .context import ContextAssembler
from .conversation import Conversation, InMemoryConversationStore
from .gate import Gate
from .llm import ModelCaller
from .loop import run_loop
from .messages import Message
from .runcontrol import RunControl
from .tools import LoopTool, LoopToolRegistry, ToolContext, ToolResult


def make_subagent_tool(
    *,
    name: str,
    description: str,
    sub_config: LoopConfig,
    sub_registry: LoopToolRegistry,
    model_caller: ModelCaller,
    assembler: ContextAssembler | None = None,
    gate: "Gate | None" = None,
) -> LoopTool:
    """把一个隔离子循环包成父可调用的工具:隔离上下文、共享预算池、深度+1、只回吐归一化结果。

    结构性只读保证(工厂时检查):子 toolset 中不得包含任何 is_control=True 的工具。
    子 agent 是临时的、无持久化路径,不能持有不可逆操作权限。

    中圈接入:传 `assembler` 则子循环用它组装上下文(配合 `sub_config.role="leaf"` →
    固定层走 device_sub 档);不传则退化到 run_loop 默认桩(保持既有调用不变)。父身份
    (`ctx.principal`)透传给子会话,使子的知识检索按同一身份过滤。
    """
    # ── 工厂时:拒绝 toolset 中包含控制工具 ────────────────────────────────────
    for tool_name in sub_config.toolset:
        if tool_name in sub_registry._tools:
            tool = sub_registry.get(tool_name)
            if tool.is_control:
                raise ValueError(
                    f"subagent '{name}' may not include control tool '{tool_name}'"
                )

    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        # 深度上限:防止无限递归
        if ctx.depth + 1 > sub_config.max_depth:
            return ToolResult(
                ok=False, content="", error=f"max depth {sub_config.max_depth} exceeded"
            )

        # 子会话:独立、临时、不持久化到父 store
        # thread_id 用 uuid4().hex 保证唯一性(id(args) 在 GC 后可复用,易碰撞)
        sub_conv = Conversation(thread_id=f"{name}:{uuid4().hex}")
        sub_conv.append(Message(role="user", content=str(args.get("task", ""))))
        # 身份脊柱:父身份透传给子(同一用户、更窄工具集);子知识检索据此按权限过滤。
        sub_conv.principal = ctx.principal

        # 临时存储:子循环不持久化到父 store(隔离且可丢弃)
        sub_store = InMemoryConversationStore()

        # 共享父中断信号:父被中断时子在下一迭代边界也会中止,实现整棵调用树同时停止。
        # 若 ctx.run_control 为 None(如在循环外直接调用工具),则退化为独立 RunControl。
        sub_rc = ctx.run_control or RunControl()

        # 注意:不传 control=,使执行器对所有控制工具返回 disposition="failed"
        # (双重保障:工厂已拒绝 is_control 工具,此处 control=None 兜底)
        # 共享预算池:ctx.budget 传递给子,子迭代消耗父预算
        # 中圈上下文:传入则子用真组装器(固定层走 sub_config.role='leaf' → device_sub 档);
        # 不传则退化到 run_loop 默认桩(保持既有测试/调用不变)。
        # session_id 透传父会话(含空串,故不用 `or None`):子 propose 的提案记**父会话** id,
        # 父 freeze 才找得到(子 conv 是另一 uuid)。
        run_kwargs = dict(store=sub_store, run_control=sub_rc, depth=ctx.depth + 1,
                          session_id=getattr(ctx, "thread_id", ""))
        if assembler is not None:
            run_kwargs["assembler"] = assembler
        if gate is not None:                       # 同一治理闸下沉子 loop(叶子同等受查;默认 None=引擎缺省闸)
            run_kwargs["gate"] = gate
        sub_res = await run_loop(
            sub_config, sub_conv, sub_registry,
            ctx.budget, model_caller,
            **run_kwargs,
            # control 故意不传(None),executor 收到控制工具调用时返回 failed
        )

        # ── 类型化结果映射 ──────────────────────────────────────────────────────
        status = sub_res.status

        if status == "completed":
            # 子真正完成 → 父视为工具成功
            return ToolResult(ok=True, content=sub_res.final)

        # ★budget_exhausted / failed(stall 等)= 子**没完成**任务、未取得可靠结果。
        #   绝不能返 ok=True(否则父把"步数用尽时模型瞎收的尾"当成功结果 → 据此**臆造**温度/状态)。
        #   返 ok=False + 明确"无数据·别臆造",**不回传**子可能编造的 final(换成强制信号)。
        if status in {"budget_exhausted", "failed"}:
            why = "步数用尽" if status == "budget_exhausted" else (sub_res.reason or "未完成")
            return ToolResult(
                ok=False,
                content=(f"子任务未完成({why}),**未取得可靠结果**。如实告诉用户没查到/没办成,"
                         f"**绝不据此臆造温度/状态/读数等任何结果**;若是设备查无,直接回报「无此设备」。"),
                error=sub_res.reason or status,
            )

        if status == "interrupted":
            # 子被中断 → 不应增加父的连续工具失败计数
            return ToolResult(ok=False, content=sub_res.final, error="interrupted")

        # status == "awaiting_confirmation":子无控制工具,理论上不可达;防御性处理
        return ToolResult(ok=False, content=sub_res.final, error="unexpected_awaiting")

    return LoopTool(
        name=name,
        description=description,
        parameters={
            "type": "object",
            "properties": {"task": {"type": "string"}},
            "required": ["task"],
        },
        handler=handler,
    )
