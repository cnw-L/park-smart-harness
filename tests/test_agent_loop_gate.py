"""Tests for Gate seam — classify() → allow / ask / deny (S2, TDD).

设计约束:
  - 普通工具 (is_control=False) → allow
  - 控制工具 (is_control=True) → ask
  - denied 谓词命中 → deny(谓词在 is_control 检查之前)
"""
from __future__ import annotations

import pytest

from agent_loop.gate import DefaultGate
from agent_loop.tools import LoopTool, ToolContext, ToolResult
from agent_loop.messages import ToolCallReq
from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget


# ─── 辅助 ────────────────────────────────────────────────────────────────────

def _ctx() -> ToolContext:
    return ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=10)), depth=0)


def _call(name: str, cid: str = "c1") -> ToolCallReq:
    return ToolCallReq(id=cid, name=name, arguments={})


def _tool(name: str, is_control: bool = False) -> LoopTool:
    async def h(args, ctx):
        return ToolResult(ok=True, content="ok")
    return LoopTool(name=name, description="", parameters={}, handler=h,
                    is_control=is_control)


# ─── 1. 普通工具 → allow ──────────────────────────────────────────────────────

def test_default_gate_allow_for_normal_tool():
    """is_control=False 工具 → classify 返回 "allow"。"""
    gate = DefaultGate()
    verdict = gate.classify(_call("echo"), _tool("echo"), _ctx())
    assert verdict == "allow"


# ─── 2. 控制工具 → ask ───────────────────────────────────────────────────────

def test_default_gate_ask_for_control_tool():
    """is_control=True 工具 → classify 返回 "ask"。"""
    gate = DefaultGate()
    verdict = gate.classify(_call("device_ctrl"), _tool("device_ctrl", is_control=True), _ctx())
    assert verdict == "ask"


# ─── 3. denied 谓词命中 → deny ───────────────────────────────────────────────

def test_default_gate_deny_when_predicate_matches():
    """denied 谓词按工具名命中 → classify 返回 "deny"。"""
    gate = DefaultGate(denied=lambda call, tool: tool.name == "blocked_tool")
    verdict = gate.classify(_call("blocked_tool"), _tool("blocked_tool"), _ctx())
    assert verdict == "deny"


def test_default_gate_allow_when_predicate_does_not_match():
    """denied 谓词不命中普通工具 → 仍是 "allow"(谓词不误伤)。"""
    gate = DefaultGate(denied=lambda call, tool: tool.name == "blocked_tool")
    verdict = gate.classify(_call("echo"), _tool("echo"), _ctx())
    assert verdict == "allow"


# ─── 4. denied 谓词比 is_control 检查更早 ───────────────────────────────────

def test_deny_predicate_takes_priority_over_is_control():
    """denied 谓词命中控制工具 → "deny"(而非 "ask");谓词优先级最高。"""
    gate = DefaultGate(denied=lambda call, tool: tool.name == "forbidden_ctrl")
    verdict = gate.classify(
        _call("forbidden_ctrl"),
        _tool("forbidden_ctrl", is_control=True),
        _ctx(),
    )
    assert verdict == "deny"


# ─── 5. 无 denied 谓词(默认 None)——控制工具仍是 ask ──────────────────────

def test_no_denied_predicate_control_tool_is_ask():
    """DefaultGate() 不传 denied → 控制工具还是 "ask",不会 deny 也不会 allow。"""
    gate = DefaultGate()   # denied=None
    verdict = gate.classify(
        _call("ctrl"), _tool("ctrl", is_control=True), _ctx()
    )
    assert verdict == "ask"
