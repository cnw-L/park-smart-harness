import asyncio
from agent_loop.llm import ModelTurn, FakeModelCaller
from agent_loop.messages import ToolCallReq

def test_fake_model_caller_scripts_turns():
    turns = [
        ModelTurn(content="先查", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "hi"})], usage_tokens=10),
        ModelTurn(content="完成", tool_calls=[], usage_tokens=5),
    ]
    fake = FakeModelCaller(turns)
    out1 = asyncio.run(fake(None, [], []))
    out2 = asyncio.run(fake(None, [], []))
    assert out1.tool_calls[0].name == "echo"
    assert out2.tool_calls == [] and out2.content == "完成"
