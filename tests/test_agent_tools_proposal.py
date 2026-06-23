"""Phase 0:ControlProposal + ProposalStore(纯数据,无 loop)。"""
from __future__ import annotations

from agent_tools.proposal import ControlProposal, ProposalStore


def _prop(**kw):
    base = dict(target="3号楼空调", action="set_temp", params={"temp": 24}, human="设到24℃")
    base.update(kw)
    return ControlProposal(**base)


def test_put_generates_handle_and_get_roundtrips():
    store = ProposalStore()
    h = store.put(_prop())
    assert h                                         # 非空 handle
    got = store.get(h)
    assert got is not None
    assert got.handle == h
    assert got.action == "set_temp" and got.params == {"temp": 24}
    assert got.target == "3号楼空调"


def test_put_defensive_copies_params():
    """外部事后改原 params dict,不应影响已登记的提案(防篡改,仿 freeze 的 dict(args))。"""
    store = ProposalStore()
    p = {"temp": 24}
    h = store.put(_prop(params=p))
    p["temp"] = 18                                   # 篡改原 dict
    assert store.get(h).params == {"temp": 24}       # 已存不变


def test_unknown_handle_returns_none():
    assert ProposalStore().get("nope") is None


def test_pop_removes():
    store = ProposalStore()
    h = store.put(_prop())
    assert store.pop(h) is not None
    assert store.get(h) is None                      # 取出后没了
    assert store.pop(h) is None                      # 再 pop 安全


def test_explicit_handle_preserved():
    """已带 handle 的提案再 put,沿用该 handle(不重新生成)。"""
    store = ProposalStore()
    h = store.put(_prop(handle="fixed-1"))
    assert h == "fixed-1" and store.get("fixed-1") is not None
