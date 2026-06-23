"""verify 接缝:在结果边界校验 allow-executed 结果的业务正确性(§二、§五补)。

Verifier 不是循环闸——只产出裁决:
  business_ok=True  → 结果正常传递给模型;
  business_ok=False → loop 将 tool 结果标 is_error=True 并前缀 [verify-failed],
                      模型看见错误结果后自然触发重规划。

verify 失败 ≠ 基础设施失败:不计入 failures 计数,不触发熔断。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .dispatch import ToolExecOutcome
from .messages import ToolCallReq
from .tools import LoopTool, ToolContext


@dataclass
class VerifyVerdict:
    business_ok: bool
    note: str = ""


class Verifier(Protocol):
    """verify 接缝:在结果边界校验某次 allow 执行的结果(每能力的 validation_policy,规则优先)。
    不是循环闸——只产出裁决;business_ok=False → loop 把结果标 is_error 让模型看见 → 自然重规划。"""

    async def verify(
        self,
        call: ToolCallReq,
        tool: LoopTool,
        outcome: ToolExecOutcome,
        ctx: ToolContext,
    ) -> VerifyVerdict: ...


class NullVerifier:
    """默认放行:business_ok = 执行结果的 ok(接缝就位,真实 validation_policy 后续接入)。"""

    async def verify(
        self,
        call: ToolCallReq,
        tool: LoopTool,
        outcome: ToolExecOutcome,
        ctx: ToolContext,
    ) -> VerifyVerdict:
        return VerifyVerdict(business_ok=outcome.ok)
