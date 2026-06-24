"""回归:demo 的 plan 引擎元工具必须进 catalog 受治,否则 deny-first 闸把它拒掉(code-review HIGH bug)。"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget
from agent_loop.messages import ToolCallReq
from agent_loop.tools import ToolContext


def _load_demo():
    # 置空(非 pop):demo 现在 load_dotenv,pop 会被 .env 重新填上 → 显式空串让 _build_backend 走 Fake。
    os.environ["ASSISTANT_PROJECT_API_BASE_URL"] = ""
    os.environ["HARNESS_RAG_LIVE"] = "0"   # 单测离线:RAG 默认已改"接真库",显式退 Fake 不连 milvus
    path = Path(__file__).resolve().parents[1] / "scripts" / "demo_server.py"
    spec = importlib.util.spec_from_file_location("demo_server_under_test", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_demo_plan_tool_is_governed_not_denied():
    m = _load_demo()
    conv_plan = type("P", (), {})()                 # 占位 plan(只验登记/裁决,不执行)
    reg = m.build_registry(conv_plan)
    ctx = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=5)), depth=0,
                      principal=m._principal())
    # plan 进了 catalog(统一治理)+ 在执行注册表里
    assert m._rt.subsystem.catalog.find("plan") is not None
    assert "plan" in reg._tools
    # demo principal 有 plan 码 → gate 放行(而非 deny-first 拒掉)
    verdict = m._rt.subsystem.gate.classify(ToolCallReq(id="x", name="plan", arguments={}),
                                            reg.get("plan"), ctx)
    assert verdict == "allow"


def test_demo_principal_has_plan_code():
    m = _load_demo()
    # 每个 demo 身份都带 plan 码(plan 是会话级基础设施,所有身份默认可用)
    for principal in m._PERSONAS.values():
        assert m._PLAN_CODE in principal.permissions


def _fake_res(status: str):
    return type("R", (), {"status": status})()


def test_gc_clears_abandoned_proposal_on_terminal():
    """回归(code-review):撤 auto-chain + execute-latest 后,本轮 propose 没 execute 的提案若残留,
    下一轮 execute-latest 会误取这条陈旧提案 → 终态必须清掉。"""
    m = _load_demo()
    from agent_tools.proposal import ControlProposal
    store = m._rt.subsystem.store
    store.put(ControlProposal(target="空调机组106", action="deviceCtrl", params={"deviceId": "x"}))
    assert len(store.items()) == 1
    n = m._gc_abandoned_proposals(_fake_res("completed"))     # 终态 → 清
    assert n == 1 and store.items() == []


def test_gc_keeps_pending_while_awaiting_confirmation():
    """awaiting_confirmation 时**不清**——那条提案正等用户确认,生命周期归 resolve/confirm。"""
    m = _load_demo()
    from agent_tools.proposal import ControlProposal
    store = m._rt.subsystem.store
    for _h, _p in list(store.items()):                        # 先清干净(模块单例跨测共享)
        store.pop(_h)
    store.put(ControlProposal(target="空调机组106", action="deviceCtrl", params={"deviceId": "x"}))
    n = m._gc_abandoned_proposals(_fake_res("awaiting_confirmation"))
    assert n == 0 and len(store.items()) == 1                 # 等确认的提案保住


def test_control_flow_has_no_duplicate_confirmation_noise():
    """回归(用户「重复确认」):控制流程对外只剩一张确认卡——
    ① propose_control **不出** done_what 进展行(它只是 grounding 内部准备);
    ② 模型在 execute_proposal 轮里的文本反问(请确认是否继续)**不出** say 步(卡片即唯一确认入口)。"""
    m = _load_demo()
    from agent_loop.messages import Message, ToolCallReq
    # ① propose_control 不合成进展行
    assert m._synthesize_done_what("propose_control", {"device": "空调机组106"},
                                   "控制提案已登记(对「空调机组106」温度控制=24)", False) is None
    # ② execute_proposal 轮的模型叙述不出 say
    msg = Message(role="assistant", content="控制提案已登记并发起执行,请确认是否继续执行该控制指令。",
                  tool_calls=[ToolCallReq(id="e1", name="execute_proposal", arguments={})])
    kinds = [ev.get("kind") for ev in m._extract_internal_events(msg, "")]
    assert "say" not in kinds and "tool_call" in kinds       # 文本反问被吞、工具调用仍在(过程可见)
    # 对照:普通查询轮的叙述照常出 say(不误伤)
    q = Message(role="assistant", content="正在为你查询工单。",
                tool_calls=[ToolCallReq(id="r1", name="record_query", arguments={"kind": "工单"})])
    assert "say" in [ev.get("kind") for ev in m._extract_internal_events(q, "")]
