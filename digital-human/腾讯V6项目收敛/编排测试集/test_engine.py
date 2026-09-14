"""engine 套 · 引擎确定性逻辑测试（今天就能跑绿，零外部依赖）。

全部用 repo 现成件，不造轮子：
- FakeModelCaller（agent_loop.llm）按脚本逐轮吐 ModelTurn = 可控假模型
- InMemoryConversationStore（agent_loop.conversation）= 内存 store
- FakeControlCapability（agent_loop.control）= 控制桩，含 idem 账本 + execute_count
- stubs.py 的 echo / device_ctrl 工具

锁住的红线/核心行为：完成判定、只读执行、控制必确认(ask→挂起)、确认后执行一次、
拒绝不执行、越权 deny 不执行、原地踏步守卫、空响应重试耗尽。

放法：拷进 smart_park_assistant 的 tests/ 下，`pytest test_engine.py -v`。
（这是纯引擎逻辑套；经真实工具子系统+真后端的集成套见 cases.yaml + run_eval.py。）
"""
from __future__ import annotations

import asyncio

from agent_loop.loop import run_loop
from agent_loop.config import LoopConfig, LoopBudget
from agent_loop.budget import BudgetTracker
from agent_loop.llm import FakeModelCaller, ModelTurn
from agent_loop.messages import Message, ToolCallReq
from agent_loop.conversation import Conversation, InMemoryConversationStore
from agent_loop.tools import LoopToolRegistry, LoopTool, ToolContext, ToolResult
from agent_loop.gate import DefaultGate
from agent_loop.control import FakeControlCapability
from agent_loop.runcontrol import RunControl
from agent_loop.plan import PlanState, make_plan_tool
from agent_loop.stubs import echo_tool, device_ctrl_tool, add_tool


# ── 构件 ─────────────────────────────────────────────────────────────────────
def _registry(*extra: LoopTool) -> LoopToolRegistry:
    reg = LoopToolRegistry()
    reg.register(echo_tool())
    reg.register(add_tool())
    reg.register(device_ctrl_tool())
    for t in extra:
        reg.register(t)
    return reg


# 总是抛异常的工具(测熔断:disposition=failed)
def _boom_tool() -> LoopTool:
    async def h(args: dict, ctx: ToolContext) -> ToolResult:
        raise RuntimeError("tool boom")
    return LoopTool(name="boom", description="总是抛异常",
                    parameters={"type": "object", "properties": {"n": {"type": "integer"}}},
                    handler=h)


# 每次调用都抛异常的假模型(测 model_error)
class _RaisingModel:
    async def __call__(self, config, messages, schemas):
        raise RuntimeError("model boom")


# commit 必失败的 store(测 persist_error)
class _FailingCommitStore(InMemoryConversationStore):
    async def commit(self, *a, **k):
        raise RuntimeError("disk full")


def _config(toolset, max_iter=10, max_tool_failures=3) -> LoopConfig:
    return LoopConfig(
        model="fake", max_tokens=512, temperature=0.0, role="main",
        toolset=toolset, budget=LoopBudget(max_iterations=max_iter,
                                           max_tool_failures=max_tool_failures),
    )


def _conv(thread_id="t1", user="请处理", principal=None) -> Conversation:
    return Conversation(thread_id=thread_id,
                        messages=[Message(role="user", content=user)],
                        principal=principal)


def _call(name, args, cid="c1") -> ToolCallReq:
    return ToolCallReq(id=cid, name=name, arguments=args)


def _answer(text="已完成") -> ModelTurn:
    return ModelTurn(content=text, tool_calls=[])


def _run(coro):
    return asyncio.run(coro)


# ── 1. 完成判定：无工具调用 + 有正文 → completed ────────────────────────────
def test_text_answer_completes():
    async def go():
        model = FakeModelCaller([_answer("你好")])
        res = await run_loop(_config([]), _conv(), _registry(), BudgetTracker(_config([]).budget),
                             model, store=InMemoryConversationStore())
        assert res.status == "completed"
        assert res.final == "你好"
    _run(go())


# ── 2. 只读工具执行后给答案 → completed ─────────────────────────────────────
def test_readonly_tool_then_answer():
    async def go():
        model = FakeModelCaller([
            ModelTurn(content="", tool_calls=[_call("echo", {"text": "hi"})]),
            _answer("回显完成"),
        ])
        cfg = _config(["echo"])
        res = await run_loop(cfg, _conv(), _registry(), BudgetTracker(cfg.budget),
                             model, store=InMemoryConversationStore())
        assert res.status == "completed"
        assert any(m.role == "tool" and "hi" in m.content for m in res.conversation.messages)
    _run(go())


# ── 3. 控制必确认：is_control → ask → 挂起，且未内联执行 ─────────────────────
def test_control_requires_confirmation():
    async def go():
        model = FakeModelCaller([
            ModelTurn(content="", tool_calls=[_call("device_ctrl", {"device": "AC-3F", "action": "off"})]),
            _answer(),
        ])
        ctrl = FakeControlCapability()
        cfg = _config(["device_ctrl"])
        res = await run_loop(cfg, _conv(), _registry(), BudgetTracker(cfg.budget),
                             model, store=InMemoryConversationStore(), control=ctrl)
        assert res.status == "awaiting_confirmation"
        assert res.pending                      # 有 pending_batch
        assert ctrl.execute_count == 0          # ★红线：确认前绝不执行
    _run(go())


# ── 4. 确认后执行恰好一次（同一 store/control/conv/model 跨两次调用）─────────
def test_control_approve_executes_once():
    async def go():
        model = FakeModelCaller([
            ModelTurn(content="", tool_calls=[_call("device_ctrl", {"device": "AC-3F", "action": "off"})]),
            _answer("已关闭"),
        ])
        ctrl, store, conv = FakeControlCapability(), InMemoryConversationStore(), _conv()
        cfg = _config(["device_ctrl"])
        budget = BudgetTracker(cfg.budget)
        r1 = await run_loop(cfg, conv, _registry(), budget, model, store=store, control=ctrl)
        assert r1.status == "awaiting_confirmation"
        tcid = r1.pending[0].tool_call_id
        r2 = await run_loop(cfg, conv, _registry(), budget, model, store=store,
                            control=ctrl, resolution={tcid: "approve"})
        assert r2.status == "completed"
        assert ctrl.execute_count == 1          # 恰好一次（幂等）
    _run(go())


# ── 5. 拒绝 → 不执行 ────────────────────────────────────────────────────────
def test_control_reject_not_executed():
    async def go():
        model = FakeModelCaller([
            ModelTurn(content="", tool_calls=[_call("device_ctrl", {"device": "AC-3F", "action": "off"})]),
            _answer("已取消"),
        ])
        ctrl, store, conv = FakeControlCapability(), InMemoryConversationStore(), _conv()
        cfg = _config(["device_ctrl"])
        budget = BudgetTracker(cfg.budget)
        r1 = await run_loop(cfg, conv, _registry(), budget, model, store=store, control=ctrl)
        tcid = r1.pending[0].tool_call_id
        r2 = await run_loop(cfg, conv, _registry(), budget, model, store=store,
                            control=ctrl, resolution={tcid: "reject"})
        assert ctrl.execute_count == 0          # ★红线：拒绝不执行
    _run(go())


# ── 6. 越权红线：deny → 不执行（用 DefaultGate 的 denied 谓词模拟无权限）─────
def test_unauthorized_denied_not_executed():
    async def go():
        model = FakeModelCaller([
            ModelTurn(content="", tool_calls=[_call("device_ctrl", {"device": "AC-3F", "action": "off"})]),
            _answer("无权限"),
        ])
        ctrl = FakeControlCapability()
        gate = DefaultGate(denied=lambda call, tool: call.name == "device_ctrl")  # 模拟越权
        cfg = _config(["device_ctrl"])
        res = await run_loop(cfg, _conv(), _registry(), BudgetTracker(cfg.budget),
                             model, store=InMemoryConversationStore(), gate=gate, control=ctrl)
        assert res.status == "completed"
        assert ctrl.execute_count == 0          # ★红线：越权动作数 = 0
        assert any(m.role == "tool" and "blocked" in m.content for m in res.conversation.messages)
    _run(go())


# ── 7. 原地踏步守卫：相同 tool-call 连发 3 次 → failed/stall ─────────────────
def test_stall_guard():
    async def go():
        same = ModelTurn(content="", tool_calls=[_call("echo", {"text": "x"})])
        model = FakeModelCaller([same, same, same, same])
        cfg = _config(["echo"])
        res = await run_loop(cfg, _conv(), _registry(), BudgetTracker(cfg.budget),
                             model, store=InMemoryConversationStore())
        assert res.status == "failed"
        assert res.reason == "stall"
    _run(go())


# ── 8. 空响应重试耗尽 → failed/empty_response ───────────────────────────────
def test_empty_response_exhausts():
    async def go():
        empty = ModelTurn(content="", tool_calls=[])
        model = FakeModelCaller([empty, empty, empty, empty])
        cfg = _config([])
        res = await run_loop(cfg, _conv(), _registry(), BudgetTracker(cfg.budget),
                             model, store=InMemoryConversationStore())
        assert res.status == "failed"
        assert res.reason == "empty_response"
    _run(go())


# ══════════ 补齐:编排 / 兜底 / 其余出口分支 ══════════

# ── 9. 多工具串行:逐轮调不同工具,都执行 → completed ────────────────────────
def test_multi_tool_serial():
    async def go():
        model = FakeModelCaller([
            ModelTurn(content="", tool_calls=[_call("echo", {"text": "hi"}, "c1")]),
            ModelTurn(content="", tool_calls=[_call("add", {"a": 1, "b": 2}, "c2")]),
            _answer("串行完成"),
        ])
        cfg = _config(["echo", "add"])
        res = await run_loop(cfg, _conv(), _registry(), BudgetTracker(cfg.budget),
                             model, store=InMemoryConversationStore())
        assert res.status == "completed"
        tools = [m for m in res.conversation.messages if m.role == "tool"]
        assert any("hi" in m.content for m in tools) and any("3" in m.content for m in tools)
    _run(go())


# ── 10. 一轮并行:同一轮两个只读调用 → asyncio.gather 并发执行 ────────────────
def test_parallel_one_turn():
    async def go():
        model = FakeModelCaller([
            ModelTurn(content="", tool_calls=[_call("echo", {"text": "hi"}, "c1"),
                                              _call("add", {"a": 2, "b": 3}, "c2")]),
            _answer("并行完成"),
        ])
        cfg = _config(["echo", "add"])
        res = await run_loop(cfg, _conv(), _registry(), BudgetTracker(cfg.budget),
                             model, store=InMemoryConversationStore())
        assert res.status == "completed"
        tools = [m for m in res.conversation.messages if m.role == "tool"]
        assert any("hi" in m.content for m in tools) and any("5" in m.content for m in tools)
    _run(go())


# ── 11. 熔断:工具连续抛异常达上限 → failed/tool_failures ─────────────────────
def test_circuit_breaker_tool_failures():
    async def go():
        model = FakeModelCaller([
            ModelTurn(content="", tool_calls=[_call("boom", {"n": 1}, "c1")]),
            ModelTurn(content="", tool_calls=[_call("boom", {"n": 2}, "c2")]),
            ModelTurn(content="", tool_calls=[_call("boom", {"n": 3}, "c3")]),
            _answer("不该到这"),
        ])
        cfg = _config(["boom"], max_tool_failures=3)
        res = await run_loop(cfg, _conv(), _registry(_boom_tool()), BudgetTracker(cfg.budget),
                             model, store=InMemoryConversationStore())
        assert res.status == "failed" and res.reason == "tool_failures"
    _run(go())


# ── 12. 预算耗尽:迭代超 max_iterations → grace 收尾 → budget_exhausted ────────
def test_budget_exhausted():
    async def go():
        model = FakeModelCaller([
            ModelTurn(content="", tool_calls=[_call("echo", {"text": "a"}, "c1")]),
            ModelTurn(content="", tool_calls=[_call("echo", {"text": "b"}, "c2")]),
            ModelTurn(content="", tool_calls=[_call("echo", {"text": "c"}, "c3")]),
            ModelTurn(content="", tool_calls=[_call("echo", {"text": "d"}, "c4")]),
        ])
        cfg = _config(["echo"], max_iter=2)
        res = await run_loop(cfg, _conv(), _registry(), BudgetTracker(cfg.budget),
                             model, store=InMemoryConversationStore())
        assert res.status == "budget_exhausted"
    _run(go())


# ── 13. 中断:RunControl 置位 → 不提交在途迭代 → interrupted ──────────────────
def test_interrupted():
    async def go():
        rc = RunControl(); rc.request_interrupt()
        model = FakeModelCaller([_answer("不该被调用")])
        cfg = _config([])
        res = await run_loop(cfg, _conv(), _registry(), BudgetTracker(cfg.budget),
                             model, store=InMemoryConversationStore(), run_control=rc)
        assert res.status == "interrupted"
    _run(go())


# ── 14. 模型调用失败重试耗尽 → failed/model_error ───────────────────────────
def test_model_error():
    async def go():
        cfg = _config([])
        res = await run_loop(cfg, _conv(), _registry(), BudgetTracker(cfg.budget),
                             _RaisingModel(), store=InMemoryConversationStore())
        assert res.status == "failed" and res.reason == "model_error"
    _run(go())


# ── 15. 只更新计划不执行:连续 plan-only → failed/no_progress ────────────────
def test_no_progress_plan_only():
    async def go():
        plan = make_plan_tool(PlanState())
        def _p(c, items): return _call("plan", {"items": items}, c)
        model = FakeModelCaller([
            ModelTurn(content="", tool_calls=[_p("c1", [{"id": "1", "content": "x", "status": "todo"}])]),
            ModelTurn(content="", tool_calls=[_p("c2", [{"id": "1", "content": "y", "status": "todo"}])]),
            ModelTurn(content="", tool_calls=[_p("c3", [{"id": "1", "content": "z", "status": "todo"}])]),
            _answer("不该到这"),
        ])
        cfg = _config(["plan"])
        res = await run_loop(cfg, _conv(), _registry(plan), BudgetTracker(cfg.budget),
                             model, store=InMemoryConversationStore())
        assert res.status == "failed" and res.reason == "no_progress"
    _run(go())


# ── 16. 持久化失败:store.commit 抛错 → failed/persist_error ─────────────────
def test_persist_error():
    async def go():
        model = FakeModelCaller([_answer("完成")])
        cfg = _config([])
        res = await run_loop(cfg, _conv(), _registry(), BudgetTracker(cfg.budget),
                             model, store=_FailingCommitStore())
        assert res.status == "failed" and res.reason == "persist_error"
    _run(go())
