"""test_agent_loop_steer.py — 模态门 + steer (Task S5)

§六补:pending 期间新意图门控
  1. 自由文本新意图不穿过 pending 态:既无 resolution 又无 cancel → 维持 awaiting_confirmation。
  2. cancel=True → 整批 reject-all → 干净边界 → 新意图正常处理 → completed。
  3. resolution(approve)回归:confirm 路径不受影响 → completed,execute_count==1。

§五补:非 pending 场景 steer(可选)
  4. 无 pending 态:新消息直接落入正常循环,模型处理并 completed。
"""
from __future__ import annotations

import asyncio

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.control import FakeControlCapability
from agent_loop.conversation import Boundary, Conversation, InMemoryConversationStore
from agent_loop.llm import FakeModelCaller, ModelTurn
from agent_loop.loop import run_loop
from agent_loop.messages import Message, ToolCallReq
from agent_loop.stubs import echo_tool
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolResult


# ─── 共用辅助 ────────────────────────────────────────────────────────────────

def _cfg(max_iter: int = 10) -> LoopConfig:
    return LoopConfig(
        model="m", max_tokens=100, temperature=0.0, role="main",
        toolset=["ctrl", "echo"],
        budget=LoopBudget(max_iterations=max_iter),
    )


def _ctrl_tool() -> LoopTool:
    """is_control=True 工具;handler 不应被内联调用。"""
    async def h(args, ctx):
        return ToolResult(ok=True, content="should-not-run")
    return LoopTool(
        name="ctrl", description="控制工具", is_control=True,
        parameters={"type": "object", "properties": {"cmd": {"type": "string"}}},
        handler=h,
    )


def _commit_user_seed(
    store: InMemoryConversationStore,
    thread_id: str,
    text: str = "请操作",
) -> Conversation:
    """服务端职责:入站 user 消息先落库,再交给 run_loop。

    恢复路径完全从 store 重载;调用方必须先把 user 消息 commit 进去,
    否则重载后会话缺 user 消息、assembler 角色交替校验失败。
    """
    asyncio.run(store.commit(
        thread_id,
        [Message(role="user", content=text)],
        Boundary(status="user", turn_id="turn-0", seq=0,
                 pending_batch=None, budget_snapshot=None),
    ))
    return asyncio.run(store.load(thread_id))


def _make_reg() -> LoopToolRegistry:
    reg = LoopToolRegistry()
    reg.register(echo_tool())
    reg.register(_ctrl_tool())
    return reg


def run(coro):
    return asyncio.run(coro)


# ─── 辅助:驱动一次 run 到 awaiting_confirmation ────────────────────────────────

def _drive_to_suspend(
    thread_id: str = "t",
    user_text: str = "请操作",
    ctrl_call_id: str = "tc1",
) -> tuple[InMemoryConversationStore, FakeControlCapability, LoopConfig]:
    """首次 run:control tool → awaiting_confirmation。
    返回 (store, control, cfg) 供后续 resume/gate 测试使用。
    """
    store = InMemoryConversationStore()
    conv = _commit_user_seed(store, thread_id, user_text)
    reg = _make_reg()
    cfg = _cfg()
    budget = BudgetTracker(cfg.budget)
    control = FakeControlCapability()

    ctrl_call = ToolCallReq(id=ctrl_call_id, name="ctrl", arguments={"cmd": "open"})
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ctrl_call]),
    ])

    res = run(run_loop(cfg, conv, reg, budget, fake,
                       store=store, control=control))
    assert res.status == "awaiting_confirmation", f"期望挂起,得 {res.status}"
    return store, control, cfg


# ─── Test 1: 模态门阻断自由文本新意图 ────────────────────────────────────────

def test_modal_gate_blocks_free_text_through_pending():
    """自由文本新意图不穿过 pending 态。

    - 无 resolution、无 cancel → 返回 awaiting_confirmation。
    - control.execute_count == 0(模型未被调用,控制未执行)。
    - 新意图对应的 assistant turn 未产生(模型未消费脚本化回复)。
    """
    tid = "gate-test"
    store, control, cfg = _drive_to_suspend(tid, ctrl_call_id="tc1")

    # 重载 + 追加自由文本新意图
    conv2 = run(store.load(tid))
    conv2.messages.append(Message(role="user", content="新指令:做别的事"))

    # 脚本化:如果门控失效、模型被调用,会消耗这条 turn
    fake2 = FakeModelCaller([
        ModelTurn(content="新意图的回答", tool_calls=[]),
    ])
    budget2 = BudgetTracker(cfg.budget)

    # 无 resolution、无 cancel
    res2 = run(run_loop(cfg, conv2, _make_reg(), budget2, fake2,
                        store=store, control=control))

    # 断言:状态维持挂起
    assert res2.status == "awaiting_confirmation", (
        f"门控应维持挂起,得 {res2.status!r}")

    # 控制未执行(execute_count 仍 0)
    assert control.execute_count == 0

    # 模型未被调用:FakeModelCaller 的索引仍在 0(脚本化 turn 未被消费)
    assert fake2._i == 0, "门控失效:模型被调用了(新意图穿过了 pending 态)"

    # store 最新边界仍是 awaiting_confirmation(未被覆盖)
    lb = run(store.latest_boundary(tid))
    assert lb is not None and lb.status == "awaiting_confirmation"


# ─── Test 2: cancel=True → reject-all → 干净边界 → 新意图被处理 ──────────────

def test_cancel_reject_all_then_new_intent_processed():
    """cancel=True → 整批 reject → 进入正常循环处理新意图 → completed。

    - pending action 被 reject(execute_count == 0)。
    - 占位符替换为 [rejected] 内容。
    - 循环继续,新意图的回答被完成(status == completed)。
    """
    tid = "cancel-test"
    store, control, cfg = _drive_to_suspend(tid, ctrl_call_id="tc2")

    # 重载 + 追加新意图 user 消息
    conv2 = run(store.load(tid))
    conv2.messages.append(Message(role="user", content="算了,改做回显"))

    # 模型处理新意图后回复
    fake2 = FakeModelCaller([
        ModelTurn(content="新意图已处理", tool_calls=[]),
    ])
    budget2 = BudgetTracker(cfg.budget)

    res2 = run(run_loop(cfg, conv2, _make_reg(), budget2, fake2,
                        store=store, control=control,
                        cancel=True))

    # pending 整批被 reject(未执行)
    assert control.execute_count == 0, "cancel=reject-all 不应执行 control"

    # 循环继续完成,新意图被处理
    assert res2.status == "completed", f"期望 completed,得 {res2.status!r}"
    assert res2.final == "新意图已处理"

    # store 中占位符已替换为 [rejected] 文本
    loaded = run(store.load(tid))
    tool_msgs = [m for m in loaded.messages
                 if m.role == "tool" and m.tool_call_id == "tc2"]
    assert tool_msgs, "控制工具结果应在 store 中"
    assert "[rejected]" in tool_msgs[-1].content, (
        f"期望 [rejected],得 {tool_msgs[-1].content!r}")
    assert "[pending_confirmation]" not in tool_msgs[-1].content


# ─── Test 3: resolution(approve) 回归 ────────────────────────────────────────

def test_resolution_approve_still_works():
    """模态门新增代码不破坏既有 approve 恢复路径。

    approve → control.execute_count == 1 → status == completed。
    """
    tid = "approve-test"
    store, control, cfg = _drive_to_suspend(tid, ctrl_call_id="tc3")

    conv2 = run(store.load(tid))
    # 兼容既有 resume 测试风格:重载后需要包含 user 消息(assembler 角色交替)
    # store.load 已含落库的 user seed,不需再 prepend
    budget2 = BudgetTracker(cfg.budget)
    fake2 = FakeModelCaller([
        ModelTurn(content="操作完成", tool_calls=[]),
    ])

    res2 = run(run_loop(cfg, conv2, _make_reg(), budget2, fake2,
                        store=store, control=control,
                        resolution={"tc3": "approve"}))

    assert res2.status == "completed", f"期望 completed,得 {res2.status!r}"
    assert res2.final == "操作完成"
    # approve → 执行一次
    assert control.execute_count == 1


# ─── Test 4: 非 pending 场景 steer ───────────────────────────────────────────

def test_non_pending_new_message_processed_normally():
    """无 pending 态:新 user 消息直接进入正常循环处理,无需 gate。

    验证非 pending 路径不受模态门干扰。
    """
    store = InMemoryConversationStore()
    conv = _commit_user_seed(store, "steer-test", "第一条消息")
    cfg = _cfg()
    budget = BudgetTracker(cfg.budget)

    # 正常回复,无 control 工具调用
    fake = FakeModelCaller([
        ModelTurn(content="处理完毕", tool_calls=[]),
    ])

    res = run(run_loop(cfg, conv, _make_reg(), budget, fake, store=store))

    assert res.status == "completed"
    assert res.final == "处理完毕"


# ─── Test 5: cancel=True 优先于 resolution(precedence) ──────────────────────

def test_cancel_takes_precedence_over_resolution():
    """同时给 cancel=True 与 resolution{approve} → cancel 胜出,整批 reject、approve 被忽略。"""
    tid = "precedence-test"
    store, control, cfg = _drive_to_suspend(tid, ctrl_call_id="tc5")

    conv2 = run(store.load(tid))
    budget2 = BudgetTracker(cfg.budget)
    fake2 = FakeModelCaller([
        ModelTurn(content="已取消", tool_calls=[]),
    ])

    res2 = run(run_loop(cfg, conv2, _make_reg(), budget2, fake2,
                        store=store, control=control,
                        resolution={"tc5": "approve"}, cancel=True))

    assert res2.status == "completed"
    assert control.execute_count == 0, "cancel 应优先 → approve 被忽略,不执行"
    loaded = run(store.load(tid))
    tc_msgs = [m for m in loaded.messages if m.role == "tool" and m.tool_call_id == "tc5"]
    assert tc_msgs and "[rejected]" in tc_msgs[-1].content
