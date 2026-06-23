from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ToolCallReq:
    id: str
    name: str
    arguments: dict


@dataclass
class Message:
    role: str                       # system|user|assistant|tool
    content: str = ""
    reasoning: str = ""             # 隐=thought(扩展思考模型),与 content 分开存(Hermes 同款)
    tool_calls: list[ToolCallReq] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None
    is_error: bool = False          # §五补:tool 结果校验失败时置 True,模型可据此重规划
