"""Phase 2:ProposalControlCapability + execute_proposal(单元,无 loop)。"""
from __future__ import annotations

import asyncio

from agent_loop.messages import ToolCallReq

from agent_tools.execute_proposal import make_execute_proposal_tool
from agent_tools.proposal import ControlProposal, ProposalStore
from agent_tools.proposal_control import ProposalControlCapability


def _seed(store) -> str:
    return store.put(ControlProposal(target="3号楼空调", action="set_temp",
                                     params={"temp": 24}, human="设到24℃"))


def _call(handle, cid="c1"):
    return ToolCallReq(id=cid, name="execute_proposal", arguments={"handle": handle})


def test_execute_proposal_tool_is_control():
    assert make_execute_proposal_tool().is_control is True


def test_freeze_uses_proposal_params_not_model_typed():
    """设计最硬需求:frozen_action 的参数来自**提案**,不是 execute_proposal(handle=…) 这层调用。"""
    store = ProposalStore(); cap = ProposalControlCapability(store)
    h = _seed(store)
    pending = cap.freeze(_call(h))
    assert pending.frozen_action["name"] == "set_temp"
    assert pending.frozen_action["arguments"] == {"temp": 24}     # 精确参数保真
    assert pending.handle == h


def test_approve_executes_once_and_is_idempotent():
    store = ProposalStore(); cap = ProposalControlCapability(store)
    pending = cap.freeze(_call(_seed(store)))
    r1 = asyncio.run(cap.resolve(pending, "approve"))
    assert r1.ok and "set_temp" in r1.content and cap.execute_count == 1
    r2 = asyncio.run(cap.resolve(pending, "approve"))            # 同 idem_key 重入
    assert r2 is r1 or r2.content == r1.content
    assert cap.execute_count == 1                                # 不重发


def test_reject_does_not_execute():
    store = ProposalStore(); cap = ProposalControlCapability(store)
    pending = cap.freeze(_call(_seed(store)))
    r = asyncio.run(cap.resolve(pending, "reject"))
    assert r.ok and "rejected" in r.content and cap.execute_count == 0


def test_unknown_handle_yields_sentinel_and_fails_safely():
    store = ProposalStore(); cap = ProposalControlCapability(store)
    pending = cap.freeze(_call("does-not-exist"))               # freeze 不抛
    r = asyncio.run(cap.resolve(pending, "approve"))
    assert r.ok is False and cap.execute_count == 0             # 不执行
