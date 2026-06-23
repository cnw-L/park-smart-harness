"""propose_control 是只读 grounding 闸 → 可进只读子 agent(grounding 行为见 test_agent_tools_grounding)。"""
from __future__ import annotations

import pytest

from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.llm import FakeModelCaller
from agent_loop.stubs import device_ctrl_tool
from agent_loop.subagent import make_subagent_tool
from agent_loop.tools import LoopToolRegistry

from agent_tools.backend import FakeBackendClient
from agent_tools.propose import make_propose_control_tool
from agent_tools.proposal import ProposalStore


def _cfg(toolset):
    return LoopConfig(model="x", max_tokens=100, temperature=0.0, role="leaf",
                      toolset=toolset, budget=LoopBudget(max_iterations=5))


def test_propose_control_is_read_only():
    """grounding 只查字典+登记,不写后端 → is_control False(否则进不了子 agent)。"""
    assert make_propose_control_tool(ProposalStore(), FakeBackendClient()).is_control is False


def test_subagent_accepts_propose_control_but_rejects_real_control():
    """回归守卫(直击 subagent.py:32-38):propose_control 非控制→工厂不抛;真控制工具→抛。"""
    reg = LoopToolRegistry()
    reg.register(make_propose_control_tool(ProposalStore(), FakeBackendClient()))
    make_subagent_tool(name="sub", description="d", sub_config=_cfg(["propose_control"]),
                       sub_registry=reg, model_caller=FakeModelCaller([]))   # 不抛

    reg2 = LoopToolRegistry(); reg2.register(device_ctrl_tool())
    with pytest.raises(ValueError):
        make_subagent_tool(name="sub2", description="d", sub_config=_cfg(["device_ctrl"]),
                           sub_registry=reg2, model_caller=FakeModelCaller([]))
