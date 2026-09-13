"""estimate_tokens 契约单测（agent_context.tokens）。

被 assembler / history / compactor 三处用作压缩 fail-safe 触发依据，
契约来自模块自述（char-based 粗估、单调、大致缩放、不为 0）与调用方事实。
不引入真 tokenizer。
"""
from agent_loop.messages import Message, ToolCallReq
from agent_context.tokens import estimate_tokens


def test_empty_messages_returns_positive_floor():
    # 估值为 0 会让 fail-safe 触发条件永远不满足，故下限必须为正
    assert estimate_tokens([]) >= 1


def test_default_fields_tolerated():
    # Message 全默认字段（content=""/reasoning=""/tool_calls=[]）不得崩
    assert estimate_tokens([Message(role="user")]) >= 1


def test_content_and_reasoning_both_counted():
    base = Message(role="assistant", content="")
    with_content = Message(role="assistant", content="x" * 100)
    with_reasoning = Message(role="assistant", reasoning="y" * 100)
    assert estimate_tokens([with_content]) > estimate_tokens([base])
    assert estimate_tokens([with_reasoning]) > estimate_tokens([base])


def test_tool_calls_counted():
    plain = Message(role="assistant", content="")
    with_call = Message(
        role="assistant",
        tool_calls=[ToolCallReq(id="t1", name="read_file", arguments={"path": "a" * 50})],
    )
    assert estimate_tokens([with_call]) > estimate_tokens([plain])


def test_monotonic_non_decreasing():
    few = [Message(role="user", content="a" * 10)]
    many = few + [
        Message(role="user", content="b" * 100),
        Message(role="tool", content="c" * 100),
    ]
    assert estimate_tokens(many) >= estimate_tokens(few)


def test_roughly_linear_scaling():
    # 约 2 chars/token：字符数翻倍 → 估值近似翻倍（允许粗估容差）
    small = estimate_tokens([Message(role="user", content="a" * 500)])
    big = estimate_tokens([Message(role="user", content="a" * 1000)])
    assert big > small
    assert 1.5 <= big / small <= 2.5
