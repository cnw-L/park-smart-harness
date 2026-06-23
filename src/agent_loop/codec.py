"""codec.py — JSON-safe 序列化/反序列化，供 Redis/Postgres 持久化层使用。

纯函数，无 I/O，无网络。所有编码结果均可 json.dumps/json.loads 安全穿越。
解码函数对缺失的可选字段宽容（使用 .get + 默认值），忽略未知额外字段。
"""
from __future__ import annotations

from .messages import Message, ToolCallReq
from .conversation import Boundary
from .pending import PendingAction


# ---------------------------------------------------------------------------
# ToolCallReq
# ---------------------------------------------------------------------------

def encode_tool_call(tc: ToolCallReq) -> dict:
    """将 ToolCallReq 编码为 JSON-safe dict。"""
    return {
        "id": tc.id,
        "name": tc.name,
        "arguments": dict(tc.arguments),   # 拷贝:编码结果独立,避免下游改 dict 污染 live 对象
    }


def decode_tool_call(d: dict) -> ToolCallReq:
    """从 dict 还原 ToolCallReq；忽略未知字段，缺失字段使用默认值。"""
    return ToolCallReq(
        id=d.get("id", ""),
        name=d.get("name", ""),
        arguments=d.get("arguments") or {},
    )


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

def encode_message(m: Message) -> dict:
    """将 Message 编码为 JSON-safe dict（含所有字段）。"""
    return {
        "role": m.role,
        "content": m.content,
        "reasoning": m.reasoning,
        "tool_calls": [encode_tool_call(tc) for tc in m.tool_calls],
        "tool_call_id": m.tool_call_id,
        "name": m.name,
        "is_error": m.is_error,
    }


def decode_message(d: dict) -> Message:
    """从 dict 还原 Message；宽容可选字段缺失，忽略未知字段。"""
    raw_tool_calls = d.get("tool_calls") or []
    return Message(
        role=d.get("role", ""),
        content=d.get("content", ""),
        reasoning=d.get("reasoning", ""),
        tool_calls=[decode_tool_call(tc) for tc in raw_tool_calls],
        tool_call_id=d.get("tool_call_id", None),
        name=d.get("name", None),
        is_error=d.get("is_error", False),
    )


def encode_messages(msgs: list[Message]) -> list[dict]:
    """批量编码 Message 列表。"""
    return [encode_message(m) for m in msgs]


def decode_messages(dicts: list[dict]) -> list[Message]:
    """批量解码 Message 列表。"""
    return [decode_message(d) for d in dicts]


# ---------------------------------------------------------------------------
# PendingAction
# ---------------------------------------------------------------------------

def encode_pending(p: PendingAction) -> dict:
    """将 PendingAction 编码为 JSON-safe dict。
    handle 字段透传（调用方保证其 JSON-safe 或为 None）。"""
    return {
        "tool_call_id": p.tool_call_id,
        "idem_key": p.idem_key,
        "frozen_action": dict(p.frozen_action),   # 拷贝(同上)
        "handle": p.handle,
    }


def decode_pending(d: dict) -> PendingAction:
    """从 dict 还原 PendingAction；宽容可选字段缺失，忽略未知字段。"""
    return PendingAction(
        tool_call_id=d.get("tool_call_id", ""),
        idem_key=d.get("idem_key", ""),
        frozen_action=d.get("frozen_action") or {},
        handle=d.get("handle", None),
    )


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------

def encode_boundary(b: Boundary) -> dict:
    """将 Boundary 编码为 JSON-safe dict。
    pending_batch: None → None，list[PendingAction] → list[dict]。
    budget_snapshot: 直接透传（已为 plain dict 或 None）。"""
    if b.pending_batch is None:
        encoded_batch = None
    else:
        encoded_batch = [encode_pending(p) for p in b.pending_batch]

    return {
        "status": b.status,
        "turn_id": b.turn_id,
        "seq": b.seq,
        "pending_batch": encoded_batch,
        "budget_snapshot": dict(b.budget_snapshot) if b.budget_snapshot is not None else None,  # 拷贝(同上)
    }


def decode_boundary(d: dict) -> Boundary:
    """从 dict 还原 Boundary；宽容可选字段缺失，忽略未知字段。"""
    raw_batch = d.get("pending_batch", None)
    if raw_batch is None:
        decoded_batch = None
    else:
        decoded_batch = [decode_pending(p) for p in raw_batch]

    return Boundary(
        status=d.get("status", ""),
        turn_id=d.get("turn_id", ""),
        seq=d.get("seq", 0),
        pending_batch=decoded_batch,
        budget_snapshot=d.get("budget_snapshot", None),
    )
