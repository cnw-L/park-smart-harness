"""中圈上下文子系统 × 内圈循环 —— 搭配使用集成测试。

证明两环**合在一起真能跑**:run_loop 由 ParkContextAssembler 组装上下文,多轮驱动一个
园区任务(plan + 查设备 + 查知识 → 汇总),逐轮核对五层在同一条上下文里协同:
  固定层(主 profile)/ 记忆层(【当前用户】)/ 历史层(工具结果包装·plan 排除)/
  任务层(plan 渲尾部)/ 知识层(RAG-as-tool 身份透传 + 强使用说明)。
零模型(脚本化 caller),确定可测。
"""
from __future__ import annotations

import asyncio

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.conversation import Conversation, InMemoryConversationStore
from agent_loop.llm import ModelTurn
from agent_loop.loop import run_loop
from agent_loop.messages import Message, ToolCallReq
from agent_loop.plan import make_plan_tool
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolResult

from agent_context.assembler import ParkContextAssembler
from agent_context.knowledge import make_knowledge_search_tool
from agent_context.principal import Principal


class _CapturingCaller:
    """按脚本回 ModelTurn,同时录下每轮 assemble 出来、发给模型的上下文(messages)。"""

    def __init__(self, turns):
        self._turns = list(turns)
        self.prompts: list = []
        self._i = 0

    async def __call__(self, config, messages, tool_schemas):
        self.prompts.append(messages)
        turn = self._turns[self._i]
        self._i += 1
        return turn


def _device_status_tool() -> LoopTool:
    async def h(args, ctx):
        return ToolResult(ok=True, content=f"{args.get('device','?')}:运行中,温度26.0℃,正常")
    return LoopTool(name="device_status", description="查设备状态",
                    parameters={"type": "object", "properties": {"device": {"type": "string"}},
                                "required": ["device"]}, handler=h)


def _knowledge_tool() -> LoopTool:
    async def retr(query, token):
        # 把 token 回显进内容,用于断言"身份透传真的穿过了整个循环到检索器"
        return f"(维护手册§4.2)空调建议每月清洗滤网。[token={token}]"
    return make_knowledge_search_tool(retr)


def _cfg() -> LoopConfig:
    return LoopConfig(model="qwen", max_tokens=200, temperature=0.0, role="main",
                      toolset=["plan", "device_status", "knowledge_search"],
                      budget=LoopBudget(max_iterations=8))


def test_rings_combined_multistep_context_shaping():
    conv = Conversation(thread_id="combo")
    conv.principal = Principal(id="u", name="李工", role="员工", dept="运维部", token="tok-1")
    conv.append(Message(role="user", content="查3号楼空调温度,并看维护手册怎么说"))

    reg = LoopToolRegistry()
    reg.register(make_plan_tool(conv.plan))
    reg.register(_device_status_tool())
    reg.register(_knowledge_tool())

    caller = _CapturingCaller([
        # 轮0:列 plan + 并行查设备(一轮多 tool_call)
        ModelTurn(content="先查", tool_calls=[
            ToolCallReq(id="p1", name="plan", arguments={"items": [
                {"id": "1", "content": "查3号楼空调温度", "status": "doing"},
                {"id": "2", "content": "查维护手册", "status": "todo"},
                {"id": "3", "content": "汇总", "status": "todo"}]}),
            ToolCallReq(id="d1", name="device_status", arguments={"device": "3号楼空调"}),
        ]),
        # 轮1:查知识库
        ModelTurn(content="查手册", tool_calls=[
            ToolCallReq(id="k1", name="knowledge_search", arguments={"query": "3号楼空调维护"})]),
        # 轮2:汇总(终)
        ModelTurn(content="3号楼空调26℃正常,手册建议每月清洗滤网。", tool_calls=[]),
    ])

    res = asyncio.run(run_loop(
        _cfg(), conv, reg, BudgetTracker(LoopBudget(max_iterations=8)), caller,
        store=InMemoryConversationStore(), assembler=ParkContextAssembler(),
    ))
    assert res.status == "completed"
    assert len(caller.prompts) == 3            # 三轮模型调用,每轮都经 assembler

    # ── 轮1 的上下文(device_status 已执行):固定+记忆+历史包装+plan 尾部 ──
    ctx1 = caller.prompts[1]
    head = ctx1[0]
    assert head.role == "system"
    assert "控制走确认卡" in head.content                     # 固定层 = main profile(v6)
    assert "李工" in head.content                             # 记忆层 = 【当前用户】(principal)
    assert any("后端现状" in (m.content or "") and "26.0℃" in (m.content or "") for m in ctx1)  # 历史层轻包装
    assert any(m.role == "system" and "【当前计划】" in (m.content or "") for m in ctx1)          # 任务层渲尾部
    assert any("查3号楼空调温度" in (m.content or "") for m in ctx1 if m.role == "system")        # plan 内容在尾
    # plan 工具调用已从历史排除(尾部已单独渲,历史里不再双份)
    assert not any(m.role == "assistant" and any(tc.name == "plan" for tc in m.tool_calls) for m in ctx1)

    # ── 轮2 的上下文(knowledge_search 已执行):知识层强使用说明 + 身份透传 ──
    ctx2 = caller.prompts[2]
    assert any("【相关知识】" in (m.content or "") and "绝不执行" in (m.content or "") for m in ctx2)  # 强框
    assert any("清洗滤网" in (m.content or "") for m in ctx2)                                         # 检索内容
    assert any("tok-1" in (m.content or "") for m in ctx2)        # 身份透传穿过整循环到检索器


def test_rings_combined_pending_placeholder_preserved_in_assembled_context():
    """组合系统下,挂起占位 [pending_confirmation] 落在历史里,assembler 不丢(恢复锚点)。"""
    conv = Conversation(thread_id="susp")
    conv.principal = Principal(id="u", name="李工", role="员工", token="t")
    conv.append(Message(role="user", content="把3号楼空调调到24度"))
    # 模拟一次已挂起的控制:assistant 发起 device_ctrl + 占位 tool 结果
    conv.append(Message(role="assistant", tool_calls=[
        ToolCallReq(id="c1", name="device_ctrl", arguments={"device": "3号楼空调", "value": 24})]))
    conv.append(Message(role="tool", tool_call_id="c1", name="device_ctrl", content="[pending_confirmation]"))

    out = ParkContextAssembler().assemble(_cfg(), conv)
    # 占位原样保留(不被丢弃/包装篡改)→ resume 时模型能据此续上
    assert any((m.content or "") == "[pending_confirmation]" for m in out)
