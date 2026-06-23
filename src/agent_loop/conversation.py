from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol
from .messages import Message
from .plan import PlanState, derive_plan


@dataclass
class Boundary:
    """Marks the end of one committed iteration in the message log.

    Every successful commit atomically appends a batch of messages and one
    Boundary.  The store's load() reconstructs the conversation only up to the
    last Boundary — anything written after the last Boundary (torn tail) is
    silently discarded.
    """
    status: str                        # "iteration" | "completed" | "awaiting_confirmation" | "failed"
    turn_id: str
    seq: int                           # monotonic boundary index (1-based)
    pending_batch: list | None = None  # opaque pending-action records (awaiting_confirmation)
    budget_snapshot: dict | None = None


@dataclass
class Conversation:
    thread_id: str
    messages: list[Message] = field(default_factory=list)
    plan: PlanState = field(default_factory=PlanState)
    # 身份脊柱(engine-opaque):由调用方在会话入口解析后 set,不从消息日志加载、不持久化。
    # 引擎只把它透到 ToolContext;中圈解释(记忆层渲染/知识层透传/闸 deny)。
    principal: object | None = None

    def append(self, msg: Message) -> None:
        """Append a message to the in-memory conversation (used by loop internals)."""
        self.messages.append(msg)


class ConversationStore(Protocol):
    async def load(self, thread_id: str) -> Conversation: ...
    async def commit(
        self,
        thread_id: str,
        new_messages: list[Message],
        boundary: Boundary,
    ) -> None: ...
    async def latest_boundary(self, thread_id: str) -> Boundary | None: ...
    async def resolve_pending(
        self,
        thread_id: str,
        resolved: dict[str, Message],
        boundary: Boundary,
    ) -> None: ...
    # 生产(append-only 审计日志)会 append 一条 resolution-event;
    # in-memory 原型做原地替换以简化测试。


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------

@dataclass
class _ThreadState:
    """Internal per-thread committed state.

    committed_messages: messages up to and including the last boundary.
    uncommitted_tail:   messages written without a following boundary
                        (torn tail; populated only by _append_uncommitted test seam).
    boundaries:         ordered list of committed Boundary objects.
    """
    committed_messages: list[Message] = field(default_factory=list)
    uncommitted_tail: list[Message] = field(default_factory=list)
    boundaries: list[Boundary] = field(default_factory=list)


class InMemoryConversationStore:
    """Dict-backed conversation store with atomic commit semantics.

    Atomicity (in-memory): commit() mutates committed_messages and boundaries
    together in a single synchronous step inside the coroutine — no await
    between them — so no interleaving is possible in a cooperative async loop.

    Tail-discard seam: _append_uncommitted() writes to uncommitted_tail without
    recording a boundary, simulating a crash between message-write and
    boundary-write.  load() ignores uncommitted_tail entirely, returning only
    committed_messages.  This seam is intentionally NOT part of the public
    ConversationStore Protocol.
    """

    def __init__(self) -> None:
        self._threads: dict[str, _ThreadState] = {}

    def _get_or_create(self, thread_id: str) -> _ThreadState:
        if thread_id not in self._threads:
            self._threads[thread_id] = _ThreadState()
        return self._threads[thread_id]

    async def load(self, thread_id: str) -> Conversation:
        """Return a Conversation reconstructed up to the last committed boundary.

        Messages in the uncommitted tail (written after the last boundary) are
        discarded — they represent a torn/in-flight iteration.
        """
        state = self._threads.get(thread_id)
        if state is None:
            return Conversation(thread_id=thread_id)
        # Return a copy of committed messages only (tail is invisible)
        committed = list(state.committed_messages)
        conv = Conversation(
            thread_id=thread_id,
            messages=committed,
        )
        # 从消息日志派生 plan 投影（Claude TodoWrite 式：取最近一条 plan 调用快照）
        conv.plan = derive_plan(committed)
        return conv

    async def commit(
        self,
        thread_id: str,
        new_messages: list[Message],
        boundary: Boundary,
    ) -> None:
        """Atomically append new_messages and record boundary.

        After this call, load() returns all previously committed messages plus
        new_messages, and latest_boundary() returns this boundary.
        Both mutations happen without any await between them.
        """
        state = self._get_or_create(thread_id)
        # Clear any uncommitted tail first (torn state from a previous crash sim)
        state.uncommitted_tail.clear()
        # Atomic: extend messages then record boundary (no await between)
        state.committed_messages.extend(new_messages)
        state.boundaries.append(boundary)

    async def latest_boundary(self, thread_id: str) -> Boundary | None:
        """Return the most recently committed Boundary, or None for an empty thread."""
        state = self._threads.get(thread_id)
        if not state or not state.boundaries:
            return None
        return state.boundaries[-1]

    async def resolve_pending(
        self,
        thread_id: str,
        resolved: dict[str, Message],
        boundary: Boundary,
    ) -> None:
        """原地替换 committed_messages 中匹配 tool_call_id 的占位符并追加边界。

        生产环境(append-only 审计)会 append 一条 resolution-event 而非修改历史;
        in-memory 原型做原地替换以保持测试简洁。
        """
        state = self._get_or_create(thread_id)
        for i, m in enumerate(state.committed_messages):
            if m.role == "tool" and m.tool_call_id in resolved:
                state.committed_messages[i] = resolved[m.tool_call_id]
        state.boundaries.append(boundary)

    # ------------------------------------------------------------------
    # Test seam — NOT part of the public ConversationStore Protocol
    # ------------------------------------------------------------------

    def _append_uncommitted(self, thread_id: str, msgs: list[Message]) -> None:
        """Simulate a torn write: append messages without committing a boundary.

        Use ONLY in tests to verify that load() discards the tail.
        In production code this method must never be called.
        """
        state = self._get_or_create(thread_id)
        state.uncommitted_tail.extend(msgs)
        # NOTE: we do NOT add these to committed_messages, so load() will not
        # see them.  This faithfully models a crash after message-write but
        # before boundary-write.
