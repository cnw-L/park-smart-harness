"""Phase 6:真 qwen 验证(live,gated)。

验**核心经验风险 R3**:弱 qwen 是否可靠地 (a) 委派 facility_agent (b) 从归一化结果读出 handle
(c) 调 execute_proposal 带该 handle(而非自己重打控制参数)。结构上已防危险路径(子无控制工具、
主只有 execute_proposal),故最坏是不动手、不会误执行——这里验**完成度**。

门槛:`AGENT_LOOP_LIVE_INFRA=1`(+ qwen@6008 可达)。松断言、不 gate CI。
    AGENT_LOOP_LIVE_INFRA=1 python -m pytest tests/test_agent_tools_live_qwen.py -v --timeout=300
"""
from __future__ import annotations

import asyncio
import os

import pytest

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.conversation import Boundary, InMemoryConversationStore
from agent_loop.loop import run_loop
from agent_loop.messages import Message
from agent_loop.providers import OpenAIModelCaller

from agent_context.assembler import ParkContextAssembler
from agent_context.principal import Principal

from agent_tools.composition import build_tool_subsystem

pytestmark = pytest.mark.skipif(
    os.getenv("AGENT_LOOP_LIVE_INFRA") != "1",
    reason="set AGENT_LOOP_LIVE_INFRA=1 to run live qwen test",
)


def _seed(store, tid, text):
    asyncio.run(store.commit(
        tid, [Message(role="user", content=text)],
        Boundary(status="user", turn_id="turn-0", seq=0, pending_batch=None, budget_snapshot=None)))
    return asyncio.run(store.load(tid))


def test_live_facility_propose_execute_confirm():
    model = OpenAIModelCaller(timeout=60.0)
    assembler = ParkContextAssembler(
        control_tools=frozenset({"execute_proposal"}),
        subagent_tools=frozenset({"facility_agent"}),
    )
    sub = build_tool_subsystem(model_caller=model, assembler=assembler)
    store = InMemoryConversationStore()
    conv = _seed(store, "live", "查一下3号楼空调温度,太热了帮我调低到24度")
    conv.principal = Principal(id="u", name="运维", role="物业运维", token="t")
    cfg = LoopConfig(model="chat", max_tokens=512, temperature=0.2, role="main",
                     toolset=sub.toolset, budget=LoopBudget(max_iterations=30))

    # Run 1:期望 qwen 委派 facility → 提案 → execute_proposal → 挂起
    res1 = asyncio.run(run_loop(cfg, conv, sub.registry, BudgetTracker(cfg.budget), model,
                                store=store, control=sub.control, assembler=assembler))
    assert res1.status == "awaiting_confirmation", f"期望挂起(R3),得 {res1.status}/{res1.reason}"
    assert sub.control.execute_count == 0
    assert res1.pending and res1.pending[0].frozen_action["name"]    # 冻结了某个提案动作

    # Run 2(approve):执行 → completed
    conv2 = asyncio.run(store.load("live"))
    res2 = asyncio.run(run_loop(cfg, conv2, sub.registry, BudgetTracker(cfg.budget), model,
                                store=store, control=sub.control, assembler=assembler,
                                resolution={res1.pending[0].tool_call_id: "approve"}))
    assert res2.status == "completed"
    assert sub.control.execute_count == 1
