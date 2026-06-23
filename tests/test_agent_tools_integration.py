"""Phase 5:全循环集成(确定性)——头条场景端到端,设计验证线。

facility_agent(查温 + 登记提案)→ 主见 handle → execute_proposal(handle)→ ask → 挂起 →
resume approve → **执行提案的精确动作(set_temp 24,非模型乱打)** → completed;+ reject 路径。
复用 test_agent_loop_integration 的 _commit_user_seed + 双 run_loop suspend/resume 模式。
"""
from __future__ import annotations

import asyncio

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.conversation import Boundary, InMemoryConversationStore
from agent_loop.llm import ModelTurn
from agent_loop.loop import run_loop
from agent_loop.messages import Message, ToolCallReq

from agent_context.principal import Principal

from agent_tools.composition import build_tool_subsystem

# 子 loop 现受同一 CatalogGate(deny-first)→ 会话需带能力码 principal(身份脊柱透传给子)。
_ADMIN = Principal(id="u", name="x", role="管理员",
                   permissions=("device:read", "device:control", "record:read",
                                "life:read", "knowledge:read"))


def _commit_user_seed(store, thread_id, text):
    asyncio.run(store.commit(
        thread_id, [Message(role="user", content=text)],
        Boundary(status="user", turn_id="turn-0", seq=0, pending_batch=None, budget_snapshot=None)))
    conv = asyncio.run(store.load(thread_id))
    conv.principal = _ADMIN
    return conv


class _SubRelay:
    """facility 子模型:device_status → propose_control → 末轮把 propose 结果(含 handle)当 final。"""
    def __init__(self):
        self._i = 0

    async def __call__(self, config, messages, tool_schemas):
        scripted = [
            ModelTurn(content="", tool_calls=[ToolCallReq(
                id="d1", name="device_status", arguments={"device": "3号楼空调"})]),
            ModelTurn(content="", tool_calls=[ToolCallReq(
                id="p1", name="propose_control",
                arguments={"target": "3号楼空调", "point_type_id": "3700", "device_id": "ac-3f-2",
                           "param": "温度设定", "value": "24"})]),
        ]
        if self._i < len(scripted):
            t = scripted[self._i]; self._i += 1; return t
        last = next((m for m in reversed(messages) if m.role == "tool"), None)
        return ModelTurn(content=(last.content if last else "完成"), tool_calls=[])


class _MainHandleAware:
    """主模型(包1 后):① 委派 facility_agent;② **不读 handle**,直接 execute_proposal(无参数)
    → freeze 取最近一条提案;③ 完成。验证 handle 不经模型的新流程。"""
    def __init__(self):
        self.phase = 0

    async def __call__(self, config, messages, tool_schemas):
        if self.phase == 0:
            self.phase = 1
            return ModelTurn(content="", tool_calls=[ToolCallReq(
                id="f1", name="facility_agent",
                arguments={"task": "查3号楼空调温度,太热就提案调到24度"})])
        if self.phase == 1:
            self.phase = 2
            return ModelTurn(content="", tool_calls=[ToolCallReq(
                id="e1", name="execute_proposal", arguments={})])  # ★无 handle:取最近未消解提案
        return ModelTurn(content="已完成:3号楼空调已调到24℃。", tool_calls=[])


def _cfg(toolset):
    return LoopConfig(model="big", max_tokens=200, temperature=0.0, role="main",
                      toolset=toolset, budget=LoopBudget(max_iterations=20))


def test_full_chain_propose_execute_confirm_executes_proposal_action():
    store = InMemoryConversationStore()
    conv = _commit_user_seed(store, "tm1", "3号楼空调太热,调到24度")
    sub = build_tool_subsystem(model_caller=_SubRelay())
    main = _MainHandleAware()
    cfg = _cfg(sub.toolset)

    # ── Run 1:facility → execute_proposal → 挂起 ──
    res1 = asyncio.run(run_loop(cfg, conv, sub.registry, BudgetTracker(cfg.budget), main,
                                store=store, control=sub.control))
    assert res1.status == "awaiting_confirmation"
    assert sub.control.execute_count == 0                          # 挂起阶段不执行
    # 冻结的是**提案的**精确动作(从提案取、非模型重打)——设计最硬需求,全循环级证明
    assert res1.pending and len(res1.pending) == 1
    fa = res1.pending[0].frozen_action
    assert fa["name"] == "deviceCtrl" and fa["arguments"].get("paramValue") == "24"  # grounded、非模型乱打

    # ── Run 2(approve):执行提案动作 → completed ──
    conv2 = asyncio.run(store.load("tm1")); conv2.principal = _ADMIN
    res2 = asyncio.run(run_loop(cfg, conv2, sub.registry, BudgetTracker(cfg.budget), main,
                                store=store, control=sub.control,
                                resolution={res1.pending[0].tool_call_id: "approve"}))
    assert res2.status == "completed"
    assert sub.control.execute_count == 1                          # 恰执行一次
    loaded = asyncio.run(store.load("tm1"))
    executed = [m for m in loaded.messages
                if m.role == "tool" and "executed" in (m.content or "").lower()]
    assert executed and "deviceCtrl" in executed[-1].content and "paramValue" in executed[-1].content
    # 提案已被消费(pop-on-resolve)
    assert len(sub.store._store) == 0


def test_reject_path_does_not_execute():
    store = InMemoryConversationStore()
    conv = _commit_user_seed(store, "tm2", "3号楼空调太热,调到24度")
    sub = build_tool_subsystem(model_caller=_SubRelay())
    main = _MainHandleAware()
    cfg = _cfg(sub.toolset)

    res1 = asyncio.run(run_loop(cfg, conv, sub.registry, BudgetTracker(cfg.budget), main,
                                store=store, control=sub.control))
    assert res1.status == "awaiting_confirmation"

    conv2 = asyncio.run(store.load("tm2")); conv2.principal = _ADMIN
    res2 = asyncio.run(run_loop(cfg, conv2, sub.registry, BudgetTracker(cfg.budget), main,
                                store=store, control=sub.control,
                                resolution={res1.pending[0].tool_call_id: "reject"}))
    assert res2.status == "completed"
    assert sub.control.execute_count == 0                          # 拒绝不执行
    loaded = asyncio.run(store.load("tm2"))
    ctl = [m for m in loaded.messages if m.role == "tool" and m.tool_call_id == "e1"]
    assert ctl and "rejected" in ctl[-1].content.lower()
