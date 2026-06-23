"""Tests for the transactional run_loop (Task 6).

每轮迭代 = 一个事务;commit 驱动全部持久化。
"""
from __future__ import annotations

import asyncio
import pytest

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.control import FakeControlCapability
from agent_loop.conversation import Conversation, InMemoryConversationStore
from agent_loop.dispatch import ToolExecOutcome
from agent_loop.gate import DefaultGate
from agent_loop.loop import LoopResult, run_loop
from agent_loop.llm import FakeModelCaller, ModelTurn
from agent_loop.messages import Message, ToolCallReq
from agent_loop.stubs import echo_tool
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolResult


# ─── 共用辅助 ────────────────────────────────────────────────────────────────

def _cfg(max_iter: int = 5, max_fail: int = 3, toolset=None) -> LoopConfig:
    return LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=toolset or ["echo"],
        budget=LoopBudget(max_iterations=max_iter, max_tool_failures=max_fail),
    )


def _seeded(tid: str = "t") -> Conversation:
    c = Conversation(thread_id=tid)
    c.append(Message(role="user", content="开始"))
    return c


def run(coro):
    return asyncio.run(coro)


# ─── 1. 无工具调用 + 非空内容 → completed,one completed boundary ──────────────

def test_no_tool_calls_completed():
    """无工具调用 + 非空内容 → completed;store 有一条 completed 边界;会话含用户 + 助手消息。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([ModelTurn(content="done", tool_calls=[])])
    conv = _seeded()
    cfg = _cfg(); budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "completed"
    assert res.final == "done"

    # store 应有 1 条 completed 边界
    boundary = run(store.latest_boundary("t"))
    assert boundary is not None
    assert boundary.status == "completed"
    assert boundary.seq == 1

    # 会话包含 seed user + assistant
    roles = [m.role for m in conv.messages]
    assert roles == ["user", "assistant"]

    # 持久化消息:只有 assistant(seed user 由调用方负责,loop 只 commit buffer)
    persisted = run(store.load("t"))
    assert len(persisted.messages) == 1
    assert persisted.messages[0].role == "assistant"


# ─── 2. 一次读工具 + 最终答案 → completed;2 boundaries;budget 消耗 2 ──────────

def test_one_tool_iteration_then_final_answer():
    """读工具 → 最终答案:store 有 2 条边界(iteration + completed),预算消耗 2 次。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "hi"})]),
        ModelTurn(content="完成", tool_calls=[]),
    ])
    conv = _seeded()
    cfg = _cfg(); budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "completed"
    assert res.final == "完成"

    # 2 条边界
    state = store._threads.get("t")
    assert state is not None
    assert len(state.boundaries) == 2
    assert state.boundaries[0].status == "iteration"
    assert state.boundaries[1].status == "completed"

    # 预算消耗 2 次迭代
    assert budget._iters == 2

    # 会话: user + assistant1 + tool + assistant2
    roles = [m.role for m in conv.messages]
    assert roles == ["user", "assistant", "tool", "assistant"]
    assert any(m.role == "tool" and m.content == "hi" for m in conv.messages)


# ─── 3. 空文本轮次后正常答案:空轮回滚,不留边界 ─────────────────────────────

def test_empty_turn_rolled_back_not_committed():
    """空文本 + 无工具的轮次回滚(不 commit);后续真实答案正常 completed。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[]),   # 空响应:被回滚
        ModelTurn(content="真正答案", tool_calls=[]),
    ])
    conv = _seeded()
    cfg = _cfg(); budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "completed"
    assert res.final == "真正答案"

    # 只有一条边界(空轮不 commit)
    state = store._threads.get("t")
    assert state is not None
    assert len(state.boundaries) == 1
    assert state.boundaries[0].status == "completed"

    # 会话不含空 assistant 消息(已被回滚)
    assistant_msgs = [m for m in conv.messages if m.role == "assistant"]
    assert len(assistant_msgs) == 1
    assert assistant_msgs[0].content == "真正答案"


# ─── 4. 预算耗尽 → grace → budget_exhausted ──────────────────────────────────

def test_budget_exhausted_via_grace():
    """小预算 → 工具循环耗尽 → grace 轮 → budget_exhausted。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    # 足够多的工具轮以耗尽 max_iterations=2
    looping = [
        ModelTurn(content="", tool_calls=[ToolCallReq(id=f"c{i}", name="echo", arguments={"text": "x"})])
        for i in range(10)
    ] + [ModelTurn(content="grace 收尾", tool_calls=[])]
    fake = FakeModelCaller(looping)
    conv = _seeded()
    cfg = _cfg(max_iter=2); budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "budget_exhausted"
    # 最后一条边界 status="completed"(grace 路径)
    boundary = run(store.latest_boundary("t"))
    assert boundary is not None
    assert boundary.status == "completed"


# ─── 5. 连续工具 failed → failed ─────────────────────────────────────────────

def test_consecutive_tool_failures_stop_loop():
    """连续 max_tool_failures 次 disposition==failed 触发熔断,返回 failed。"""
    def boom() -> LoopTool:
        async def h(args, ctx):
            raise RuntimeError("infra error")
        return LoopTool(name="boom", description="", parameters={"type": "object", "properties": {}},
                        handler=h)

    reg = LoopToolRegistry(); reg.register(boom())
    # 3 次 boom(不同参数以绕开原地踏步检测) → 每次 disposition=failed,failures 累积
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="b0", name="boom", arguments={"x": 1})]),
        ModelTurn(content="", tool_calls=[ToolCallReq(id="b1", name="boom", arguments={"x": 2})]),
        ModelTurn(content="", tool_calls=[ToolCallReq(id="b2", name="boom", arguments={"x": 3})]),
        ModelTurn(content="不应到达", tool_calls=[]),
    ])
    conv = _seeded()
    cfg = _cfg(toolset=["boom"], max_fail=3); budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "failed"
    # 最后边界 status=failed
    boundary = run(store.latest_boundary("t"))
    assert boundary is not None
    assert boundary.status == "failed"


# ─── 6. 原地踏步检测:相同 tool call 连续 3 次 → failed ──────────────────────

def test_stall_detection_same_tool_call_repeated():
    """模型连续 STALL_LIMIT=3 次发出相同 tool call 签名 → failed(检测到原地踏步)。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    same_turn = ModelTurn(
        content="", tool_calls=[ToolCallReq(id="stall", name="echo", arguments={"text": "loop"})]
    )
    fake = FakeModelCaller([same_turn, same_turn, same_turn,
                            ModelTurn(content="不应到达", tool_calls=[])])
    conv = _seeded()
    cfg = _cfg(max_iter=10); budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "failed"
    assert "原地踏步" in res.final


# ─── S2 Gate 路由测试 ─────────────────────────────────────────────────────────

# ─── 7. gate allow 路径:普通工具经 gate 允许 → executed,循环完成 ──────────────

def test_gate_allow_read_tool_executes_and_completes():
    """普通工具 → gate allow → executor.execute_one → executed;循环正常完成。"""
    reg = LoopToolRegistry()
    reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "g8"})]),
        ModelTurn(content="门卫放行", tool_calls=[]),
    ])
    conv = _seeded()
    cfg = _cfg(); budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "completed"
    assert res.final == "门卫放行"
    # 会话中 tool 消息存在(echo handler 被执行)
    tool_msgs = [m for m in conv.messages if m.role == "tool"]
    assert any("g8" in m.content for m in tool_msgs)


# ─── 8. gate ask 路径:控制工具 → gate ask → 挂起;handler 从未执行 ──────────────

def test_gate_ask_control_tool_suspends_via_loop():
    """is_control=True 工具 → gate ask → loop 调用 control.freeze → awaiting_confirmation。
    证明:S2 起 loop 负责冻结(非 executor),control.execute_count==0,占位符出现。"""
    async def ctrl_handler(args, ctx):
        return ToolResult(ok=True, content="should-not-run")

    ctrl = LoopTool(
        name="ctrl", description="控制工具", is_control=True,
        parameters={}, handler=ctrl_handler,
    )
    reg = LoopToolRegistry()
    reg.register(ctrl)

    ctrl_call = ToolCallReq(id="tc-gate", name="ctrl", arguments={"cmd": "open"})
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ctrl_call]),
        ModelTurn(content="完成", tool_calls=[]),
    ])

    conv = _seeded("gate-ask")
    cfg = LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=["ctrl"],
        budget=LoopBudget(max_iterations=10),
    )
    budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()
    control = FakeControlCapability()

    res = run(run_loop(cfg, conv, reg, budget, fake,
                       store=store, control=control))

    # loop 通过 gate ask 路径挂起
    assert res.status == "awaiting_confirmation"
    assert res.pending is not None and len(res.pending) == 1
    # handler 从未执行(freeze 而非 execute)
    assert control.execute_count == 0
    # 占位符出现在会话中
    placeholder_msgs = [m for m in conv.messages
                        if m.role == "tool" and m.content == "[pending_confirmation]"]
    assert len(placeholder_msgs) == 1
    assert placeholder_msgs[0].tool_call_id == "tc-gate"


# ─── 9. gate deny 路径:被拒工具 → blocked 合成消息,不计失败,循环继续完成 ────

def test_gate_deny_synthesizes_blocked_message_no_failure():
    """DefaultGate(denied=...) 命中 → 合成 [blocked] tool 消息;
    handler 从未被调用;不计入 failures;循环正常完成(Hermes deny 语义)。"""
    handler_called = False

    async def blocked_handler(args, ctx):
        nonlocal handler_called
        handler_called = True
        return ToolResult(ok=True, content="should not run")

    blocked = LoopTool(
        name="blocked_tool", description="被拒工具", is_control=False,
        parameters={}, handler=blocked_handler,
    )
    reg = LoopToolRegistry()
    reg.register(blocked)

    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[
            ToolCallReq(id="b1", name="blocked_tool", arguments={})
        ]),
        ModelTurn(content="策略拦截后继续", tool_calls=[]),
    ])
    conv = _seeded("gate-deny")
    cfg = LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=["blocked_tool"],
        budget=LoopBudget(max_iterations=10, max_tool_failures=1),
    )
    budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()
    gate = DefaultGate(denied=lambda call, tool: tool.name == "blocked_tool")

    res = run(run_loop(cfg, conv, reg, budget, fake,
                       store=store, gate=gate))

    # 循环正常完成(deny 不计失败,不熔断)
    assert res.status == "completed"
    assert res.final == "策略拦截后继续"
    # handler 从未被调用
    assert handler_called is False
    # [blocked] 合成消息存在于会话
    blocked_msgs = [m for m in conv.messages
                    if m.role == "tool" and "[blocked]" in m.content]
    assert len(blocked_msgs) == 1
    assert blocked_msgs[0].tool_call_id == "b1"


# ─── 10. gate ask 但 control=None:防御分支 → [error] + 计失败 ──────────────────

def test_gate_ask_without_control_capability_errors_and_fails():
    """is_control 工具 → gate ask,但 run_loop 未提供 control → 防御分支:
    合成 [error] 消息、failures+=1、handler 未执行。max_fail=1 → 循环 failed。"""
    handler_called = False

    async def ctrl_handler(args, ctx):
        nonlocal handler_called
        handler_called = True
        return ToolResult(ok=True, content="should-not-run")

    ctrl = LoopTool(
        name="ctrl", description="控制工具", is_control=True,
        parameters={}, handler=ctrl_handler,
    )
    reg = LoopToolRegistry()
    reg.register(ctrl)

    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="x1", name="ctrl", arguments={})]),
    ])
    conv = _seeded("ask-no-control")
    cfg = LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=["ctrl"], budget=LoopBudget(max_iterations=10, max_tool_failures=1),
    )
    budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, budget, fake, store=store))  # 不传 control

    assert res.status == "failed" and res.reason == "tool_failures"
    assert handler_called is False
    err_msgs = [m for m in conv.messages if m.role == "tool" and "[error]" in m.content]
    assert any(m.tool_call_id == "x1" for m in err_msgs)


# ─── 11. 混合批次:同一轮 allow + deny + ask 三条,各自归一化后挂起 ──────────────

def test_gate_mixed_batch_allow_deny_ask():
    """一轮内 allow(echo) + deny(blocked) + ask(ctrl):三条各自路由、各自入 buffer;
    有 ask → 整批挂起 awaiting_confirmation;allow 结果/[blocked]/[pending_confirmation] 同在。"""
    async def ctrl_handler(args, ctx):
        return ToolResult(ok=True, content="should-not-run")

    ctrl = LoopTool(name="ctrl", description="控制", is_control=True,
                    parameters={}, handler=ctrl_handler)
    blocked = LoopTool(name="blocked_tool", description="被拒", is_control=False,
                       parameters={}, handler=lambda a, c: None)
    reg = LoopToolRegistry()
    reg.register(echo_tool()); reg.register(ctrl); reg.register(blocked)

    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[
            ToolCallReq(id="a1", name="echo", arguments={"text": "mix"}),
            ToolCallReq(id="d1", name="blocked_tool", arguments={}),
            ToolCallReq(id="k1", name="ctrl", arguments={"cmd": "open"}),
        ]),
    ])
    conv = _seeded("mixed")
    cfg = LoopConfig(model="m", max_tokens=100, temperature=0.0, role="main",
                     toolset=["echo", "blocked_tool", "ctrl"],
                     budget=LoopBudget(max_iterations=10))
    budget = BudgetTracker(cfg.budget)
    store = InMemoryConversationStore()
    control = FakeControlCapability()
    gate = DefaultGate(denied=lambda call, tool: tool.name == "blocked_tool")

    res = run(run_loop(cfg, conv, reg, budget, fake,
                       store=store, control=control, gate=gate))

    assert res.status == "awaiting_confirmation"
    assert res.pending is not None and len(res.pending) == 1     # 仅 ctrl 进 pending
    tool_msgs = {m.tool_call_id: m.content for m in conv.messages if m.role == "tool"}
    assert "mix" in tool_msgs["a1"]                              # allow 执行结果
    assert "[blocked]" in tool_msgs["d1"]                        # deny 合成
    assert tool_msgs["k1"] == "[pending_confirmation]"           # ask 占位
    assert control.execute_count == 0                            # ask 未执行


# ─── 12. 模型重试退避:瞬时抖动恢复 + 指数退避 ───────────────────────────────

def test_model_retry_backoff_recovers_and_sleeps(monkeypatch):
    """前 2 次模型调用抛异常、第 3 次成功 → 循环恢复完成;重试间有指数退避 sleep。"""
    sleeps: list[float] = []

    async def fake_sleep(d):
        sleeps.append(d)

    monkeypatch.setattr("agent_loop.loop.asyncio.sleep", fake_sleep)

    class FlakyCaller:
        def __init__(self):
            self.n = 0
        async def __call__(self, config, messages, schemas):
            self.n += 1
            if self.n <= 2:
                raise ConnectionError("transient vLLM blip")
            return ModelTurn(content="恢复成功", tool_calls=[])

    reg = LoopToolRegistry(); reg.register(echo_tool())
    conv = _seeded("flaky")
    cfg = _cfg()
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, BudgetTracker(cfg.budget), FlakyCaller(), store=store))

    assert res.status == "completed"
    assert res.final == "恢复成功"
    # 两次重试间各退避一次,指数:0.5, 1.0
    assert sleeps == [0.5, 1.0]


def test_model_retry_exhausted_returns_model_error(monkeypatch):
    """全部尝试都失败 → failed/model_error;最后一次失败不再 sleep(退避次数 = retries)。"""
    sleeps: list[float] = []

    async def fake_sleep(d):
        sleeps.append(d)

    monkeypatch.setattr("agent_loop.loop.asyncio.sleep", fake_sleep)

    class AlwaysFail:
        async def __call__(self, config, messages, schemas):
            raise ConnectionError("down")

    reg = LoopToolRegistry(); reg.register(echo_tool())
    conv = _seeded("down")
    cfg = _cfg()
    store = InMemoryConversationStore()

    res = run(run_loop(cfg, conv, reg, BudgetTracker(cfg.budget), AlwaysFail(), store=store))

    assert res.status == "failed" and res.reason == "model_error"
    # retries=2 → 3 次尝试,前 2 次失败后各 sleep 一次,最后一次不 sleep
    assert len(sleeps) == 2


# ─── thrashing 看门狗:连续无有效结果 → 如实停(对齐 CC thrashing-error) ──────────

def test_thrashing_unproductive_results_stop_before_ceiling():
    """工具结果连续全无效(业务否/ok=False)→ thrashing 看门狗 ~3 轮停,不烧到 max_iterations(30)。"""
    def _bad(args, ctx):
        return ToolResult(ok=False, content="", error="grounding 被拒(模拟死循环)")
    reg = LoopToolRegistry()
    reg.register(LoopTool(name="bad", description="d",
                          parameters={"type": "object", "properties": {}}, handler=_bad))
    # 参数每轮不同 → 绕过 stall(签名相同才触发);只有 thrashing(全无效)能抓住这种死循环
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id=f"x{i}", name="bad", arguments={"n": i})])
        for i in range(30)])
    conv = _seeded()
    cfg = _cfg(max_iter=30, max_fail=99, toolset=["bad"])
    budget = BudgetTracker(cfg.budget)

    res = run(run_loop(cfg, conv, reg, budget, fake, store=InMemoryConversationStore()))

    assert res.status == "failed" and res.reason == "no_progress"
    assert budget._iters <= 4               # ~3 轮即停,远不到 30(不烧天花板)


# ─── 单子抽取上限:run_loop 自身步数上限,独立于(更大的)共享池 ──────────────────

def test_local_iteration_cap_independent_of_shared_pool():
    """有效工具但模型不收尾 → 在 cfg cap(3)停,即使共享池(99)远没满。模拟子 agent 不吃光整池。"""
    reg = LoopToolRegistry(); reg.register(echo_tool())
    # 参数每轮不同 → 不触发 stall;echo 每轮有效 → 不触发 thrashing;只有本地步数上限会停它
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id=f"e{i}", name="echo", arguments={"text": f"hi{i}"})])
        for i in range(50)])
    conv = _seeded()
    cfg = _cfg(max_iter=3, toolset=["echo"])          # 本调用步数上限=3
    shared = BudgetTracker(LoopBudget(max_iterations=99))   # 共享池远大于 cfg cap

    res = run(run_loop(cfg, conv, reg, shared, fake, store=InMemoryConversationStore()))

    assert res.status == "budget_exhausted"
    assert shared._iters <= 4               # 在 cfg cap=3 停,没烧到 99(剩余留给父会话)
