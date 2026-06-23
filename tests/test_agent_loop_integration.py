"""test_agent_loop_integration.py — 端到端事务型集成测试 (Task 8 + S6)

涵盖:
  1. 完整链路:plan → read(echo) → control suspend → resume approve → completed
  2. Resume reject:拒绝不执行,循环继续至 completed
  3. 中途中断(迭代 2):未提交边界被回滚,store 仅保留迭代 1
  4. 主 agent 规划 → 子 agent 委派 → 完成(隔离断言)
  S6-A. 全接缝链路组合:plan-spec / allow / verify-fail / deny / control-suspend / resume
  S6-B. repair 接缝:孤立 tool 消息在循环顶部被清除
"""
from __future__ import annotations
import asyncio
from agent_loop.loop import run_loop
from agent_loop.config import LoopConfig, LoopBudget
from agent_loop.conversation import Conversation, InMemoryConversationStore, Boundary
from agent_loop.tools import LoopToolRegistry
from agent_loop.budget import BudgetTracker
from agent_loop.control import FakeControlCapability
from agent_loop.runcontrol import RunControl
from agent_loop.stubs import echo_tool, device_ctrl_tool, add_tool
from agent_loop.plan import PlanState, make_plan_tool
from agent_loop.subagent import make_subagent_tool
from agent_loop.llm import ModelTurn, FakeModelCaller
from agent_loop.messages import Message, ToolCallReq
from agent_loop.gate import DefaultGate
from agent_loop.verify import VerifyVerdict


# ─── 共用工厂 ─────────────────────────────────────────────────────────────────

def _main_cfg(max_iter: int = 10) -> LoopConfig:
    return LoopConfig(
        model="big", max_tokens=200, temperature=0.0, role="main",
        toolset=["plan", "echo", "device_ctrl"],
        budget=LoopBudget(max_iterations=max_iter),
    )


def _make_reg(conv: Conversation) -> LoopToolRegistry:
    reg = LoopToolRegistry()
    reg.register(make_plan_tool(conv.plan))
    reg.register(echo_tool())
    reg.register(device_ctrl_tool())
    return reg


def _seed_conv(thread_id: str = "main") -> Conversation:
    """返回已种入 user 消息的会话(assembler 角色交替要求)。仅用于单次、不重载的场景。"""
    conv = Conversation(thread_id=thread_id)
    conv.append(Message(role="user", content="开始"))
    return conv


def _commit_user_seed(store: InMemoryConversationStore, thread_id: str, text: str = "开始") -> Conversation:
    """模拟服务端职责:入站 user 消息先落库(append-only),再交给 run_loop。

    run_loop 只提交它自己产生的消息(buffer),不持久化入站 user 消息——因为
    恢复路径完全从 store 重载,调用方必须先把 user 消息 commit 进去,否则重载后
    会话缺 user 消息、assembler 角色交替校验失败。seq=0 的 user 边界不带预算快照
    (run_loop 入口因此跳过 restore),后续迭代从 seq=1 起。
    """
    asyncio.run(store.commit(
        thread_id, [Message(role="user", content=text)],
        Boundary(status="user", turn_id="turn-0", seq=0,
                 pending_batch=None, budget_snapshot=None),
    ))
    return asyncio.run(store.load(thread_id))


# ─── Test 1: suspend → resume approve ────────────────────────────────────────

def test_full_chain_plan_read_control_suspend_resume_completes():
    """headline:
    Run1: plan(commit) → echo(commit) → device_ctrl → suspend(awaiting_confirmation)
    Run2(approve): resolve → 继续 → final "已完成" (completed)
    """
    store = InMemoryConversationStore()
    conv = _commit_user_seed(store, "main")
    reg = _make_reg(conv)
    main_cfg = _main_cfg()
    control = FakeControlCapability()

    # 四轮模型调用,同一 FakeModelCaller 实例跨两次 run_loop 共享索引
    fake = FakeModelCaller([
        # turn0: 写计划
        ModelTurn(content="", tool_calls=[ToolCallReq(
            id="p1", name="plan",
            arguments={"items": [
                {"id": "1", "content": "读取设备状态", "status": "todo"},
                {"id": "2", "content": "下发控制", "status": "todo"},
            ]})]),
        # turn1: 读取 echo(普通工具)
        ModelTurn(content="", tool_calls=[ToolCallReq(
            id="e1", name="echo", arguments={"text": "device_status=OK"})]),
        # turn2: 下发控制(控制工具,触发 suspend)
        ModelTurn(content="", tool_calls=[ToolCallReq(
            id="ctl1", name="device_ctrl",
            arguments={"device": "gate-01", "action": "open"})]),
        # turn3: Run2 恢复后的最终答复
        ModelTurn(content="已完成", tool_calls=[]),
    ])

    budget = BudgetTracker(main_cfg.budget)

    # ── Run 1 ──
    res1 = asyncio.run(run_loop(
        main_cfg, conv, reg, budget, fake,
        store=store, control=control,
    ))

    assert res1.status == "awaiting_confirmation", f"期望挂起,得到 {res1.status}"
    assert res1.pending is not None and len(res1.pending) == 1
    assert control.execute_count == 0, "suspend 阶段不应执行"

    # store 最新边界是 awaiting_confirmation
    lb = asyncio.run(store.latest_boundary("main"))
    assert lb is not None and lb.status == "awaiting_confirmation"

    # store.load 里应有 [pending_confirmation] 占位符,tool_call_id == "ctl1"
    loaded = asyncio.run(store.load("main"))
    placeholder_msgs = [
        m for m in loaded.messages
        if m.role == "tool" and m.tool_call_id == "ctl1"
    ]
    assert len(placeholder_msgs) == 1, "期望一条 pending 占位符消息"
    assert placeholder_msgs[0].content == "[pending_confirmation]"

    # ── Run 2 (approve) ──
    # 重新加载会话,新鲜预算(rehydration 通过边界 snapshot 恢复消耗量)
    conv2 = asyncio.run(store.load("main"))
    budget2 = BudgetTracker(main_cfg.budget)   # 新鲜上限;恢复靠 snapshot

    res2 = asyncio.run(run_loop(
        main_cfg, conv2, reg, budget2, fake,
        store=store, control=control,
        resolution={"ctl1": "approve"},
    ))

    # 执行恰好一次(幂等:第二次调用不再 +1)
    assert control.execute_count == 1, f"approve 应执行一次,得 {control.execute_count}"

    # 占位符已替换为真实结果(含 "executed")
    loaded2 = asyncio.run(store.load("main"))
    ctl_msgs = [m for m in loaded2.messages if m.role == "tool" and m.tool_call_id == "ctl1"]
    assert ctl_msgs, "控制工具结果应在 store 中"
    assert "[pending_confirmation]" not in ctl_msgs[-1].content, "占位符应已替换"
    assert "executed" in ctl_msgs[-1].content.lower(), "内容应含 executed"

    # 最终完成
    assert res2.status == "completed", f"期望 completed,得 {res2.status}"
    assert res2.final == "已完成"

    # 预算 rehydration 健全性:budget2 消耗迭代数 > 1(非从零起步)
    assert budget2.snapshot()["iters"] > 1, "budget2 应已还原 Run1 消耗的迭代数"


# ─── Test 2: suspend → resume reject ─────────────────────────────────────────

def test_resume_reject_does_not_execute():
    """reject 路径:control.execute_count 保持 0,占位符替换为 rejected 文本,循环 completed。"""
    store = InMemoryConversationStore()
    conv = _commit_user_seed(store, "main2")
    reg = _make_reg(conv)
    main_cfg = LoopConfig(
        model="big", max_tokens=200, temperature=0.0, role="main",
        toolset=["plan", "echo", "device_ctrl"],
        budget=LoopBudget(max_iterations=10),
    )
    control = FakeControlCapability()

    fake = FakeModelCaller([
        # turn0: plan
        ModelTurn(content="", tool_calls=[ToolCallReq(
            id="p1", name="plan",
            arguments={"items": [{"id": "1", "content": "控制", "status": "todo"}]})]),
        # turn1: 控制工具 → suspend
        ModelTurn(content="", tool_calls=[ToolCallReq(
            id="ctl1", name="device_ctrl",
            arguments={"device": "gate-02", "action": "close"})]),
        # turn2: reject 后继续,模型最终回答
        ModelTurn(content="已拒绝,流程结束", tool_calls=[]),
    ])

    budget = BudgetTracker(main_cfg.budget)

    # Run 1: suspend
    res1 = asyncio.run(run_loop(
        main_cfg, conv, reg, budget, fake,
        store=store, control=control,
    ))
    assert res1.status == "awaiting_confirmation"

    # Run 2: reject
    conv2 = asyncio.run(store.load("main2"))
    budget2 = BudgetTracker(main_cfg.budget)
    res2 = asyncio.run(run_loop(
        main_cfg, conv2, reg, budget2, fake,
        store=store, control=control,
        resolution={"ctl1": "reject"},
    ))

    assert control.execute_count == 0, "reject 不应执行"

    # 占位符替换为 rejected 文本
    loaded = asyncio.run(store.load("main2"))
    ctl_msgs = [m for m in loaded.messages if m.role == "tool" and m.tool_call_id == "ctl1"]
    assert ctl_msgs
    assert "[pending_confirmation]" not in ctl_msgs[-1].content
    assert "rejected" in ctl_msgs[-1].content.lower()

    assert res2.status == "completed"
    assert res2.final == "已拒绝,流程结束"


# ─── Test 3: 中途中断 → 迭代 2 回滚 ─────────────────────────────────────────

def test_interrupt_mid_iteration_rolls_back():
    """机制:自定义 ModelCaller 在返回 turn1(有工具调用)之前设置 rc.request_interrupt()。
    引擎在工具批次执行完毕后做后置中断检查(loop.py 第 205~208 行),
    回滚 conversation.messages[committed_len:]、不提交边界 → store 仅保留迭代 1。
    """
    store = InMemoryConversationStore()
    conv = _seed_conv("intr")
    reg = LoopToolRegistry()
    reg.register(echo_tool())
    cfg = LoopConfig(
        model="big", max_tokens=200, temperature=0.0, role="main",
        toolset=["echo"],
        budget=LoopBudget(max_iterations=10),
    )
    rc = RunControl()

    # 自定义 caller:turn0 正常,turn1 在返回前触发中断
    class InterruptingCaller:
        def __init__(self) -> None:
            self._i = 0

        async def __call__(self, config, messages, tool_schemas) -> ModelTurn:
            i = self._i
            self._i += 1
            if i == 0:
                # 迭代 1:正常 echo 调用,会被 commit
                return ModelTurn(
                    content="",
                    tool_calls=[ToolCallReq(id="e1", name="echo", arguments={"text": "iter1"})],
                )
            elif i == 1:
                # 迭代 2:模型返回前触发中断信号
                rc.request_interrupt()
                return ModelTurn(
                    content="",
                    tool_calls=[ToolCallReq(id="e2", name="echo", arguments={"text": "iter2"})],
                )
            else:
                return ModelTurn(content="完成", tool_calls=[])

    caller = InterruptingCaller()
    budget = BudgetTracker(cfg.budget)

    res = asyncio.run(run_loop(
        cfg, conv, reg, budget, caller,
        store=store, run_control=rc,
    ))

    assert res.status == "interrupted", f"期望 interrupted,得 {res.status}"

    # store 只有一条边界(迭代 1 committed,迭代 2 回滚)
    lb = asyncio.run(store.latest_boundary("intr"))
    assert lb is not None
    assert lb.seq == 1, f"期望 seq=1(只提交迭代1),得 {lb.seq}"

    # store.load 不含迭代 2 的 echo 消息
    loaded = asyncio.run(store.load("intr"))
    iter2_msgs = [
        m for m in loaded.messages
        if m.role == "tool" and m.tool_call_id == "e2"
    ]
    assert not iter2_msgs, "迭代 2 工具消息不应被持久化(回滚)"

    # 迭代 1 的 echo 消息应存在
    iter1_msgs = [
        m for m in loaded.messages
        if m.role == "tool" and m.tool_call_id == "e1"
    ]
    assert iter1_msgs, "迭代 1 工具消息应已 committed"


# ─── Test 4: 主 agent 规划 → 子 agent 委派 → 完成(隔离) ────────────────────

def test_main_plans_then_delegates_then_finishes():
    """迁移自原 test_agent_loop_integration.py:增加 store=InMemoryConversationStore()。
    断言:父会话只见归一化结果"子完成",不见子内部 echo "OK"。
    """
    sub_reg = LoopToolRegistry()
    sub_reg.register(echo_tool())
    sub_cfg = LoopConfig(
        model="light", max_tokens=50, temperature=0.0, role="leaf",
        toolset=["echo"], budget=LoopBudget(max_iterations=4),
    )
    sub_fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="s1", name="echo", arguments={"text": "OK"})]),
        ModelTurn(content="子完成", tool_calls=[]),
    ])
    sub_tool = make_subagent_tool(
        name="worker", description="干活子agent",
        sub_config=sub_cfg, sub_registry=sub_reg, model_caller=sub_fake,
    )
    conv = Conversation(thread_id="main")
    conv.append(Message(role="user", content="开始"))   # seed user(role-alternation)
    main_reg = LoopToolRegistry()
    main_reg.register(sub_tool)
    main_reg.register(make_plan_tool(conv.plan))
    main_fake = FakeModelCaller([
        ModelTurn(content="先规划", tool_calls=[ToolCallReq(id="p1", name="plan",
            arguments={"items": [{"id": "1", "content": "委派", "status": "doing"}]})]),
        ModelTurn(content="委派子agent", tool_calls=[ToolCallReq(id="d1", name="worker", arguments={"task": "干活"})]),
        ModelTurn(content="全部完成", tool_calls=[]),
    ])
    main_cfg = LoopConfig(
        model="big", max_tokens=200, temperature=0.0, role="main",
        toolset=["plan", "worker"], budget=LoopBudget(max_iterations=8),
    )
    budget = BudgetTracker(main_cfg.budget)
    store = InMemoryConversationStore()

    res = asyncio.run(run_loop(main_cfg, conv, main_reg, budget, main_fake, store=store))

    assert res.final == "全部完成" and res.status == "completed"
    assert conv.plan.items[0].content == "委派"
    assert any(m.role == "tool" and "子完成" in m.content for m in conv.messages)
    assert all("OK" != m.content for m in conv.messages if m.role == "tool" and m.name == "echo")


# ─── S6-A: 全接缝链路组合 ─────────────────────────────────────────────────────
#
# 单次 Run1 依序触发以下接缝:
#   1. plan  — items 含 spec 字段 → PlanState 保真存储
#   2. echo  — allow + NullVerifier-like custom verifier pass → 正常结果
#   3. add   — allow + custom Verifier 返回 business_ok=False → is_error=True + [verify-failed]
#   4. echo2 — deny (DefaultGate.denied 谓词命中) → [blocked] 合成消息,handler 未执行
#   5. device_ctrl — ask → suspend, control.execute_count==0, [pending_confirmation]
# Run2 (approve) 继续 → execute_count==1, 最终 completed。
#
# 自定义 Verifier:对 call.id=="add-fail" 返回 business_ok=False,其余放行。

class _VerifyFailOnAddFail:
    """verify 接缝桩:仅对 id=='add-fail' 的调用返回 business_ok=False。"""

    async def verify(self, call, tool, outcome, ctx) -> VerifyVerdict:
        if call.id == "add-fail":
            return VerifyVerdict(business_ok=False, note="业务校验失败(测试)")
        return VerifyVerdict(business_ok=True)   # 其余一律放行(本脚本非 add-fail 调用均 ok)


def test_s6a_full_seam_chain():
    """S6-A:plan-spec / allow / verify-fail / deny / control-suspend / resume 组合验证。"""
    store = InMemoryConversationStore()
    conv = _commit_user_seed(store, "s6a")

    # 注册工具:plan + echo + add + device_ctrl
    reg = LoopToolRegistry()
    reg.register(make_plan_tool(conv.plan))
    reg.register(echo_tool())
    reg.register(add_tool())
    reg.register(device_ctrl_tool())

    cfg = LoopConfig(
        model="big", max_tokens=200, temperature=0.0, role="main",
        toolset=["plan", "echo", "add", "device_ctrl"],
        budget=LoopBudget(max_iterations=15),
    )

    # deny 谓词:拦截 id=="echo-deny" 的调用
    gate = DefaultGate(denied=lambda call, tool: call.id == "echo-deny")
    verifier = _VerifyFailOnAddFail()
    control = FakeControlCapability()

    # 脚本:6 轮模型调用,跨 Run1 + Run2 共享 FakeModelCaller 索引
    fake = FakeModelCaller([
        # turn0 — (1) plan with spec
        ModelTurn(content="", tool_calls=[ToolCallReq(
            id="p1", name="plan",
            arguments={"items": [
                {"id": "s1", "content": "读取状态", "status": "todo",
                 "spec": {"capability": "device_ctrl", "grounded": {"deviceId": "d-3-ac"}}},
                {"id": "s2", "content": "下发控制", "status": "todo"},
            ]})]),
        # turn1 — (2) echo allow + verify pass
        ModelTurn(content="", tool_calls=[ToolCallReq(
            id="echo-ok", name="echo", arguments={"text": "hello"})]),
        # turn2 — (3) add allow + verify FAIL (id=="add-fail")
        ModelTurn(content="", tool_calls=[ToolCallReq(
            id="add-fail", name="add", arguments={"a": 1, "b": 2})]),
        # turn3 — (4) echo deny (id=="echo-deny")
        ModelTurn(content="", tool_calls=[ToolCallReq(
            id="echo-deny", name="echo", arguments={"text": "blocked"})]),
        # turn4 — (5) device_ctrl ask → suspend
        ModelTurn(content="", tool_calls=[ToolCallReq(
            id="ctl-s6a", name="device_ctrl",
            arguments={"device": "gate-s6", "action": "open"})]),
        # turn5 — Run2 resume 后的继续轮(此轮无工具调用 → 终止)
        ModelTurn(content="S6A 全链路完成", tool_calls=[]),
    ])

    budget = BudgetTracker(cfg.budget)

    # ── Run 1 ──
    res1 = asyncio.run(run_loop(
        cfg, conv, reg, budget, fake,
        store=store, control=control,
        gate=gate, verifier=verifier,
    ))

    # (5) 确认 suspend
    assert res1.status == "awaiting_confirmation", f"期望 suspend,得 {res1.status}"
    assert control.execute_count == 0

    # (1) plan spec 保真:items[0].spec 携带 grounded 字段
    assert conv.plan.items[0].spec == {
        "capability": "device_ctrl",
        "grounded": {"deviceId": "d-3-ac"},
    }, f"spec 未正确存储:{conv.plan.items[0].spec!r}"

    # (2) echo-ok 结果正常(不含 verify-failed 或 blocked)
    echo_ok_msgs = [m for m in conv.messages if m.role == "tool" and m.tool_call_id == "echo-ok"]
    assert echo_ok_msgs, "echo-ok 结果消息应存在"
    assert not echo_ok_msgs[0].is_error
    assert "[verify-failed]" not in echo_ok_msgs[0].content
    assert "[blocked]" not in echo_ok_msgs[0].content

    # (3) add-fail → is_error=True + [verify-failed] 前缀
    add_fail_msgs = [m for m in conv.messages if m.role == "tool" and m.tool_call_id == "add-fail"]
    assert add_fail_msgs, "add-fail 结果消息应存在"
    assert add_fail_msgs[0].is_error, "verify 失败应置 is_error=True"
    assert add_fail_msgs[0].content.startswith("[verify-failed]"), (
        f"内容应以 [verify-failed] 开头,实际:{add_fail_msgs[0].content!r}"
    )

    # (4) echo-deny → [blocked] 合成消息
    deny_msgs = [m for m in conv.messages if m.role == "tool" and m.tool_call_id == "echo-deny"]
    assert deny_msgs, "deny 合成消息应存在"
    assert "[blocked]" in deny_msgs[0].content, f"内容应含 [blocked]:{deny_msgs[0].content!r}"

    # (5) device_ctrl 挂起 → [pending_confirmation] 占位符在 store
    loaded1 = asyncio.run(store.load("s6a"))
    ctl_placeholder = [
        m for m in loaded1.messages
        if m.role == "tool" and m.tool_call_id == "ctl-s6a"
    ]
    assert ctl_placeholder and ctl_placeholder[0].content == "[pending_confirmation]"

    # ── Run 2 (approve) ──
    conv2 = asyncio.run(store.load("s6a"))
    budget2 = BudgetTracker(cfg.budget)

    res2 = asyncio.run(run_loop(
        cfg, conv2, reg, budget2, fake,
        store=store, control=control,
        gate=gate, verifier=verifier,
        resolution={"ctl-s6a": "approve"},
    ))

    assert res2.status == "completed", f"期望 completed,得 {res2.status}"
    assert res2.final == "S6A 全链路完成"
    assert control.execute_count == 1, f"approve 应执行一次,得 {control.execute_count}"

    # 占位符已替换为真实 executed 结果
    loaded2 = asyncio.run(store.load("s6a"))
    ctl_msgs = [m for m in loaded2.messages if m.role == "tool" and m.tool_call_id == "ctl-s6a"]
    assert ctl_msgs
    assert "[pending_confirmation]" not in ctl_msgs[-1].content
    assert "executed" in ctl_msgs[-1].content.lower()


# ─── S6-B: repair 接缝端到端 ─────────────────────────────────────────────────
#
# 机制:conversation.messages 含孤立 tool 消息(tool_call_id 无匹配前置 assistant tool_call)。
# run_loop 每轮迭代顶部调用 repair_messages → 孤立消息被丢弃。
# 断言:循环完成后 conversation.messages 中不再含孤立消息。

def test_s6b_repair_removes_orphan_tool_message():
    """S6-B:孤立 tool 消息经由 loop 顶部 repair_messages 被清除。"""
    store = InMemoryConversationStore()
    thread_id = "s6b"

    # 先 commit user 消息(role-alternation 合法性)
    conv = _commit_user_seed(store, thread_id)

    # 在 conversation.messages 里人为插入孤立 tool 消息
    # tool_call_id="orphan-99" 从未出现在任何 assistant tool_calls 里
    orphan = Message(
        role="tool",
        content="[孤立 tool 消息,应被 repair 清除]",
        tool_call_id="orphan-99",
        name="ghost_tool",
    )
    conv.messages.append(orphan)

    # 确认孤立消息已入列
    assert any(m.tool_call_id == "orphan-99" for m in conv.messages), "测试前提:孤立消息已插入"

    reg = LoopToolRegistry()
    reg.register(echo_tool())

    cfg = LoopConfig(
        model="big", max_tokens=200, temperature=0.0, role="main",
        toolset=["echo"],
        budget=LoopBudget(max_iterations=5),
    )

    # 一次 echo 再给 final answer → 正常 completed
    fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(
            id="e-repair", name="echo", arguments={"text": "repair-test"})]),
        ModelTurn(content="repair 完成", tool_calls=[]),
    ])

    budget = BudgetTracker(cfg.budget)

    res = asyncio.run(run_loop(cfg, conv, reg, budget, fake, store=store))

    assert res.status == "completed", f"期望 completed,得 {res.status}"

    # 孤立消息不在最终 conversation.messages 中
    orphan_msgs = [m for m in conv.messages if m.tool_call_id == "orphan-99"]
    assert not orphan_msgs, (
        f"孤立 tool 消息应已被 repair_messages 清除,当前仍存在:{orphan_msgs}"
    )

    # 正常 echo 结果仍在(repair 未过杀)
    echo_msgs = [m for m in conv.messages if m.role == "tool" and m.tool_call_id == "e-repair"]
    assert echo_msgs, "正常 echo 结果应保留"
