from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Protocol
from .messages import Message, ToolCallReq
from .pending import PendingAction
from .tools import LoopToolRegistry, ToolContext, ToolResult


@dataclass
class ToolExecOutcome:
    """归一化后的单次 tool_call 结果,供引擎消费。

    disposition 是真相来源(三态):
      "executed"              — handler 跑完(含业务层 ok=False);计入成功/失败
      "failed"                — handler 抛异常,或控制工具误达执行器(类型安全后盾);ok=False
      "awaiting_confirmation" — 由引擎(loop)通过 gate ask 路径冻结;执行器不再产生此态
                                (字面量保留以兼容 loop 的 pending_batch 路径和持久化读取)

    注意区分:
      executed + ok=False → 业务"否"(工具正常执行并返回领域错误,模型可据此调整策略)
      failed              → 基础设施/异常或类型安全后盾(控制工具不应到达执行器)
    """
    disposition: Literal["executed", "failed", "awaiting_confirmation"]
    message: Message | None        # awaiting_confirmation 时为 None;引擎填合成占位符
    ok: bool                       # executed→result.ok; failed→False; awaiting→True
    pending: PendingAction | None = None


class ToolExecutor(Protocol):
    """工具执行子系统:决定一轮内多个 tool_calls 怎么跑(串行/并行/按依赖),
    并把结果归一化成 ToolExecOutcome 列表。引擎只拿回 outcomes,自己不关心执行细节。"""

    async def execute(
        self,
        calls: list[ToolCallReq],
        registry: LoopToolRegistry,
        ctx: ToolContext,
    ) -> list[ToolExecOutcome]: ...

    async def execute_one(
        self,
        call: ToolCallReq,
        registry: LoopToolRegistry,
        ctx: ToolContext,
    ) -> ToolExecOutcome: ...


class SequentialToolExecutor:
    """最小默认实现:串行执行,output_budget 截断,异常归一化为 failed。

    S2 起,控制型工具由 Gate → loop 路由(ask 路径);执行器只处理 allow 工具。
    is_control 检查保留为类型安全后盾(§六补 invariant):若控制工具仍到达此处,
    返回 failed — 这理论上不应发生,属于配置或路由 bug。

    TODO(工具执行子系统正式版):一轮内相互独立的 tool_calls 用 asyncio.gather 并发;
    按 plan 的 depends_on 决定串/并(Gate G3)。
    """

    async def execute_one(
        self,
        call: ToolCallReq,
        registry: LoopToolRegistry,
        ctx: ToolContext,
    ) -> ToolExecOutcome:
        """执行单条 allow 工具调用,返回 executed 或 failed。

        类型安全后盾:控制工具不应到达此处(应被闸判 ask);若到达则返回 failed。
        """
        tool = registry.get(call.name)

        # ── 类型安全后盾(§六补 invariant) ──────────────────────────────────
        # 控制工具不应到达执行器;gate ask 路径已在 loop 中处理。
        # 若到达此处属于路由 bug——返回 failed(不执行 handler)。
        if tool.is_control:
            msg = Message(
                role="tool",
                content="[error] 控制工具不应到达执行器(应被闸判 ask)",
                tool_call_id=call.id,
                name=call.name,
            )
            return ToolExecOutcome(disposition="failed", message=msg, ok=False, pending=None)

        # ── 普通工具:运行 handler,异常归一化 ────────────────────────────────
        try:
            result: ToolResult = await tool.handler(call.arguments, ctx)
            # 业务层 ok=False 仍是 "executed"(工具正常返回领域错误,非基础设施崩溃)
            content = result.content if result.ok else f"[error] {result.error}"
            if tool.output_budget:
                content = tool.output_budget.apply(content)
            msg = Message(role="tool", content=content, tool_call_id=call.id, name=call.name)
            return ToolExecOutcome(disposition="executed", message=msg, ok=result.ok, pending=None)
        except Exception as exc:
            # handler 抛异常 → 基础设施/配置错误,归为 failed
            content = f"[error] {exc}"
            msg = Message(role="tool", content=content, tool_call_id=call.id, name=call.name)
            return ToolExecOutcome(disposition="failed", message=msg, ok=False, pending=None)

    async def execute(
        self,
        calls: list[ToolCallReq],
        registry: LoopToolRegistry,
        ctx: ToolContext,
    ) -> list[ToolExecOutcome]:
        """串行执行所有调用,返回 outcome 列表。每条调用委托给 execute_one。"""
        outcomes: list[ToolExecOutcome] = []
        for call in calls:
            outcomes.append(await self.execute_one(call, registry, ctx))
        return outcomes
