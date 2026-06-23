"""离线测试 RedisConversationStore — 仅验证构造与配置解析，不做任何 I/O。

此文件**无** AGENT_LOOP_LIVE_INFRA 门槛(不含 pytestmark),CI/离线必跑。
真实 Redis 行为在 test_agent_loop_redis_store.py(live,gated)。
"""
from __future__ import annotations

from agent_loop.redis_store import RedisConversationStore


def test_constructor_resolves_config_without_io(monkeypatch):
    """构造时零 I/O:url/ttl/refresh/key 前缀正确解析,未创建连接。"""
    # 1. 参数直接指定
    store_a = RedisConversationStore(
        url="redis://localhost:1234/9",
        ttl_minutes=10,
        refresh_on_read=False,
        key_prefix="mytest",
    )
    assert store_a._url == "redis://localhost:1234/9"
    assert store_a._ttl_minutes == 10
    assert store_a._refresh_on_read is False
    assert store_a._key_prefix == "mytest"
    assert store_a._client is None  # 未调用任何方法 → 未创建连接

    # 2. 从 env 读取
    monkeypatch.setenv("ASSISTANT_REDIS_URL", "redis://192.168.99.1:6379/3")
    monkeypatch.setenv("ASSISTANT_REDIS_CHECKPOINT_TTL_MINUTES", "15")
    monkeypatch.setenv("ASSISTANT_REDIS_CHECKPOINT_REFRESH_ON_READ", "false")
    store_b = RedisConversationStore(key_prefix="envtest")
    assert store_b._url == "redis://192.168.99.1:6379/3"
    assert store_b._ttl_minutes == 15
    assert store_b._refresh_on_read is False

    # 3. TTL 未设置(空串)→ None
    monkeypatch.setenv("ASSISTANT_REDIS_CHECKPOINT_TTL_MINUTES", "")
    store_c = RedisConversationStore(url="redis://x:1/0")
    assert store_c._ttl_minutes is None

    # 4. key 命名约定
    assert store_c._messages_key("th-42") == "agentloop:th-42:messages"
    assert store_c._boundaries_key("th-42") == "agentloop:th-42:boundaries"

    # 5. 注入 client → 不拥有(不应关闭)
    fake_client = object()
    store_d = RedisConversationStore(url="redis://x:1/0", client=fake_client)
    assert store_d._client is fake_client
    assert store_d._client_owned is False
