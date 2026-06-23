from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class LoopBudget:
    max_iterations: int
    token_budget: int | None = None
    max_tool_failures: int = 3

@dataclass(frozen=True)
class LoopConfig:
    model: str
    max_tokens: int
    temperature: float
    role: Literal["main", "leaf"]
    toolset: list[str]
    budget: LoopBudget
    max_depth: int = 2
