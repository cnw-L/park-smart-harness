import asyncio
from agent_loop.messages import Message, ToolCallReq
from agent_loop.conversation import Conversation, InMemoryConversationStore, Boundary
from agent_loop.plan import PlanState

def test_conversation_appends_messages():
    conv = Conversation(thread_id="t1")
    conv.append(Message(role="user", content="hi"))
    conv.append(Message(role="assistant", content="",
                        tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"x": "y"})]))
    assert len(conv.messages) == 2
    assert conv.messages[1].tool_calls[0].name == "echo"

def test_inmemory_store_roundtrip():
    store = InMemoryConversationStore()
    async def run():
        await store.commit(
            "t1",
            [Message(role="user", content="hi")],
            Boundary(status="iteration", turn_id="turn-1", seq=1),
        )
        conv = await store.load("t1")
        return conv
    conv = asyncio.run(run())
    assert conv.messages[0].content == "hi"


def test_inmemory_load_rebuilds_plan_from_messages():
    """load() 应从已提交消息中派生 plan 投影（而非依赖内存中的 in-place 变更）。"""
    store = InMemoryConversationStore()

    plan_args = {
        "items": [
            {"id": "s1", "content": "查告警", "status": "done"},
            {"id": "s2", "content": "生成报告", "status": "doing"},
        ]
    }
    msgs = [
        Message(role="user", content="帮我汇总告警"),
        Message(role="assistant", content="",
                tool_calls=[ToolCallReq(id="p1", name="plan", arguments=plan_args)]),
        Message(role="tool", content="plan updated", tool_call_id="p1", name="plan"),
    ]

    async def run():
        await store.commit(
            "th-plan",
            msgs,
            Boundary(status="iteration", turn_id="turn-plan", seq=1),
        )
        # load 返回全新的 Conversation 对象（非内存 in-place 变更）
        conv = await store.load("th-plan")
        return conv

    conv = asyncio.run(run())

    # plan 投影已由 derive_plan 重建
    assert len(conv.plan.items) == 2
    assert conv.plan.items[0].id == "s1"
    assert conv.plan.items[0].status == "done"
    assert conv.plan.items[1].id == "s2"
    assert conv.plan.items[1].status == "doing"


def test_inmemory_load_plan_empty_when_no_plan_calls():
    """无 plan 工具调用的消息日志 → load 返回空 plan。"""
    store = InMemoryConversationStore()

    async def run():
        await store.commit(
            "th-noplan",
            [Message(role="user", content="hi"), Message(role="assistant", content="hello")],
            Boundary(status="iteration", turn_id="turn-1", seq=1),
        )
        return await store.load("th-noplan")

    conv = asyncio.run(run())
    assert conv.plan.items == []
