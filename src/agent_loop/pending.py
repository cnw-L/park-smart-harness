from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol
from .messages import ToolCallReq


@dataclass
class PendingAction:
    """不可变的冻结控制动作记录,由 executor 在拒绝内联执行时铸造。
    携带幂等键,让后续 resume 精确执行「这一次」的动作(不重问模型)。
    handle 字段由控制子系统私用(如 control_ticket id),对 loop 不透明。"""
    tool_call_id: str
    idem_key: str
    frozen_action: dict        # 冻结时捕获的工具名 + args
    handle: Any = None         # 控制子系统私有句柄(Task 4 填充)


class ControlFreezer(Protocol):
    """把一个控制型 tool_call 冻结为 PendingAction,不执行它。
    由控制能力子系统实现(Task 4);对 loop/executor 只是协议。"""

    def freeze(self, call: ToolCallReq) -> PendingAction: ...
