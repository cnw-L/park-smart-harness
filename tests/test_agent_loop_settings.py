"""test_agent_loop_settings.py — InfraSettings 离线测试 (P4)。

无 pytestmark / 无 AGENT_LOOP_LIVE_INFRA 门槛:离线 CI 必跑。
只验证纯配置解析,不触发任何 I/O。
"""
from __future__ import annotations

from agent_loop.settings import (
    InfraSettings,
    load_infra_settings,
    make_model_caller,
    make_redis_store,
)

# ── 默认值(env 全未设置) ──────────────────────────────────────────────────────

def test_load_defaults_when_env_unset(monkeypatch):
    """所有 env 未设时回落到本地 90 默认值。"""
    # 清除所有相关 env,保证测试幂等
    for key in [
        "ASSISTANT_REDIS_URL",
        "ASSISTANT_REDIS_CHECKPOINT_TTL_MINUTES",
        "ASSISTANT_REDIS_CHECKPOINT_REFRESH_ON_READ",
        "SPA_STORAGE__POSTGRES_DSN",
        "ASSISTANT_LLM_BASE_URL",
        "ASSISTANT_LLM_API_KEY",
        "ASSISTANT_LLM_MODEL",
    ]:
        monkeypatch.delenv(key, raising=False)

    s = load_infra_settings()

    assert s.redis_url == "redis://localhost:6379/0"
    assert s.redis_ttl_minutes is None
    assert s.redis_refresh_on_read is True
    assert s.pg_dsn == "postgresql://postgres:postgres@localhost:5432/smart_park"
    assert s.llm_base_url == "http://localhost:6008/v1"
    assert s.llm_api_key == "local-vllm-llm"
    assert s.llm_model == "chat"


# ── env 覆盖 ─────────────────────────────────────────────────────────────────

def test_load_reads_env_overrides(monkeypatch):
    """monkeypatch 所有 env 后 settings 反映新值。"""
    monkeypatch.setenv("ASSISTANT_REDIS_URL", "redis://myhost:9999/2")
    monkeypatch.setenv("ASSISTANT_REDIS_CHECKPOINT_TTL_MINUTES", "30")
    monkeypatch.setenv("ASSISTANT_REDIS_CHECKPOINT_REFRESH_ON_READ", "true")
    monkeypatch.setenv("SPA_STORAGE__POSTGRES_DSN", "postgresql://u:p@dbhost:5432/mydb")
    monkeypatch.setenv("ASSISTANT_LLM_BASE_URL", "http://otherhost:8080/v1")
    monkeypatch.setenv("ASSISTANT_LLM_API_KEY", "custom-key")
    monkeypatch.setenv("ASSISTANT_LLM_MODEL", "qwen2.5")

    s = load_infra_settings()

    assert s.redis_url == "redis://myhost:9999/2"
    assert s.redis_ttl_minutes == 30
    assert s.redis_refresh_on_read is True
    assert s.pg_dsn == "postgresql://u:p@dbhost:5432/mydb"
    assert s.llm_base_url == "http://otherhost:8080/v1"
    assert s.llm_api_key == "custom-key"
    assert s.llm_model == "qwen2.5"


# ── TTL 边缘情况 ──────────────────────────────────────────────────────────────

def test_ttl_empty_string_yields_none(monkeypatch):
    """ASSISTANT_REDIS_CHECKPOINT_TTL_MINUTES='' → redis_ttl_minutes=None。"""
    monkeypatch.setenv("ASSISTANT_REDIS_CHECKPOINT_TTL_MINUTES", "")
    monkeypatch.delenv("ASSISTANT_REDIS_URL", raising=False)
    s = load_infra_settings()
    assert s.redis_ttl_minutes is None


def test_ttl_numeric_string_yields_int(monkeypatch):
    """ASSISTANT_REDIS_CHECKPOINT_TTL_MINUTES='10' → redis_ttl_minutes=10。"""
    monkeypatch.setenv("ASSISTANT_REDIS_CHECKPOINT_TTL_MINUTES", "10")
    s = load_infra_settings()
    assert s.redis_ttl_minutes == 10


# ── refresh_on_read 解析 ──────────────────────────────────────────────────────

def test_refresh_false_string(monkeypatch):
    """'false' → refresh_on_read=False。"""
    monkeypatch.setenv("ASSISTANT_REDIS_CHECKPOINT_REFRESH_ON_READ", "false")
    s = load_infra_settings()
    assert s.redis_refresh_on_read is False


def test_refresh_zero_string(monkeypatch):
    """'0' → refresh_on_read=False。"""
    monkeypatch.setenv("ASSISTANT_REDIS_CHECKPOINT_REFRESH_ON_READ", "0")
    s = load_infra_settings()
    assert s.redis_refresh_on_read is False


def test_refresh_unset_defaults_true(monkeypatch):
    """env 未设 → refresh_on_read=True。"""
    monkeypatch.delenv("ASSISTANT_REDIS_CHECKPOINT_REFRESH_ON_READ", raising=False)
    s = load_infra_settings()
    assert s.redis_refresh_on_read is True


# ── InfraSettings 是 frozen dataclass ────────────────────────────────────────

def test_infra_settings_is_immutable():
    """InfraSettings 为 frozen dataclass,赋值应抛 FrozenInstanceError。"""
    import pytest
    s = InfraSettings(
        redis_url="r", redis_ttl_minutes=None, redis_refresh_on_read=True,
        pg_dsn="p", llm_base_url="l", llm_api_key="k", llm_model="m",
    )
    with pytest.raises(Exception):  # FrozenInstanceError(dataclasses)
        s.redis_url = "changed"  # type: ignore[misc]


# ── 便利工厂:不连接 ──────────────────────────────────────────────────────────

def test_make_redis_store_no_connection(monkeypatch):
    """make_redis_store 返回 RedisConversationStore,_client 仍为 None(未连接)。"""
    monkeypatch.delenv("ASSISTANT_REDIS_URL", raising=False)
    s = load_infra_settings()
    store = make_redis_store(s, key_prefix="test-p4")
    # 仅构造,不触发 I/O
    assert store._client is None
    assert store._url == s.redis_url
    assert store._key_prefix == "test-p4"


def test_make_model_caller_no_connection(monkeypatch):
    """make_model_caller 返回 OpenAIModelCaller,_client 仍为 None(未连接)。"""
    monkeypatch.delenv("ASSISTANT_LLM_BASE_URL", raising=False)
    s = load_infra_settings()
    caller = make_model_caller(s)
    # 惰性 client:只有调用 __call__ 才建连
    assert caller._client is None
    assert caller._base_url == s.llm_base_url
    assert caller._model == s.llm_model
