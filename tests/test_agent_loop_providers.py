"""test_agent_loop_providers.py — TDD 测试 OpenAIModelCaller（离线，默认跳过真实网络）。

所有非 live 测试使用注入 fake client，不发起任何网络请求。
"""
from __future__ import annotations

import json
import os
import types
import asyncio

import pytest

from agent_loop.providers import OpenAIModelCaller
from agent_loop.llm import ModelTurn
from agent_loop.messages import Message, ToolCallReq
from agent_loop.config import LoopConfig, LoopBudget


# ── Fake client helpers ────────────────────────────────────────────────────────

def _fake_tool_call(id: str, name: str, arguments: str):
    """构造假 tool_call 对象。"""
    fn = types.SimpleNamespace(name=name, arguments=arguments)
    return types.SimpleNamespace(id=id, function=fn)


def _fake_response(
    content: str = "",
    tool_calls=None,
    reasoning: str = "",
    total_tokens: int = 42,
):
    """构造与 openai response 形状兼容的假响应对象。"""
    msg = types.SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
        reasoning=reasoning,
    )
    choice = types.SimpleNamespace(message=msg)
    usage = types.SimpleNamespace(total_tokens=total_tokens)
    return types.SimpleNamespace(choices=[choice], usage=usage)


class FakeCompletions:
    """记录 create() 接收的参数，返回预设响应。"""

    def __init__(self, response):
        self._response = response
        self.last_kwargs: dict = {}

    async def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response


class FakeClient:
    def __init__(self, response):
        self.completions = FakeCompletions(response)

    @property
    def chat(self):
        return self  # chat.completions → self.completions


# ── LoopConfig 工厂 ────────────────────────────────────────────────────────────

def _cfg(model="test-model", max_tokens=512, temperature=0.7):
    return LoopConfig(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        role="main",
        toolset=[],
        budget=LoopBudget(max_iterations=5),
    )


# ── 测试：请求形状 ─────────────────────────────────────────────────────────────

def test_request_shape_with_tools():
    """有 tool_schemas 时：请求带 tools / tool_choice='auto' / extra_body / model / temp。"""
    resp = _fake_response(content="ok")
    fake_client = FakeClient(resp)
    schemas = [{"type": "function", "function": {"name": "echo", "description": "x", "parameters": {}}}]

    caller = OpenAIModelCaller(client=fake_client, enable_thinking=False)
    cfg = _cfg(model="qwen-chat", max_tokens=1024, temperature=0.3)
    asyncio.run(caller(cfg, [Message(role="user", content="hello")], schemas))

    kw = fake_client.completions.last_kwargs
    assert kw["tools"] == schemas
    assert kw["tool_choice"] == "auto"
    assert kw["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert kw["model"] == "qwen-chat"
    assert kw["temperature"] == 0.3
    assert kw["max_tokens"] == 1024


def test_request_shape_no_tools():
    """无 tool_schemas 时：请求不含 tools / tool_choice 键。"""
    resp = _fake_response(content="done")
    fake_client = FakeClient(resp)

    caller = OpenAIModelCaller(client=fake_client)
    asyncio.run(caller(_cfg(), [Message(role="user", content="ping")], []))

    kw = fake_client.completions.last_kwargs
    assert "tools" not in kw
    assert "tool_choice" not in kw


# ── 测试：消息转换保留 tool 结构 ───────────────────────────────────────────────

def test_converter_preserves_assistant_tool_calls():
    """assistant Message 含 tool_calls → 转出的 messages 里有 tool_calls[].function。"""
    resp = _fake_response(content="")
    fake_client = FakeClient(resp)
    caller = OpenAIModelCaller(client=fake_client)

    msgs = [
        Message(role="user", content="查设备"),
        Message(
            role="assistant",
            content="",
            tool_calls=[ToolCallReq(id="tc1", name="query", arguments={"id": 99})],
        ),
    ]
    asyncio.run(caller(None, msgs, []))

    sent = fake_client.completions.last_kwargs["messages"]
    asst = next(m for m in sent if m["role"] == "assistant")
    assert "tool_calls" in asst
    tc = asst["tool_calls"][0]
    assert tc["id"] == "tc1"
    assert tc["function"]["name"] == "query"
    assert json.loads(tc["function"]["arguments"]) == {"id": 99}


def test_converter_preserves_tool_result():
    """tool Message → {"role":"tool","tool_call_id":...} 结构。"""
    resp = _fake_response(content="")
    fake_client = FakeClient(resp)
    caller = OpenAIModelCaller(client=fake_client)

    msgs = [
        Message(role="user", content="q"),
        Message(role="assistant", content="", tool_calls=[ToolCallReq(id="tc2", name="fn", arguments={})]),
        Message(role="tool", content="结果", tool_call_id="tc2"),
    ]
    asyncio.run(caller(None, msgs, []))

    sent = fake_client.completions.last_kwargs["messages"]
    tool_msg = next(m for m in sent if m["role"] == "tool")
    assert tool_msg["tool_call_id"] == "tc2"
    assert tool_msg["content"] == "结果"


# ── 测试：qwen system 折叠规则 ────────────────────────────────────────────────

def test_qwen_system_folding():
    """S4 trailing system（计划快照）被折叠到最近 user 消息中，不出现在历史后面。"""
    resp = _fake_response(content="")
    fake_client = FakeClient(resp)
    caller = OpenAIModelCaller(client=fake_client)

    msgs = [
        Message(role="system", content="S"),
        Message(role="user", content="U"),
        Message(role="assistant", content="", tool_calls=[ToolCallReq(id="t1", name="fn", arguments={})]),
        Message(role="tool", content="tool_result", tool_call_id="t1"),
        Message(role="system", content="PLAN"),  # S4 尾部计划快照
    ]
    asyncio.run(caller(None, msgs, []))

    sent = fake_client.completions.last_kwargs["messages"]

    # 只有一条 system（开头）
    system_msgs = [m for m in sent if m["role"] == "system"]
    assert len(system_msgs) == 1
    assert sent[0]["role"] == "system"
    assert sent[0]["content"] == "S"

    # PLAN 文本折叠进 user 消息，且原 user 内容保留(不被覆盖)
    user_msgs = [m for m in sent if m["role"] == "user"]
    assert any("U" in m["content"] and "PLAN" in m["content"] for m in user_msgs), (
        f"PLAN 应折叠到 user 且保留原 content,实际 messages={sent}"
    )

    # 不存在排在非 system 消息后的 system 消息
    seen_non_system = False
    for m in sent:
        if m["role"] != "system":
            seen_non_system = True
        elif seen_non_system:
            pytest.fail(f"system 出现在历史之后: {sent}")


# ── 测试：响应解析 ────────────────────────────────────────────────────────────

def test_response_parse_full():
    """内容 + tool_call(带 args) + reasoning + usage → ModelTurn 字段全对。"""
    tc = _fake_tool_call(id="c1", name="do_thing", arguments='{"x": 1}')
    resp = _fake_response(
        content="好的",
        tool_calls=[tc],
        reasoning="我想了想",
        total_tokens=100,
    )
    fake_client = FakeClient(resp)
    caller = OpenAIModelCaller(client=fake_client)

    turn = asyncio.run(caller(None, [Message(role="user", content="q")], []))

    assert isinstance(turn, ModelTurn)
    assert turn.content == "好的"
    assert turn.reasoning == "我想了想"
    assert turn.usage_tokens == 100
    assert len(turn.tool_calls) == 1
    assert turn.tool_calls[0] == ToolCallReq(id="c1", name="do_thing", arguments={"x": 1})


# ── 测试：鲁棒性 ──────────────────────────────────────────────────────────────

def test_empty_choices_returns_empty_turn():
    """choices 为空列表时返回 ModelTurn(content='')，不崩溃。"""
    resp = types.SimpleNamespace(choices=[], usage=None)
    fake_client = FakeClient(resp)
    caller = OpenAIModelCaller(client=fake_client)

    turn = asyncio.run(caller(None, [Message(role="user", content="x")], []))
    assert turn.content == ""
    assert turn.tool_calls == []
    assert turn.usage_tokens == 0


def test_malformed_tool_call_arguments_no_crash():
    """tool_call arguments 格式错误 → arguments={}, 不抛异常。"""
    tc = _fake_tool_call(id="bad1", name="fn", arguments="{bad")
    resp = _fake_response(content="", tool_calls=[tc])
    fake_client = FakeClient(resp)
    caller = OpenAIModelCaller(client=fake_client)

    turn = asyncio.run(caller(None, [Message(role="user", content="x")], []))
    assert turn.tool_calls[0].arguments == {}


def test_multiple_tool_calls_parsed():
    """一条响应含多个 tool_call → 全部解析为 ToolCallReq(顺序保留)。"""
    resp = _fake_response(content="", tool_calls=[
        _fake_tool_call(id="a", name="f1", arguments='{"n": 1}'),
        _fake_tool_call(id="b", name="f2", arguments='{"n": 2}'),
    ])
    caller = OpenAIModelCaller(client=FakeClient(resp))
    turn = asyncio.run(caller(None, [Message(role="user", content="x")], []))
    assert [tc.id for tc in turn.tool_calls] == ["a", "b"]
    assert turn.tool_calls[1].arguments == {"n": 2}


def test_tool_call_with_none_function_skipped():
    """vLLM 偶发残缺 tool_call(function=None)→ 跳过,不崩溃。"""
    bad = types.SimpleNamespace(id="x", function=None)
    good = _fake_tool_call(id="g", name="fn", arguments="{}")
    resp = _fake_response(content="", tool_calls=[bad, good])
    caller = OpenAIModelCaller(client=FakeClient(resp))
    turn = asyncio.run(caller(None, [Message(role="user", content="x")], []))
    assert [tc.id for tc in turn.tool_calls] == ["g"]   # 残缺的被跳过


def test_no_usage_returns_zero_tokens():
    """response.usage 为 None 时 usage_tokens == 0。"""
    msg = types.SimpleNamespace(content="ok", tool_calls=None, reasoning=None)
    resp = types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)], usage=None)
    fake_client = FakeClient(resp)
    caller = OpenAIModelCaller(client=fake_client)

    turn = asyncio.run(caller(None, [Message(role="user", content="x")], []))
    assert turn.usage_tokens == 0


# ── Live smoke（默认 skip）────────────────────────────────────────────────────

@pytest.mark.skipif(
    os.getenv("AGENT_LOOP_LIVE_SMOKE") != "1",
    reason="set AGENT_LOOP_LIVE_SMOKE=1 to hit real 6008",
)
def test_live_smoke_real_qwen():
    """真实 qwen vLLM @ 6008 冒烟：有响应（content 或 tool_calls 非空）。"""
    echo_schema = {
        "type": "function",
        "function": {
            "name": "echo",
            "description": "Echo back the input text.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    }
    caller = OpenAIModelCaller()  # 使用默认真实配置
    turn = asyncio.run(
        caller(
            None,
            [Message(role="user", content="请用 echo 工具回显：hello")],
            [echo_schema],
        )
    )
    assert isinstance(turn, ModelTurn)
    assert turn.content or turn.tool_calls, f"响应为空: {turn}"
