"""test_agent_loop_audited_store.py — 离线测试 AuditedConversationStore (A1).

完全离线:InMemoryConversationStore + FakeAudit,不触碰任何真实 I/O。
**无** pytestmark / AGENT_LOOP_LIVE_INFRA 门槛 — CI 必跑。

覆盖:
  1. commit → inner 已提交 + FakeAudit 记录(thread_id / seq 匹配)
  2. resolve_pending → audit 记录 resolution 边界
  3. load / latest_boundary → 无审计调用(读不审计)
  4. best-effort:audit.audit_boundary 抛出 → commit 仍成功,inner 提交完整,不上抛
  5. drop-in:AuditedConversationStore 作为 run_loop store= 参数,跑完一轮,FakeAudit 记录迭代边界
"""
from __future__ import annotations

import asyncio
import logging

import pytest

from agent_loop.audited_store import AuditedConversationStore
from agent_loop.conversation import Boundary, InMemoryConversationStore
from agent_loop.messages import Message


# ---------------------------------------------------------------------------
# FakeAudit
# ---------------------------------------------------------------------------

class FakeAudit:
    """记录所有 audit_boundary 调用;可选配置为抛出。"""

    def __init__(self, *, raise_on_call: bool = False) -> None:
        self._raise = raise_on_call
        self.calls: list[tuple[str, Boundary]] = []  # [(thread_id, boundary), ...]

    async def audit_boundary(self, thread_id: str, boundary: Boundary) -> None:
        if self._raise:
            raise RuntimeError("fake audit failure")
        self.calls.append((thread_id, boundary))


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def run(coro):
    return asyncio.run(coro)


def _b(seq: int = 1, status: str = "iteration") -> Boundary:
    return Boundary(status=status, turn_id=f"turn-{seq}", seq=seq)


def _msg(content: str = "hi") -> Message:
    return Message(role="assistant", content=content)


def _user_msg(content: str = "user") -> Message:
    return Message(role="user", content=content)


# ---------------------------------------------------------------------------
# 1. commit → inner 已提交 + FakeAudit 记录
# ---------------------------------------------------------------------------

def test_commit_writes_inner_and_audits():
    inner = InMemoryConversationStore()
    audit = FakeAudit()
    store = AuditedConversationStore(inner, audit)

    b = _b(seq=1)
    msgs = [_msg("hello")]
    run(store.commit("t1", msgs, b))

    # inner 已提交:load 可见消息
    conv = run(store.load("t1"))
    assert len(conv.messages) == 1
    assert conv.messages[0].content == "hello"

    # audit 记录了一条,thread_id + seq 匹配
    assert len(audit.calls) == 1
    tid, recorded = audit.calls[0]
    assert tid == "t1"
    assert recorded.seq == 1


def test_commit_multiple_boundaries_all_audited():
    inner = InMemoryConversationStore()
    audit = FakeAudit()
    store = AuditedConversationStore(inner, audit)

    run(store.commit("t2", [_msg("a")], _b(seq=1)))
    run(store.commit("t2", [_msg("b")], _b(seq=2)))

    assert len(audit.calls) == 2
    seqs = [b.seq for _, b in audit.calls]
    assert seqs == [1, 2]


# ---------------------------------------------------------------------------
# 2. resolve_pending → audit 记录 resolution 边界
# ---------------------------------------------------------------------------

def test_resolve_pending_audits_resolution_boundary():
    """先 commit 一个 awaiting_confirmation 边界,再 resolve_pending → audit 记录。"""
    inner = InMemoryConversationStore()
    audit = FakeAudit()
    store = AuditedConversationStore(inner, audit)

    # step1: commit 挂起边界(含占位符 tool 消息)
    suspend_b = _b(seq=1, status="awaiting_confirmation")
    placeholder = Message(role="tool", content="pending", tool_call_id="tc-1")
    run(store.commit("t3", [_msg("assistant"), placeholder], suspend_b))

    # step2: resolve_pending → 替换占位符 + 新边界
    resolved_msg = Message(role="tool", content="executed", tool_call_id="tc-1")
    resume_b = _b(seq=2, status="iteration")
    run(store.resolve_pending("t3", {"tc-1": resolved_msg}, resume_b))

    # audit 应有两条:suspend + resume
    assert len(audit.calls) == 2
    _, rb = audit.calls[1]
    assert rb.seq == 2
    assert rb.status == "iteration"


# ---------------------------------------------------------------------------
# 3. load / latest_boundary → 无审计调用
# ---------------------------------------------------------------------------

def test_load_does_not_audit():
    inner = InMemoryConversationStore()
    audit = FakeAudit()
    store = AuditedConversationStore(inner, audit)

    # 先 commit 一个边界(会产生 1 次 audit 调用)
    run(store.commit("t4", [_msg("x")], _b(seq=1)))
    assert len(audit.calls) == 1

    # 再 load → 不应增加 audit 调用
    run(store.load("t4"))
    assert len(audit.calls) == 1


def test_latest_boundary_does_not_audit():
    inner = InMemoryConversationStore()
    audit = FakeAudit()
    store = AuditedConversationStore(inner, audit)

    run(store.commit("t5", [_msg("y")], _b(seq=1)))
    calls_before = len(audit.calls)

    run(store.latest_boundary("t5"))
    assert len(audit.calls) == calls_before  # 无新增


# ---------------------------------------------------------------------------
# 4. best-effort:audit 抛出 → commit 仍成功,不上抛
# ---------------------------------------------------------------------------

def test_commit_succeeds_when_audit_raises(caplog):
    inner = InMemoryConversationStore()
    audit = FakeAudit(raise_on_call=True)
    store = AuditedConversationStore(inner, audit)

    # audit 会抛,但 commit 不应传播异常
    with caplog.at_level(logging.WARNING, logger="agent_loop.audited_store"):
        run(store.commit("t6", [_msg("safe")], _b(seq=1)))

    # inner 提交完整:load 可见消息
    conv = run(store.load("t6"))
    assert len(conv.messages) == 1
    assert conv.messages[0].content == "safe"

    # warning 日志已发出
    assert any("审计失败" in r.message for r in caplog.records)


def test_commit_exception_not_propagated_when_audit_raises():
    """明确断言:不抛异常。"""
    inner = InMemoryConversationStore()
    audit = FakeAudit(raise_on_call=True)
    store = AuditedConversationStore(inner, audit)
    # 应无异常
    run(store.commit("t7", [_msg("ok")], _b(seq=1)))


# ---------------------------------------------------------------------------
# 5. drop-in:在 run_loop 中使用 AuditedConversationStore
# ---------------------------------------------------------------------------

def test_drop_in_run_loop_records_audit_boundaries():
    """AuditedConversationStore 作为 run_loop store=参数,跑完一轮。

    用 FakeModelCaller(echo)验证:循环正常完成,FakeAudit 至少记录了一条迭代边界。
    """
    from agent_loop.loop import run_loop
    from agent_loop.config import LoopConfig, LoopBudget
    from agent_loop.conversation import Conversation
    from agent_loop.tools import LoopToolRegistry
    from agent_loop.budget import BudgetTracker
    from agent_loop.llm import ModelTurn, FakeModelCaller
    from agent_loop.stubs import echo_tool
    from agent_loop.messages import ToolCallReq

    # FakeModelCaller:第一轮返回 echo 工具调用;第二轮返回 "done"(completed)
    seq_counter = {"n": 0}

    def fake_model(config, prompt, schemas):
        seq_counter["n"] += 1
        n = seq_counter["n"]
        if n == 1:
            # 第一轮:调用 echo
            return ModelTurn(
                content="",
                reasoning="",
                tool_calls=[ToolCallReq(id="tc-1", name="echo", arguments={"text": "ping"})],
            )
        # 后续轮次:直接完成
        return ModelTurn(content="done", reasoning="", tool_calls=[])

    async def _fake_model_caller(config, prompt, schemas):
        return fake_model(config, prompt, schemas)

    inner = InMemoryConversationStore()
    audit = FakeAudit()
    store = AuditedConversationStore(inner, audit)

    # 先 commit user 消息(服务端职责)
    user_b = Boundary(status="user", turn_id="turn-0", seq=0)
    asyncio.run(inner.commit(
        "drop-in", [Message(role="user", content="hi")], user_b,
    ))
    conv = asyncio.run(inner.load("drop-in"))

    reg = LoopToolRegistry()
    reg.register(echo_tool())

    cfg = LoopConfig(
        model="fake",
        max_tokens=200,
        temperature=0.0,
        role="main",
        toolset=["echo"],
        budget=LoopBudget(max_iterations=5),
    )
    budget = BudgetTracker(cfg.budget)

    result = asyncio.run(run_loop(
        cfg, conv, reg, budget, _fake_model_caller,
        store=store,
    ))

    # 循环正常完成
    assert result.status in ("completed", "iteration")

    # FakeAudit 至少记录了一条迭代边界
    assert len(audit.calls) >= 1
    statuses = {b.status for _, b in audit.calls}
    # 跳过 seq=0 的 user 边界;只看引擎产生的边界
    engine_calls = [(tid, b) for tid, b in audit.calls if b.status != "user"]
    assert len(engine_calls) >= 1
