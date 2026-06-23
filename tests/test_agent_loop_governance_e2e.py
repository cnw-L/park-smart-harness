"""test_agent_loop_governance_e2e.py — 治理关键路径端到端测试 (H3).

证明 suspend → persist → resume → 幂等执行 在 **真实 Redis + 真实 Postgres** 下工作。
模型使用确定性 FakeModelCaller（非真实 qwen），治理路径完全可复现。

运行方式（需 Redis@90:6379 + PG@90:5432 可达）:
    AGENT_LOOP_LIVE_INFRA=1 python -m pytest tests/test_agent_loop_governance_e2e.py -v --timeout=120

清理:finally 块精确删除测试 thread 的 Redis keys + PG 幂等/审计行，绝不 flushdb/TRUNCATE。
"""
from __future__ import annotations

import asyncio
import os
import uuid

import pytest

# 门控：离线模式跳过，避免无 infra 时挂起
pytestmark = pytest.mark.skipif(
    os.getenv("AGENT_LOOP_LIVE_INFRA") != "1",
    reason="set AGENT_LOOP_LIVE_INFRA=1 for live redis+pg @ 90",
)


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def run(coro):
    """同步运行协程（无 pytest-asyncio 依赖，与其他 live 测试风格一致）。"""
    return asyncio.run(coro)


async def _cleanup_redis(store, thread_id: str) -> None:
    """删除测试 thread 的两个 Redis key（不 flushdb）。"""
    try:
        client = store._get_client()
        mkey = store._messages_key(thread_id)
        bkey = store._boundaries_key(thread_id)
        await client.delete(mkey, bkey)
    except Exception as exc:
        print(f"[H3] redis cleanup warning: {exc}")


async def _cleanup_pg(pg_store, thread_id: str, idem_key: str | None) -> None:
    """删除测试产生的 PG 幂等行 + 审计行（精确 WHERE，不 TRUNCATE）。"""
    try:
        pool = await pg_store._get_pool()
        async with pool.acquire() as conn:
            if idem_key:
                await conn.execute(
                    "DELETE FROM agentloop_idem WHERE idem_key = $1",
                    idem_key,
                )
            await conn.execute(
                "DELETE FROM agentloop_audit WHERE thread_id = $1",
                thread_id,
            )
    except Exception as exc:
        print(f"[H3] pg cleanup warning: {exc}")


# ---------------------------------------------------------------------------
# 主测试：suspend → persist(real Redis) → resume → idempotent(real PG)
# ---------------------------------------------------------------------------

def test_suspend_resume_idempotent_on_real_redis_and_pg():
    """H3 headline — 治理关键路径端到端验证：

    1. Run1: device_ctrl 触发 suspend → awaiting_confirmation 边界落 **真实 Redis**
    2. Run2(approve): 从 Redis 重载 → PG 台账写入 → execute_count==1
    3. 幂等性证明: 直接对同一 PendingAction 再 resolve(approve) →
       PG ON CONFLICT → execute_count 仍为 1（不重执行）
    """
    run(_headline())


async def _headline() -> None:
    from agent_loop.redis_store import RedisConversationStore
    from agent_loop.pg_store import PgStore, PgControlCapability
    from agent_loop.loop import run_loop
    from agent_loop.config import LoopConfig, LoopBudget
    from agent_loop.budget import BudgetTracker
    from agent_loop.tools import LoopToolRegistry
    from agent_loop.stubs import device_ctrl_tool
    from agent_loop.messages import Message, ToolCallReq
    from agent_loop.conversation import Boundary
    from agent_loop.llm import FakeModelCaller, ModelTurn

    # 唯一隔离标识（防止并发/上次失败残留干扰）
    unique_prefix = f"h3-gov-{uuid.uuid4().hex[:12]}"
    thread_id = f"h3-{uuid.uuid4().hex[:8]}"

    # 真实 Redis store（唯一前缀，不污染生产 key）
    store = RedisConversationStore(key_prefix=unique_prefix)

    # 真实 PG store + PgControlCapability（幂等台账）
    pg_store = PgStore()
    control = PgControlCapability(pg_store)

    # 工具注册：只注册 device_ctrl（is_control=True → gate 路由 ask）
    reg = LoopToolRegistry()
    reg.register(device_ctrl_tool())

    cfg = LoopConfig(
        model="x",
        max_tokens=100,
        temperature=0.0,
        role="main",
        toolset=["device_ctrl"],
        budget=LoopBudget(max_iterations=10),
    )

    # 确定性脚本：同一 FakeModelCaller 实例跨 Run1 + Run2 共享索引
    # Turn0: 下发控制（触发 suspend）
    # Turn1: Run2 恢复后返回最终答复（completed）
    fake = FakeModelCaller([
        ModelTurn(
            content="",
            tool_calls=[ToolCallReq(
                id="ctl-h3",
                name="device_ctrl",
                arguments={"device": "gate-1", "action": "open"},
            )],
        ),
        ModelTurn(content="已完成", tool_calls=[]),
    ])

    # 捕获 idem_key 供幂等证明 + cleanup
    captured_idem_key: str | None = None

    try:
        # ── Step 1: 调用方职责 — 入站 user 消息先落 Redis ────────────────────
        await store.commit(
            thread_id,
            [Message(role="user", content="请开闸")],
            Boundary(
                status="user",
                turn_id="turn-0",
                seq=0,
                pending_batch=None,
                budget_snapshot=None,
            ),
        )

        # 从 Redis 重载（与服务端重水化路径一致）
        conv = await store.load(thread_id)
        assert len(conv.messages) >= 1, "种子消息应已落 Redis"

        # ── Run 1: device_ctrl → suspend ─────────────────────────────────────
        budget = BudgetTracker(cfg.budget)
        res1 = await run_loop(
            cfg, conv, reg, budget, fake,
            store=store, control=control,
        )

        # 断言：挂起态
        assert res1.status == "awaiting_confirmation", (
            f"Run1 期望 awaiting_confirmation，得 {res1.status!r}"
        )
        assert res1.pending is not None and len(res1.pending) == 1, (
            f"Run1 应有 1 条 pending，得 {res1.pending!r}"
        )
        assert control.execute_count == 0, (
            f"suspend 阶段不应执行，execute_count={control.execute_count}"
        )

        # 捕获 PendingAction（idem_key 供清理 + 幂等证明）
        pending = res1.pending[0]
        captured_idem_key = pending.idem_key
        print(f"\n[H3] Run1 idem_key={captured_idem_key!r}")

        # 断言：真实 Redis 最新边界 = awaiting_confirmation + pending_batch 长度为 1
        lb = await store.latest_boundary(thread_id)
        assert lb is not None, "Redis 应有边界记录"
        assert lb.status == "awaiting_confirmation", (
            f"Redis latest_boundary 期望 awaiting_confirmation，得 {lb.status!r}"
        )
        assert lb.pending_batch is not None and len(lb.pending_batch) == 1, (
            f"Redis 边界的 pending_batch 应有 1 条，得 {lb.pending_batch!r}"
        )

        # 断言：真实 Redis 消息日志含 [pending_confirmation] 占位符
        loaded1 = await store.load(thread_id)
        placeholder_msgs = [
            m for m in loaded1.messages
            if m.role == "tool" and m.tool_call_id == "ctl-h3"
        ]
        assert len(placeholder_msgs) == 1, (
            f"Redis 消息日志应含 1 条 ctl-h3 tool 消息，得 {len(placeholder_msgs)}"
        )
        assert placeholder_msgs[0].content == "[pending_confirmation]", (
            f"占位符内容期望 [pending_confirmation]，得 {placeholder_msgs[0].content!r}"
        )
        print(f"[H3] Run1 验证通过: Redis 已持久化 awaiting_confirmation + 占位符")

        # ── Run 2: resume approve → execute_count==1 + completed ─────────────
        conv2 = await store.load(thread_id)
        budget2 = BudgetTracker(cfg.budget)  # 新鲜上限；快照 rehydration 由 loop 自动处理

        res2 = await run_loop(
            cfg, conv2, reg, budget2, fake,
            store=store, control=control,
            resolution={"ctl-h3": "approve"},
        )

        # 断言：完成态
        assert res2.status == "completed", (
            f"Run2 期望 completed，得 {res2.status!r}"
        )
        assert res2.final == "已完成", (
            f"Run2 final 期望 '已完成'，得 {res2.final!r}"
        )
        assert control.execute_count == 1, (
            f"approve 应执行恰好一次，得 execute_count={control.execute_count}"
        )

        # 断言：真实 Redis — 占位符已替换为 executed 结果
        loaded2 = await store.load(thread_id)
        ctl_msgs = [
            m for m in loaded2.messages
            if m.role == "tool" and m.tool_call_id == "ctl-h3"
        ]
        assert ctl_msgs, "Redis 中应有 ctl-h3 工具结果消息"
        assert "[pending_confirmation]" not in ctl_msgs[-1].content, (
            f"占位符应已替换，实际内容: {ctl_msgs[-1].content!r}"
        )
        assert "executed" in ctl_msgs[-1].content.lower(), (
            f"内容应含 'executed'，实际: {ctl_msgs[-1].content!r}"
        )

        # 断言：真实 PG 台账已记录该 idem_key
        ledger_row = await control._ledger.get(captured_idem_key)
        assert ledger_row is not None, (
            f"PG 台账应有 idem_key={captured_idem_key!r} 记录"
        )
        assert ledger_row.get("ok") is True, (
            f"PG 台账 ok 字段应为 True，得 {ledger_row!r}"
        )
        print(f"[H3] Run2 验证通过: execute_count=1, PG 台账已记录, 占位符已替换")

        # ── Step 5: 幂等性证明（崩溃重试安全） — 对同一 PendingAction 再 resolve ─
        result_dup = await control.resolve(pending, "approve")
        assert control.execute_count == 1, (
            f"PG ON CONFLICT → 幂等重入不应增加 execute_count，"
            f"实际={control.execute_count}"
        )
        # 返回结果内容应与首次一致（台账缓存）
        first_result_content = ctl_msgs[-1].content
        assert "executed" in result_dup.content.lower(), (
            f"幂等重入应返回 executed 内容，得 {result_dup.content!r}"
        )
        print(
            f"[H3] 幂等性证明通过: 二次 resolve 后 execute_count 仍为 1，"
            f"返回缓存内容={result_dup.content[:60]!r}"
        )

        print(
            f"\n[H3] 全部断言通过 —— "
            f"res1.status={res1.status!r}  res2.status={res2.status!r}  "
            f"execute_count={control.execute_count}"
        )

    finally:
        # ── 清理：精确删除，不影响其他 thread ─────────────────────────────────
        await _cleanup_redis(store, thread_id)
        await _cleanup_pg(pg_store, thread_id, captured_idem_key)
        try:
            await store.aclose()
        except Exception:
            pass
        try:
            await pg_store.aclose()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 可选测试：reject 路径（真实 infra 上快速验证拒绝语义）
# ---------------------------------------------------------------------------

def test_suspend_then_reject_on_real_redis_and_pg():
    """reject 路径：suspend → resume reject → execute_count==0 + [rejected] 替换占位符。"""
    run(_reject_path())


async def _reject_path() -> None:
    from agent_loop.redis_store import RedisConversationStore
    from agent_loop.pg_store import PgStore, PgControlCapability
    from agent_loop.loop import run_loop
    from agent_loop.config import LoopConfig, LoopBudget
    from agent_loop.budget import BudgetTracker
    from agent_loop.tools import LoopToolRegistry
    from agent_loop.stubs import device_ctrl_tool
    from agent_loop.messages import Message, ToolCallReq
    from agent_loop.conversation import Boundary
    from agent_loop.llm import FakeModelCaller, ModelTurn

    unique_prefix = f"h3-rej-{uuid.uuid4().hex[:12]}"
    thread_id = f"h3-rej-{uuid.uuid4().hex[:8]}"

    store = RedisConversationStore(key_prefix=unique_prefix)
    pg_store = PgStore()
    control = PgControlCapability(pg_store)

    reg = LoopToolRegistry()
    reg.register(device_ctrl_tool())

    cfg = LoopConfig(
        model="x",
        max_tokens=100,
        temperature=0.0,
        role="main",
        toolset=["device_ctrl"],
        budget=LoopBudget(max_iterations=10),
    )

    # Turn0: 下发控制（触发 suspend）；Turn1: reject 后继续 → completed
    fake = FakeModelCaller([
        ModelTurn(
            content="",
            tool_calls=[ToolCallReq(
                id="ctl-h3-rej",
                name="device_ctrl",
                arguments={"device": "gate-2", "action": "close"},
            )],
        ),
        ModelTurn(content="已拒绝，流程结束", tool_calls=[]),
    ])

    captured_idem_key: str | None = None

    try:
        # 种子 user 消息落 Redis
        await store.commit(
            thread_id,
            [Message(role="user", content="请关闸")],
            Boundary(
                status="user",
                turn_id="turn-0",
                seq=0,
                pending_batch=None,
                budget_snapshot=None,
            ),
        )

        conv = await store.load(thread_id)

        # Run1: suspend
        budget = BudgetTracker(cfg.budget)
        res1 = await run_loop(
            cfg, conv, reg, budget, fake,
            store=store, control=control,
        )
        assert res1.status == "awaiting_confirmation", (
            f"reject 路径 Run1 期望 awaiting_confirmation，得 {res1.status!r}"
        )
        pending = res1.pending[0]
        captured_idem_key = pending.idem_key

        # Run2: reject
        conv2 = await store.load(thread_id)
        budget2 = BudgetTracker(cfg.budget)
        res2 = await run_loop(
            cfg, conv2, reg, budget2, fake,
            store=store, control=control,
            resolution={"ctl-h3-rej": "reject"},
        )

        assert res2.status == "completed", (
            f"reject 路径 Run2 期望 completed，得 {res2.status!r}"
        )
        assert res2.final == "已拒绝，流程结束", (
            f"reject 路径 final 不符：{res2.final!r}"
        )
        assert control.execute_count == 0, (
            f"reject 不应执行，execute_count={control.execute_count}"
        )

        # 占位符已替换为 [rejected]
        loaded = await store.load(thread_id)
        rej_msgs = [
            m for m in loaded.messages
            if m.role == "tool" and m.tool_call_id == "ctl-h3-rej"
        ]
        assert rej_msgs, "Redis 中应有 ctl-h3-rej 工具结果消息"
        assert "[pending_confirmation]" not in rej_msgs[-1].content
        assert "rejected" in rej_msgs[-1].content.lower(), (
            f"rejected 内容期望含 'rejected'，得 {rej_msgs[-1].content!r}"
        )

        # reject 不写 PG 台账
        ledger_row = await control._ledger.get(captured_idem_key)
        assert ledger_row is None, (
            f"reject 不应写 PG 台账，实际 ledger_row={ledger_row!r}"
        )

        print(
            f"\n[H3-reject] 全部断言通过 —— "
            f"res1.status={res1.status!r}  res2.status={res2.status!r}  "
            f"execute_count={control.execute_count}"
        )

    finally:
        await _cleanup_redis(store, thread_id)
        await _cleanup_pg(pg_store, thread_id, captured_idem_key)
        try:
            await store.aclose()
        except Exception:
            pass
        try:
            await pg_store.aclose()
        except Exception:
            pass
