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


def test_latest_for_scopes_to_thread_no_cross_user():
    """会话切片:latest_for(t) 只取本会话最近,无 → (None,None),绝不回落别会话(堵串提案)。"""
    s = ProposalStore()
    s.put(_prop(target="A", thread_id="t1"))
    s.put(_prop(target="B", thread_id="t2"))
    assert s.latest_for("t1")[1].target == "A"
    assert s.latest_for("t2")[1].target == "B"
    assert s.latest_for("tX") == (None, None)        # 无本会话提案 → 空,不串别人


class _FakeRedis:
    """最小内存 redis(decode_responses 语义):覆盖 RedisProposalStore 用到的 ~9 个方法。"""
    def __init__(self): self.kv = {}; self.sets = {}; self.lists = {}
    def set(self, k, v, ex=None): self.kv[k] = v
    def get(self, k): return self.kv.get(k)
    def delete(self, k): self.kv.pop(k, None)
    def sadd(self, k, v): self.sets.setdefault(k, set()).add(v)
    def srem(self, k, v): self.sets.get(k, set()).discard(v)
    def smembers(self, k): return set(self.sets.get(k, set()))
    def rpush(self, k, v): self.lists.setdefault(k, []).append(v)
    def lrange(self, k, a, b): return list(self.lists.get(k, []))
    def lrem(self, k, count, v):
        self.lists[k] = [x for x in self.lists.get(k, []) if x != v]


def test_redis_proposal_store_roundtrip_and_thread_scope():
    """RedisProposalStore 与内存版同接口:put/get/pop/items/latest_for + 会话切片一致。"""
    from agent_tools.proposal import RedisProposalStore
    s = RedisProposalStore(client=_FakeRedis())
    hA = s.put(_prop(target="甲", thread_id="userA"))
    s.put(_prop(target="乙", thread_id="userB"))
    assert s.get(hA).target == "甲"
    assert s.latest_for("userA")[1].target == "甲"          # 会话切片
    assert s.latest_for("userB")[1].target == "乙"
    assert s.latest_for("userX") == (None, None)            # 无本会话 → 空,不串
    assert len(s.items()) == 2
    popped = s.pop(hA)
    assert popped.target == "甲" and s.get(hA) is None
    assert s.latest_for("userA") == (None, None)            # pop 后该会话空
    assert len(s.items()) == 1                              # 索引也清了


def test_redis_store_pluggable_into_subsystem():
    """组合根可注入 store(RedisProposalStore)→ 多实例/跨重启共享提案。"""
    from agent_loop.llm import FakeModelCaller
    from agent_tools.composition import build_tool_subsystem
    from agent_tools.proposal import RedisProposalStore
    rs = RedisProposalStore(client=_FakeRedis())
    sub = build_tool_subsystem(model_caller=FakeModelCaller([]), store=rs)
    assert sub.store is rs                                  # 注入生效


def test_redis_latest_for_cleans_stale_thread_handles():
    """latest_for 遍历时清掉 TTL过期/陈旧 handle,防 thread 列表无界增长(code-review #1)。"""
    from agent_tools.proposal import RedisProposalStore
    fr = _FakeRedis()
    s = RedisProposalStore(client=fr)
    h = s.put(_prop(target="x", thread_id="t1"))
    fr.kv.pop(f"proposal:p:{h}", None)                      # 模拟 TTL 过期:提案 key 没了
    assert h in fr.lists.get("proposal:thr:t1", [])         # 陈旧 handle 仍在 thread 列表
    assert s.latest_for("t1") == (None, None)
    assert h not in fr.lists.get("proposal:thr:t1", [])     # latest_for 顺手清掉了
