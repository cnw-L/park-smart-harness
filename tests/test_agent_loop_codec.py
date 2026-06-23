"""Tests for agent_loop.codec — JSON-safe 序列化/反序列化 (P1).

所有测试均为纯函数，无 I/O，通过真实 json.dumps/json.loads 穿越验证。
"""
from __future__ import annotations

import json

import pytest

from agent_loop.codec import (
    decode_boundary,
    decode_message,
    decode_messages,
    decode_pending,
    decode_tool_call,
    encode_boundary,
    encode_message,
    encode_messages,
    encode_pending,
    encode_tool_call,
)
from agent_loop.conversation import Boundary
from agent_loop.messages import Message, ToolCallReq
from agent_loop.pending import PendingAction


# ---------------------------------------------------------------------------
# 辅助：JSON 往返（所有测试都过此关卡确保 JSON-safe）
# ---------------------------------------------------------------------------

def _json_roundtrip(obj):
    """序列化为 JSON 字符串再反序列化，模拟 Redis/Postgres 存取。"""
    return json.loads(json.dumps(obj))


# ---------------------------------------------------------------------------
# ToolCallReq 编解码
# ---------------------------------------------------------------------------

def test_tool_call_roundtrip_simple():
    tc = ToolCallReq(id="call-1", name="get_weather", arguments={"city": "Beijing"})
    encoded = _json_roundtrip(encode_tool_call(tc))
    decoded = decode_tool_call(encoded)
    assert decoded == tc


def test_tool_call_roundtrip_nested_arguments():
    """嵌套 dict arguments 安全穿越 JSON。"""
    tc = ToolCallReq(
        id="call-2",
        name="create_ticket",
        arguments={"payload": {"priority": 1, "tags": ["urgent", "patrol"]}, "dry_run": False},
    )
    encoded = _json_roundtrip(encode_tool_call(tc))
    decoded = decode_tool_call(encoded)
    assert decoded == tc


# ---------------------------------------------------------------------------
# Message 编解码
# ---------------------------------------------------------------------------

def test_message_plain_user():
    """普通 user 消息，所有可选字段保持默认值。"""
    m = Message(role="user", content="你好，请帮我查一下当前告警")
    encoded = _json_roundtrip(encode_message(m))
    decoded = decode_message(encoded)
    assert decoded == m


def test_message_assistant_with_multiple_tool_calls():
    """assistant 消息携带多个 tool_calls。"""
    m = Message(
        role="assistant",
        content="",
        reasoning="先查告警再查工单",
        tool_calls=[
            ToolCallReq(id="c1", name="list_alarms", arguments={"limit": 10}),
            ToolCallReq(id="c2", name="list_orders", arguments={"status": "open", "page": 1}),
        ],
    )
    encoded = _json_roundtrip(encode_message(m))
    decoded = decode_message(encoded)
    assert decoded == m
    assert len(decoded.tool_calls) == 2
    assert decoded.tool_calls[0].name == "list_alarms"
    assert decoded.tool_calls[1].name == "list_orders"


def test_message_tool_result_with_error():
    """tool 消息，带 tool_call_id/name/is_error=True，模拟执行失败结果。"""
    m = Message(
        role="tool",
        content="ConnectionError: timeout",
        tool_call_id="c1",
        name="list_alarms",
        is_error=True,
    )
    encoded = _json_roundtrip(encode_message(m))
    decoded = decode_message(encoded)
    assert decoded == m
    assert decoded.is_error is True
    assert decoded.tool_call_id == "c1"
    assert decoded.name == "list_alarms"


def test_message_all_fields_preserved():
    """断言每个具名字段均被正确还原。"""
    m = Message(
        role="assistant",
        content="好的",
        reasoning="我想了一会儿",
        tool_calls=[ToolCallReq(id="x", name="noop", arguments={})],
        tool_call_id=None,
        name="sub_agent",
        is_error=False,
    )
    decoded = decode_message(_json_roundtrip(encode_message(m)))
    assert decoded.role == "assistant"
    assert decoded.content == "好的"
    assert decoded.reasoning == "我想了一会儿"
    assert decoded.tool_calls == [ToolCallReq(id="x", name="noop", arguments={})]
    assert decoded.tool_call_id is None
    assert decoded.name == "sub_agent"
    assert decoded.is_error is False


# ---------------------------------------------------------------------------
# PendingAction 编解码
# ---------------------------------------------------------------------------

def test_pending_action_handle_none():
    """handle=None（默认）正常穿越 JSON。"""
    p = PendingAction(
        tool_call_id="c3",
        idem_key="idem-abc-123",
        frozen_action={"tool": "open_gate", "args": {"gate_id": "G01"}},
        handle=None,
    )
    encoded = _json_roundtrip(encode_pending(p))
    decoded = decode_pending(encoded)
    assert decoded == p


def test_pending_action_handle_string():
    """handle 为字符串（ticket id）时正常穿越。"""
    p = PendingAction(
        tool_call_id="c4",
        idem_key="idem-xyz-456",
        frozen_action={"tool": "lock_door", "args": {"door_id": "D02", "force": True}},
        handle="ticket-789",
    )
    encoded = _json_roundtrip(encode_pending(p))
    decoded = decode_pending(encoded)
    assert decoded == p
    assert decoded.handle == "ticket-789"


# ---------------------------------------------------------------------------
# Boundary 编解码
# ---------------------------------------------------------------------------

def test_boundary_no_pending_batch():
    """pending_batch=None 的普通 iteration 边界。"""
    b = Boundary(status="iteration", turn_id="turn-1", seq=1)
    encoded = _json_roundtrip(encode_boundary(b))
    decoded = decode_boundary(encoded)
    assert decoded == b
    assert decoded.pending_batch is None
    assert decoded.budget_snapshot is None


def test_boundary_awaiting_confirmation_full_roundtrip():
    """awaiting_confirmation 边界，含 pending_batch（多个 PendingAction）和 budget_snapshot。

    这是 P1 的核心场景：encode → json.dumps → json.loads → decode，深度比较。
    """
    p1 = PendingAction(
        tool_call_id="c1",
        idem_key="idem-001",
        frozen_action={"tool": "open_gate", "args": {"gate_id": "G01"}},
        handle=None,
    )
    p2 = PendingAction(
        tool_call_id="c2",
        idem_key="idem-002",
        frozen_action={"tool": "dispatch_patrol", "args": {"zone": "A3"}},
        handle="ticket-999",
    )
    b = Boundary(
        status="awaiting_confirmation",
        turn_id="turn-2",
        seq=2,
        pending_batch=[p1, p2],
        budget_snapshot={"iters": 2, "tokens": 10, "grace_used": False},
    )

    # 真实 JSON 穿越
    wire = json.dumps(encode_boundary(b))
    recovered = decode_boundary(json.loads(wire))

    assert recovered == b
    assert len(recovered.pending_batch) == 2
    assert recovered.pending_batch[0] == p1
    assert recovered.pending_batch[1] == p2
    assert recovered.budget_snapshot == {"iters": 2, "tokens": 10, "grace_used": False}


def test_boundary_budget_snapshot_passthrough():
    """budget_snapshot 的所有字段均被透传（dict pass-through）。"""
    snap = {"iters": 5, "tokens": 999, "grace_used": True}
    b = Boundary(status="completed", turn_id="t3", seq=3, budget_snapshot=snap)
    decoded = decode_boundary(_json_roundtrip(encode_boundary(b)))
    assert decoded.budget_snapshot == snap


# ---------------------------------------------------------------------------
# 防御性解码：缺失可选字段 + 未知额外字段
# ---------------------------------------------------------------------------

def test_decode_message_missing_optional_fields():
    """只有 role 的最小 dict 可以被解码，不崩溃，可选字段用默认值填充。"""
    minimal = {"role": "user"}
    decoded = decode_message(minimal)
    assert decoded.role == "user"
    assert decoded.content == ""
    assert decoded.reasoning == ""
    assert decoded.tool_calls == []
    assert decoded.tool_call_id is None
    assert decoded.name is None
    assert decoded.is_error is False


def test_decode_message_unknown_extra_key_ignored():
    """dict 中包含未知字段时不会引发 TypeError。"""
    d = {
        "role": "user",
        "content": "hello",
        "unknown_future_field": "some_value",
        "another_extra": 42,
    }
    decoded = decode_message(d)  # 不应抛出异常
    assert decoded.role == "user"
    assert decoded.content == "hello"


def test_decode_tool_call_missing_fields():
    """最小 ToolCallReq dict（空 dict）不崩溃。"""
    decoded = decode_tool_call({})
    assert decoded.id == ""
    assert decoded.name == ""
    assert decoded.arguments == {}


def test_decode_tool_call_unknown_extra_key_ignored():
    d = {"id": "c1", "name": "foo", "arguments": {}, "extra": "bar"}
    decoded = decode_tool_call(d)
    assert decoded.id == "c1"
    assert decoded.name == "foo"


def test_decode_pending_missing_fields():
    """最小 PendingAction dict 不崩溃。"""
    decoded = decode_pending({})
    assert decoded.tool_call_id == ""
    assert decoded.idem_key == ""
    assert decoded.frozen_action == {}
    assert decoded.handle is None


def test_decode_pending_unknown_extra_key_ignored():
    d = {
        "tool_call_id": "c1",
        "idem_key": "k",
        "frozen_action": {},
        "handle": None,
        "extra_field": "surprise",
    }
    decoded = decode_pending(d)
    assert decoded.tool_call_id == "c1"


def test_decode_boundary_missing_optional_fields():
    """只有必填字段的 Boundary dict 不崩溃。"""
    d = {"status": "iteration", "turn_id": "t1", "seq": 1}
    decoded = decode_boundary(d)
    assert decoded.status == "iteration"
    assert decoded.pending_batch is None
    assert decoded.budget_snapshot is None


def test_decode_boundary_unknown_extra_key_ignored():
    d = {
        "status": "completed",
        "turn_id": "t2",
        "seq": 2,
        "future_field": "v2_feature",
    }
    decoded = decode_boundary(d)
    assert decoded.status == "completed"


# ---------------------------------------------------------------------------
# encode_messages / decode_messages 列表批量接口
# ---------------------------------------------------------------------------

def test_encode_decode_messages_list_roundtrip():
    """批量列表接口：encode_messages/decode_messages 正确处理混合消息列表。"""
    msgs = [
        Message(role="user", content="查一下 G01 大门状态"),
        Message(
            role="assistant",
            content="",
            tool_calls=[ToolCallReq(id="c1", name="get_gate_status", arguments={"gate_id": "G01"})],
        ),
        Message(role="tool", content='{"status": "open"}', tool_call_id="c1", name="get_gate_status"),
    ]
    encoded = encode_messages(msgs)
    wire = _json_roundtrip(encoded)
    decoded = decode_messages(wire)
    assert decoded == msgs


def test_encode_messages_empty_list():
    assert encode_messages([]) == []
    assert decode_messages([]) == []


def test_empty_pending_batch_roundtrips_distinct_from_none():
    """pending_batch=[](空列表)≠ None,应保真 round-trip。"""
    b = Boundary(status="iteration", turn_id="t1", seq=1, pending_batch=[])
    got = decode_boundary(json.loads(json.dumps(encode_boundary(b))))
    assert got.pending_batch == []
    assert got.pending_batch is not None


def test_encode_does_not_alias_source_dicts():
    """encode 结果是独立快照:改编码后的 dict 不污染 live 对象。"""
    tc = ToolCallReq(id="c1", name="fn", arguments={"n": 1})
    enc = encode_tool_call(tc)
    enc["arguments"]["n"] = 999
    assert tc.arguments["n"] == 1   # 源未被污染

    b = Boundary(status="x", turn_id="t", seq=1, budget_snapshot={"iters": 2})
    eb = encode_boundary(b)
    eb["budget_snapshot"]["iters"] = 999
    assert b.budget_snapshot["iters"] == 2

    p = PendingAction(tool_call_id="c1", idem_key="k", frozen_action={"a": 1})
    ep = encode_pending(p)
    ep["frozen_action"]["a"] = 999
    assert p.frozen_action["a"] == 1
