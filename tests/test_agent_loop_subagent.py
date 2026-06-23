"""Tests for make_subagent_tool (Task 7 + H2).

覆盖:
- 基础隔离 + 正常完成
- 深度上限阻断递归
- 子模型错误 → 父得到 error="model_error"
- 工厂拒绝控制工具
- 预算共享:子迭代消耗父预算
- H2: 共享父中断信号(父已中断 → 子立即返回 interrupted)
- H2: run_control=None 时退化为独立 RunControl(正常运行)
- H2: uuid thread_id 不碰撞
"""
import asyncio
import pytest

from agent_loop.subagent import make_subagent_tool
from agent_loop.config import LoopConfig, LoopBudget
from agent_loop.conversation import InMemoryConversationStore
from agent_loop.tools import LoopTool, LoopToolRegistry, ToolContext, ToolResult
from agent_loop.budget import BudgetTracker
from agent_loop.runcontrol import RunControl
from agent_loop.stubs import echo_tool
from agent_loop.llm import ModelTurn, FakeModelCaller
from agent_loop.messages import ToolCallReq


# ─── 辅助 ────────────────────────────────────────────────────────────────────

def _sub_cfg(max_iter: int = 10, max_depth: int = 3, toolset=None) -> LoopConfig:
    return LoopConfig(
        model="light", max_tokens=50, temperature=0.0, role="leaf",
        toolset=toolset if toolset is not None else ["echo"],
        budget=LoopBudget(max_iterations=max_iter),
        max_depth=max_depth,
    )


def run(coro):
    return asyncio.run(coro)


# ─── 1. 基础隔离:父会话不含子内部消息,只得到归一化结果 ──────────────────────

def test_subagent_isolated_returns_only_result():
    """子 run_loop 完成后父只看到归一化 ToolResult;子内部消息不污染父。"""
    sub_reg = LoopToolRegistry()
    sub_reg.register(echo_tool())
    sub_cfg = _sub_cfg()
    sub_fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="s1", name="echo", arguments={"text": "子结果"})]),
        ModelTurn(content="子完成:子结果", tool_calls=[]),
    ])

    sub_tool = make_subagent_tool(
        name="echo_agent", description="子agent",
        sub_config=sub_cfg, sub_registry=sub_reg, model_caller=sub_fake,
    )

    shared = BudgetTracker(LoopBudget(max_iterations=10))
    ctx = ToolContext(budget=shared, depth=0)
    result = run(sub_tool.handler({"task": "做点事"}, ctx))

    assert result.ok
    assert "子完成" in result.content
    # 子消耗了 2 次迭代(工具轮 + 答案轮)
    assert shared._iters >= 2


# ─── 2. 深度上限阻断递归 ─────────────────────────────────────────────────────

def test_depth_limit_blocks_recursion():
    """ctx.depth + 1 > max_depth 时立即返回失败,不调用 run_loop。"""
    sub_cfg = _sub_cfg(max_depth=1)
    sub_tool = make_subagent_tool(
        name="a", description="d",
        sub_config=sub_cfg, sub_registry=LoopToolRegistry(),
        model_caller=FakeModelCaller([ModelTurn(content="x", tool_calls=[])]),
    )
    ctx = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=10)), depth=1)
    result = run(sub_tool.handler({"task": "t"}, ctx))

    assert not result.ok
    assert "depth" in (result.error or "")


# ─── 3. 子模型错误 → 父得到 error="model_error" ──────────────────────────────

def test_sub_model_error_surfaces_typed_reason():
    """子 FakeModelCaller 抛异常 → sub run_loop 返回 status=failed reason=model_error
    → 父 ToolResult.error == "model_error"(不是泛型 "failed")。"""
    class AlwaysFailCaller:
        async def __call__(self, config, messages, tool_schemas):
            raise RuntimeError("模型调用失败(测试注入)")

    sub_reg = LoopToolRegistry()
    sub_cfg = _sub_cfg(toolset=[])  # 无工具,模型调用失败直接触发 model_error
    sub_tool = make_subagent_tool(
        name="fail_agent", description="必然失败的子",
        sub_config=sub_cfg, sub_registry=sub_reg,
        model_caller=AlwaysFailCaller(),
    )

    ctx = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=20)), depth=0)
    result = run(sub_tool.handler({"task": "注定失败"}, ctx))

    assert not result.ok
    assert result.error == "model_error", f"期望 model_error,实际={result.error!r}"


# ─── 4. 工厂拒绝控制工具 ─────────────────────────────────────────────────────

def test_factory_rejects_control_tool_in_toolset():
    """sub_config.toolset 中包含 is_control=True 的工具时,make_subagent_tool 应抛 ValueError。"""
    ctrl_tool = LoopTool(
        name="door_open",
        description="开门(控制动作)",
        parameters={"type": "object", "properties": {}},
        handler=None,  # type: ignore[arg-type]
        is_control=True,
    )
    sub_reg = LoopToolRegistry()
    sub_reg.register(ctrl_tool)

    sub_cfg = _sub_cfg(toolset=["door_open"])

    with pytest.raises(ValueError, match="control tool 'door_open'"):
        make_subagent_tool(
            name="bad_agent", description="含控制工具的子",
            sub_config=sub_cfg, sub_registry=sub_reg,
            model_caller=FakeModelCaller([]),
        )


# ─── 5. 预算共享:子消耗父预算 ───────────────────────────────────────────────

def test_sub_iterations_consume_parent_budget():
    """子循环迭代应从共享 BudgetTracker 中扣减,父预算在调用后减少。"""
    sub_reg = LoopToolRegistry()
    sub_reg.register(echo_tool())
    sub_cfg = _sub_cfg()
    sub_fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="t1", name="echo", arguments={"text": "a"})]),
        ModelTurn(content="done", tool_calls=[]),
    ])
    sub_tool = make_subagent_tool(
        name="budget_sub", description="预算共享测试",
        sub_config=sub_cfg, sub_registry=sub_reg, model_caller=sub_fake,
    )

    shared = BudgetTracker(LoopBudget(max_iterations=20))
    before = shared._iters  # 应为 0
    ctx = ToolContext(budget=shared, depth=0)
    result = run(sub_tool.handler({"task": "消耗预算"}, ctx))

    assert result.ok
    assert shared._iters > before, "子迭代应消耗父预算"
    assert shared._iters - before >= 2  # 至少 2 次(工具轮 + 答案轮)


# ─── H2-1. 父已中断 → 子立即返回 interrupted ─────────────────────────────────

def test_shared_interrupt_halts_subagent():
    """H2:ctx.run_control 已置中断时,子 run_loop 在迭代顶检查 rc.interrupted → 返回
    interrupted;handler 映射为 ToolResult(ok=False, error="interrupted")。

    对比修复前:旧代码用独立 sub_rc = RunControl(),父的中断对子不可见,
    子会继续尝试调用模型。本测试断言子现在能感知父中断。
    """
    sub_reg = LoopToolRegistry()
    sub_reg.register(echo_tool())
    sub_cfg = _sub_cfg()
    # FakeModelCaller 有内容但不应被调用到:子在迭代顶就因 rc.interrupted 退出
    sub_fake = FakeModelCaller([
        ModelTurn(content="不应出现", tool_calls=[]),
    ])

    sub_tool = make_subagent_tool(
        name="interrupt_sub", description="共享中断测试子",
        sub_config=sub_cfg, sub_registry=sub_reg, model_caller=sub_fake,
    )

    # 父中断信号:在调用 handler 前已置位
    parent_rc = RunControl()
    parent_rc.request_interrupt()

    ctx = ToolContext(
        budget=BudgetTracker(LoopBudget(max_iterations=10)),
        depth=0,
        run_control=parent_rc,  # 共享父中断信号
    )
    result = run(sub_tool.handler({"task": "应被中断"}, ctx))

    assert not result.ok, "父已中断,子应返回失败"
    assert result.error == "interrupted", f"期望 interrupted,实际={result.error!r}"


# ─── H2-2. run_control=None 退化为独立 RunControl,子正常运行 ─────────────────

def test_subagent_runs_normally_when_no_parent_run_control():
    """H2:ToolContext.run_control=None(默认)时,子创建自己的 RunControl 并正常完成。
    保证后向兼容:在循环外直接调用工具时不会因缺少 run_control 而崩溃。
    """
    sub_reg = LoopToolRegistry()
    sub_reg.register(echo_tool())
    sub_cfg = _sub_cfg()
    sub_fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="h2t1", name="echo", arguments={"text": "ok"})]),
        ModelTurn(content="完成", tool_calls=[]),
    ])

    sub_tool = make_subagent_tool(
        name="no_rc_sub", description="无父 RunControl 测试",
        sub_config=sub_cfg, sub_registry=sub_reg, model_caller=sub_fake,
    )

    # run_control 不传 → 默认 None
    ctx = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=10)), depth=0)
    result = run(sub_tool.handler({"task": "正常运行"}, ctx))

    assert result.ok, f"无父 RunControl 时子应正常完成,实际 error={result.error!r}"
    assert "完成" in result.content


# ─── H2-3. uuid thread_id 不碰撞 ─────────────────────────────────────────────

def test_uuid_thread_id_no_collision():
    """H2:多次调用同一 subagent handler 产生的 sub_conv.thread_id 应各不相同。
    通过 monkeypatch 捕获实际 Conversation 构造参数来验证唯一性。
    """
    import agent_loop.subagent as _subagent_mod
    from agent_loop import conversation as _conv_mod

    thread_ids: list[str] = []
    _orig_conversation = _conv_mod.Conversation

    class _CapturingConversation(_orig_conversation):  # type: ignore[misc]
        def __init__(self, *, thread_id: str) -> None:
            thread_ids.append(thread_id)
            super().__init__(thread_id=thread_id)

    sub_reg = LoopToolRegistry()
    sub_reg.register(echo_tool())
    sub_cfg = _sub_cfg()

    sub_tool = make_subagent_tool(
        name="uuid_sub", description="uuid 测试",
        sub_config=sub_cfg, sub_registry=sub_reg,
        model_caller=FakeModelCaller([
            ModelTurn(content="done1", tool_calls=[]),
            ModelTurn(content="done2", tool_calls=[]),
        ]),
    )

    import agent_loop.subagent as _sub_mod
    original_conv = _sub_mod.Conversation

    # monkeypatch subagent 模块中的 Conversation
    _sub_mod.Conversation = _CapturingConversation  # type: ignore[attr-defined]
    try:
        ctx1 = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=20)), depth=0)
        ctx2 = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=20)), depth=0)
        run(sub_tool.handler({"task": "第一次"}, ctx1))
        run(sub_tool.handler({"task": "第二次"}, ctx2))
    finally:
        _sub_mod.Conversation = original_conv  # type: ignore[attr-defined]

    # 过滤出 uuid_sub 前缀的 thread_id
    sub_ids = [tid for tid in thread_ids if tid.startswith("uuid_sub:")]
    assert len(sub_ids) >= 2, f"期望至少2个子会话 thread_id,实际={sub_ids}"
    assert sub_ids[0] != sub_ids[1], f"uuid thread_id 不应碰撞:{sub_ids}"


# ─── P0①: 子 agent 接中圈(assembler + principal 透传) ───────────────────────

def test_subagent_inherits_parent_principal():
    """父 ctx.principal 透传到子会话 → 子工具看到同一身份(子知识检索按身份过滤的前提)。"""
    seen = {}

    async def _probe(args, ctx):
        seen["principal"] = ctx.principal
        return ToolResult(ok=True, content="ok")

    sub_reg = LoopToolRegistry()
    sub_reg.register(LoopTool(name="probe", description="",
                              parameters={"type": "object", "properties": {}}, handler=_probe))
    sub_tool = make_subagent_tool(
        name="probe_agent", description="探针子",
        sub_config=_sub_cfg(toolset=["probe"]), sub_registry=sub_reg,
        model_caller=FakeModelCaller([
            ModelTurn(content="", tool_calls=[ToolCallReq(id="s1", name="probe", arguments={})]),
            ModelTurn(content="done", tool_calls=[]),
        ]),
    )
    sentinel = object()        # engine-opaque 身份对象
    ctx = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=10)), depth=0, principal=sentinel)
    result = run(sub_tool.handler({"task": "t"}, ctx))
    assert result.ok
    assert seen["principal"] is sentinel        # 同一身份对象透到子工具


def test_subagent_injected_assembler_yields_device_sub_profile():
    """注入 ParkContextAssembler + role='leaf' → 子系统头是 device_sub 档(只读不控制),非 main 档。"""
    from agent_context.assembler import ParkContextAssembler

    captured = {}

    class CapturingCaller:
        async def __call__(self, config, messages, tool_schemas):
            captured.setdefault("messages", messages)
            return ModelTurn(content="子完成", tool_calls=[])

    sub_tool = make_subagent_tool(
        name="dev_agent", description="设备子",
        sub_config=_sub_cfg(toolset=[]), sub_registry=LoopToolRegistry(),
        model_caller=CapturingCaller(),
        assembler=ParkContextAssembler(),
    )
    ctx = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=10)), depth=0)
    result = run(sub_tool.handler({"task": "查3号楼空调"}, ctx))
    assert result.ok
    sys_msg = captured["messages"][0]
    assert sys_msg.role == "system"
    assert "只读不控制" in (sys_msg.content or "")     # device_sub 档生效
    assert "总入口" not in (sys_msg.content or "")      # 确认不是 main 档(裸桩也不会有这句)
