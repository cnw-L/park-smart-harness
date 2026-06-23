"""redis_store.py — Redis 热会话存储，实现 ConversationStore 协议 (P2).

设计要点（§六补 storage）:
- 每个 thread_id 对应两个 Redis LIST:
    {prefix}:{thread_id}:messages   — JSON 字符串列表（一条 = 一个 Message）
    {prefix}:{thread_id}:boundaries — JSON 字符串列表（一条 = 一个 Boundary）
- commit() 用 MULTI/EXEC pipeline 原子写入（RPUSH messages + RPUSH boundary）。
- awaiting_confirmation 边界 → 给两个 key 设置 EXPIRE（挂起 TTL）。
- 非挂起（正常）边界 → PERSIST 两个 key（移除 TTL，活跃会话不超时）。
- refresh_on_read=True 且当前最新边界为 awaiting_confirmation → load() 时刷新 TTL。
- resolve_pending(): LRANGE 读 → 原地替换 tool 占位符 → DELETE+RPUSH+RPUSH in pipeline
  （单线程/单 writer 假设：§六补 规定每个 thread_id 同一时刻至多一个 pending 集，
  由上层保证单 writer，DELETE+RPUSH 序列不存在并发冲突）。
- 序列化全部经由 codec.py（encode_message/decode_message/encode_boundary/decode_boundary）。
"""
from __future__ import annotations

import json
import os
from typing import Any

from .codec import (
    decode_boundary,
    decode_message,
    encode_boundary,
    encode_message,
)
from .messages import Message
from .conversation import Boundary, Conversation
from .plan import derive_plan


class RedisConversationStore:
    """Redis 持久化会话存储，满足 ConversationStore 协议。

    参数:
        url          : Redis URL；若为 None → 读 ASSISTANT_REDIS_URL env → 默认 redis://localhost:6379/0
        ttl_minutes  : 挂起 TTL 分钟数；None → 不设 TTL；
                       可通过 ASSISTANT_REDIS_CHECKPOINT_TTL_MINUTES env 设置（空/缺 → None）。
        refresh_on_read: 读取时若最新边界为 awaiting_confirmation 是否刷新 TTL；
                         默认 True；可通过 ASSISTANT_REDIS_CHECKPOINT_REFRESH_ON_READ env 控制。
        key_prefix   : Redis key 前缀（默认 "agentloop"）。
        client       : 可注入的 redis.asyncio.Redis 实例（测试用）；为 None 时延迟创建。
    """

    def __init__(
        self,
        *,
        url: str | None = None,
        ttl_minutes: int | None = None,
        refresh_on_read: bool | None = None,
        key_prefix: str = "agentloop",
        client: Any = None,
    ) -> None:
        # --- URL 解析 ---
        if url is None:
            url = os.getenv("ASSISTANT_REDIS_URL", "redis://localhost:6379/0")
        self._url = url

        # --- TTL 解析 ---
        if ttl_minutes is None:
            raw_ttl = os.getenv("ASSISTANT_REDIS_CHECKPOINT_TTL_MINUTES", "")
            ttl_minutes = int(raw_ttl) if raw_ttl.strip() else None
        self._ttl_minutes = ttl_minutes

        # --- refresh_on_read 解析 ---
        if refresh_on_read is None:
            raw_ror = os.getenv("ASSISTANT_REDIS_CHECKPOINT_REFRESH_ON_READ", "true")
            refresh_on_read = raw_ror.strip().lower() not in ("0", "false", "no", "")
        self._refresh_on_read = refresh_on_read

        self._key_prefix = key_prefix

        # --- client ---
        self._client = client
        self._client_owned = client is None  # 若非注入则我们负责关闭

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """延迟创建 Redis 客户端（第一次真实 I/O 时才建连）。"""
        if self._client is None:
            import redis.asyncio as aioredis  # type: ignore[import]
            self._client = aioredis.Redis.from_url(self._url, decode_responses=True)
        return self._client

    def _messages_key(self, thread_id: str) -> str:
        return f"{self._key_prefix}:{thread_id}:messages"

    def _boundaries_key(self, thread_id: str) -> str:
        return f"{self._key_prefix}:{thread_id}:boundaries"

    def _ttl_seconds(self) -> int | None:
        if self._ttl_minutes is None:
            return None
        return self._ttl_minutes * 60

    async def _apply_ttl_or_persist(
        self, client: Any, thread_id: str, is_suspended: bool
    ) -> None:
        """根据边界状态决定是 EXPIRE 还是 PERSIST。

        is_suspended=True  (awaiting_confirmation) + ttl 已配置 → EXPIRE 两个 key。
        is_suspended=False (正常 iteration/completed 等) + ttl 已配置 → PERSIST 两个 key
            （活跃会话恢复后不应因 TTL 超时丢数据）。
        未配置 TTL → 无操作。
        """
        ttl = self._ttl_seconds()
        if ttl is None:
            return
        mkey = self._messages_key(thread_id)
        bkey = self._boundaries_key(thread_id)
        if is_suspended:
            await client.expire(mkey, ttl)
            await client.expire(bkey, ttl)
        else:
            # PERSIST 移除 TTL，保障活跃会话不因旧的挂起 TTL 过期
            await client.persist(mkey)
            await client.persist(bkey)

    # ------------------------------------------------------------------
    # ConversationStore 协议实现
    # ------------------------------------------------------------------

    async def commit(
        self,
        thread_id: str,
        new_messages: list[Message],
        boundary: Boundary,
    ) -> None:
        """原子追加 new_messages 和 boundary。

        使用 MULTI/EXEC pipeline：RPUSH messages … + RPUSH boundaries …
        两步在同一事务内执行，保证不出现「消息写入但边界未写」的撕裂状态。
        """
        client = self._get_client()
        mkey = self._messages_key(thread_id)
        bkey = self._boundaries_key(thread_id)

        # 序列化
        encoded_msgs = [json.dumps(encode_message(m)) for m in new_messages]
        encoded_boundary = json.dumps(encode_boundary(boundary))

        # MULTI/EXEC 原子写入
        async with client.pipeline(transaction=True) as pipe:
            if encoded_msgs:
                pipe.rpush(mkey, *encoded_msgs)
            pipe.rpush(bkey, encoded_boundary)
            await pipe.execute()

        # TTL / PERSIST 处理（在事务外，单独命令；非原子但可接受）。
        # 失败窗口(进程在 EXEC 后、本命令前崩溃,约一个 RTT):
        #   挂起侧 → 该挂起会话无 TTL、永不过期(资源泄漏,可容忍);
        #   恢复侧 → 恢复中的活跃会话仍持旧挂起 TTL,极小窗口内可能过期(风险更高,但窗口极小)。
        is_suspended = boundary.status == "awaiting_confirmation"
        await self._apply_ttl_or_persist(client, thread_id, is_suspended)

    async def load(self, thread_id: str) -> Conversation:
        """加载 thread 的已提交消息。

        因为 commit() 使用 MULTI/EXEC 原子写入，消息列表与边界列表始终同步，
        不存在撕裂尾巴（torn tail），直接返回全部消息。

        若 refresh_on_read=True 且最新边界为 awaiting_confirmation，刷新 TTL
        （延长挂起窗口，防止正在等待用户确认时 key 到期）。
        """
        client = self._get_client()
        mkey = self._messages_key(thread_id)
        bkey = self._boundaries_key(thread_id)

        raw_msgs = await client.lrange(mkey, 0, -1)
        if not raw_msgs:
            return Conversation(thread_id=thread_id)

        messages = [decode_message(json.loads(s)) for s in raw_msgs]

        # refresh_on_read: 若最新边界为 awaiting_confirmation，刷新 TTL
        if self._refresh_on_read and self._ttl_seconds() is not None:
            raw_last = await client.lindex(bkey, -1)
            if raw_last is not None:
                last_b = decode_boundary(json.loads(raw_last))
                if last_b.status == "awaiting_confirmation":
                    ttl = self._ttl_seconds()
                    await client.expire(mkey, ttl)
                    await client.expire(bkey, ttl)

        conv = Conversation(thread_id=thread_id, messages=messages)
        # 从消息日志派生 plan 投影（Claude TodoWrite 式：取最近一条 plan 调用快照）
        conv.plan = derive_plan(messages)
        return conv

    async def latest_boundary(self, thread_id: str) -> Boundary | None:
        """返回最近一次已提交的 Boundary，或 None（thread 不存在/为空）。"""
        client = self._get_client()
        bkey = self._boundaries_key(thread_id)
        raw = await client.lindex(bkey, -1)
        if raw is None:
            return None
        return decode_boundary(json.loads(raw))

    async def resolve_pending(
        self,
        thread_id: str,
        resolved: dict[str, Any],
        boundary: Boundary,
    ) -> None:
        """原地替换 tool 占位符消息，并追加新边界（MULTI/EXEC）。

        读取全量消息 → 在内存中替换匹配 tool_call_id 的 tool 消息 → pipeline:
            DEL messages_key
            RPUSH messages_key <重新编码的消息列表>
            RPUSH boundaries_key <新边界>
        执行一次事务。

        单 writer 假设（§六补）：每个 thread_id 同一时刻至多一个 pending 集，
        由上层 gate/control 保证无并发 resolve，因此 read-modify-write 不加 WATCH。
        """
        client = self._get_client()
        mkey = self._messages_key(thread_id)
        bkey = self._boundaries_key(thread_id)

        # 读取当前消息列表（原地替换前的快照）
        raw_msgs = await client.lrange(mkey, 0, -1)
        messages = [decode_message(json.loads(s)) for s in raw_msgs]

        # 原地替换匹配 tool_call_id 的 tool 消息
        for i, m in enumerate(messages):
            if m.role == "tool" and m.tool_call_id in resolved:
                messages[i] = resolved[m.tool_call_id]

        # 重新序列化
        encoded_msgs = [json.dumps(encode_message(m)) for m in messages]
        encoded_boundary = json.dumps(encode_boundary(boundary))

        # MULTI/EXEC 原子重写
        async with client.pipeline(transaction=True) as pipe:
            pipe.delete(mkey)
            if encoded_msgs:
                pipe.rpush(mkey, *encoded_msgs)
            pipe.rpush(bkey, encoded_boundary)
            await pipe.execute()

        # TTL / PERSIST 处理
        is_suspended = boundary.status == "awaiting_confirmation"
        await self._apply_ttl_or_persist(client, thread_id, is_suspended)

    async def aclose(self) -> None:
        """关闭 Redis 连接（仅关闭我们自己创建的 client）。"""
        if self._client is not None and self._client_owned:
            await self._client.aclose()
            self._client = None
