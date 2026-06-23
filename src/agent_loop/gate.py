from __future__ import annotations

from typing import Callable, Literal, Protocol

from .messages import ToolCallReq
from .tools import LoopTool, ToolContext

Verdict = Literal["allow", "ask", "deny"]


class Gate(Protocol):
    """闸接缝:逐调用裁决 allow / ask / deny。
    循环只 act on verdict;权限/工单等内部实现在接缝外(此处桩)。"""

    def classify(self, call: ToolCallReq, tool: LoopTool, ctx: ToolContext) -> Verdict: ...


class DefaultGate:
    """默认闸:
      1. denied 谓词命中 → deny(最高优先级)
      2. is_control=True → ask(需人工确认)
      3. 其余 → allow
    denied 谓词默认 None(无人被拒);权限实现后续接入(接缝外)。
    """

    def __init__(
        self,
        denied: Callable[[ToolCallReq, LoopTool], bool] | None = None,
    ) -> None:
        self._denied = denied

    def classify(self, call: ToolCallReq, tool: LoopTool, ctx: ToolContext) -> Verdict:
        if self._denied and self._denied(call, tool):
            return "deny"
        if tool.is_control:
            return "ask"
        return "allow"
