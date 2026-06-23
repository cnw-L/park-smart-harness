"""test_agent_loop_e2e_smoke.py — 真实模型 + 真实 Redis 端到端冒烟 (P4)。

门槛:AGENT_LOOP_LIVE_INFRA=1
目的:证明 run_loop 在真实 qwen@6008 + 真实 Redis@6379 下能干净终止并持久化。
断言故意 **宽松**:对抗真实模型的不确定性;只断言终止干净 + 数据落库,不断言 exact content。

清理:finally 块删除测试 thread 的 Redis keys(绝不 flushdb)。
"""
from __future__ import annotations

import asyncio
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("AGENT_LOOP_LIVE_INFRA") != "1",
    reason="set AGENT_LOOP_LIVE_INFRA=1 to run real-infra tests",
)


def test_e2e_real_qwen_redis_one_turn():
    """真实 qwen + 真实 Redis:一次 run_loop 干净终止 + 数据持久化。"""
    asyncio.run(_e2e_smoke())


async def _e2e_smoke() -> None:
    from agent_loop.redis_store import RedisConversationStore
    from agent_loop.providers import OpenAIModelCaller
    from agent_loop.loop import run_loop
    from agent_loop.config import LoopConfig, LoopBudget
    from agent_loop.budget import BudgetTracker
    from agent_loop.tools import LoopToolRegistry
    from agent_loop.stubs import echo_tool
    from agent_loop.messages import Message
    from agent_loop.conversation import Boundary

    # 唯一前缀 + thread_id,保证测试隔离
    unique_prefix = f"e2e-smoke-{uuid.uuid4().hex[:12]}"
    thread_id = f"thread-{uuid.uuid4().hex[:8]}"

    store = RedisConversationStore(key_prefix=unique_prefix)

    # 注册 echo 工具
    registry = LoopToolRegistry()
    registry.register(echo_tool())

    # 配置:小预算防止超时;temperature=0 提高确定性
    cfg = LoopConfig(
        model="chat",
        max_tokens=512,
        temperature=0.0,
        role="main",
        toolset=["echo"],
        budget=LoopBudget(max_iterations=4),
    )

    try:
        # ── Step 1: 调用方先把 user 种子消息落库(镜像 _commit_user_seed 合约) ──
        user_content = "请调用 echo 工具回显文本：park-ok,然后告诉我完成了"
        await store.commit(
            thread_id,
            [Message(role="user", content=user_content)],
            Boundary(
                status="user",
                turn_id="turn-0",
                seq=0,
                pending_batch=None,
                budget_snapshot=None,
            ),
        )

        # ── Step 2: 从 store 重载会话(与服务端重水化路径一致) ──────────────────
        conv = await store.load(thread_id)
        assert len(conv.messages) >= 1, "种子消息应已落库"

        # ── Step 3: 调用真实 run_loop ──────────────────────────────────────────
        model = OpenAIModelCaller()  # 使用真实 qwen@6008 默认配置
        budget = BudgetTracker(cfg.budget)

        res = await run_loop(
            cfg, conv, registry, budget, model,
            store=store,
        )

        print(f"\n[e2e-smoke] res.status={res.status!r}  "
              f"final={res.final[:60]!r}  "
              f"messages_in_conv={len(res.conversation.messages)}")

        # ── Step 4: 宽松断言 ─────────────────────────────────────────────────
        # 4a. 循环干净终止(非 failed / interrupted)
        assert res.status in {"completed", "budget_exhausted"}, (
            f"run_loop 应干净终止,实际 status={res.status!r}  reason={res.reason!r}"
        )

        # 4b. 数据已持久化到 Redis
        reloaded = await store.load(thread_id)
        print(f"[e2e-smoke] reloaded messages count: {len(reloaded.messages)}")

        # 至少有种子 user 消息 + ≥1 条 assistant 轮次落库
        assert len(reloaded.messages) >= 2, (
            f"Redis 应至少保存 2 条消息(user seed + assistant),实际 {len(reloaded.messages)}"
        )
        # 必须有至少一条 assistant 消息
        assert any(m.role == "assistant" for m in reloaded.messages), (
            "reloaded 会话中应有 assistant 消息"
        )

        # 4c. 至少写入了一条边界
        lb = await store.latest_boundary(thread_id)
        assert lb is not None, "应有至少一条 Boundary 落库"
        print(f"[e2e-smoke] latest_boundary.status={lb.status!r}  seq={lb.seq}")

    finally:
        # ── 清理:删除测试 thread 的两个 Redis key,绝不 flushdb ──────────────
        try:
            client = store._get_client()
            mkey = store._messages_key(thread_id)
            bkey = store._boundaries_key(thread_id)
            await client.delete(mkey, bkey)
        except Exception as exc:
            print(f"[e2e-smoke] cleanup warning: {exc}")
        finally:
            await store.aclose()
