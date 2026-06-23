"""Task S/§九缺口① — AuditedConversationStore 的 B/C 审计分流。

含控制动作的边界(pending_batch / resolve_pending)→ 审计必达否则上抛(fail-closed);
纯对话边界 → best-effort(审计失败不阻断)。
"""
from __future__ import annotations

import asyncio

import pytest

from agent_loop.audited_store import AuditedConversationStore
from agent_loop.conversation import Boundary, InMemoryConversationStore
from agent_loop.messages import Message


class _FailAudit:
    async def audit_boundary(self, thread_id, boundary):
        raise RuntimeError("PG down")


class _OkAudit:
    def __init__(self):
        self.calls = []

    async def audit_boundary(self, thread_id, boundary):
        self.calls.append(boundary.seq)


def _ctrl(seq):
    return Boundary(status="awaiting_confirmation", turn_id=f"t{seq}", seq=seq,
                    pending_batch=[{"tool_call_id": "c1"}])


def _dlg(seq):
    return Boundary(status="iteration", turn_id=f"t{seq}", seq=seq)


def test_dialogue_boundary_best_effort():
    """纯对话 boundary + 审计失败 → 不抛(B,best-effort)。"""
    s = AuditedConversationStore(InMemoryConversationStore(), _FailAudit())
    asyncio.run(s.commit("t", [Message(role="user", content="hi")], _dlg(1)))   # 不抛即通过


def test_control_boundary_mandatory_raises():
    """含控制(pending_batch)+ 审计失败 → 上抛(C,fail-closed)。"""
    s = AuditedConversationStore(InMemoryConversationStore(), _FailAudit())
    with pytest.raises(Exception):
        asyncio.run(s.commit("t", [Message(role="assistant", content="")], _ctrl(1)))


def test_resolve_pending_mandatory_raises():
    """resolve_pending(控制已解析)+ 审计失败 → 上抛(C)。"""
    s = AuditedConversationStore(InMemoryConversationStore(), _FailAudit())
    with pytest.raises(Exception):
        asyncio.run(s.resolve_pending("t", {}, _dlg(2)))


def test_control_boundary_audited_when_ok():
    a = _OkAudit()
    s = AuditedConversationStore(InMemoryConversationStore(), a)
    asyncio.run(s.commit("t", [Message(role="assistant", content="")], _ctrl(1)))
    assert 1 in a.calls
