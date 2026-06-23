from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol
from .config import LoopConfig
from .messages import Message, ToolCallReq

@dataclass
class ModelTurn:
    content: str
    tool_calls: list[ToolCallReq] = field(default_factory=list)
    usage_tokens: int = 0
    reasoning: str = ""

class ModelCaller(Protocol):
    async def __call__(self, config: LoopConfig | None,
                       messages: list[Message], tool_schemas: list[dict]) -> ModelTurn: ...

class FakeModelCaller:
    """测试用:按调用次序返回脚本化 ModelTurn。"""
    def __init__(self, turns: list[ModelTurn]) -> None:
        self._turns = list(turns); self._i = 0
    async def __call__(self, config, messages, tool_schemas) -> ModelTurn:
        turn = self._turns[self._i]; self._i += 1
        return turn
