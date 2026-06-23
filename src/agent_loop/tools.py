from __future__ import annotations
from dataclasses import dataclass
from typing import Awaitable, Callable, TYPE_CHECKING
from .budget import BudgetTracker

if TYPE_CHECKING:
    from .runcontrol import RunControl

@dataclass
class ToolResult:
    ok: bool
    content: str
    error: str | None = None

@dataclass(frozen=True)
class OutputBudget:
    max_chars: int
    def apply(self, text: str) -> str:
        return text if len(text) <= self.max_chars else text[: self.max_chars] + "…"

@dataclass
class ToolContext:
    budget: BudgetTracker
    depth: int
    run_control: "RunControl | None" = None  # 父循环的中断信号;子 agent 共享此信号实现级联中断
    principal: object | None = None           # 身份脊柱(engine-opaque):知识层透传权限、闸 deny 读

ToolHandler = Callable[[dict, "ToolContext"], Awaitable["ToolResult"]]

@dataclass
class LoopTool:
    name: str
    description: str
    parameters: dict
    handler: ToolHandler
    output_budget: OutputBudget | None = None
    is_control: bool = False   # 控制型工具标记:executor 拒绝内联执行,转为冻结 PendingAction
    def schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": self.parameters}}

class LoopToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, LoopTool] = {}
    def register(self, tool: LoopTool) -> None:
        self._tools[tool.name] = tool
    def get(self, name: str) -> LoopTool:
        return self._tools[name]
    def schemas(self, toolset: list[str]) -> list[dict]:
        return [self._tools[n].schema() for n in toolset if n in self._tools]
