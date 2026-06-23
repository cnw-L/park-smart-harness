"""settings.py — 基础设施环境配置聚合 (P4)。

纯读写:仅读取环境变量与默认值,不建立任何连接。
便利工厂 make_redis_store / make_model_caller 只构造对象,不触发 I/O。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .redis_store import RedisConversationStore
    from .providers import OpenAIModelCaller


# ── 本地 90 默认值 ─────────────────────────────────────────────────────────────
_DEFAULT_REDIS_URL = "redis://localhost:6379/0"
_DEFAULT_PG_DSN = "postgresql://postgres:postgres@localhost:5432/smart_park"
_DEFAULT_LLM_BASE_URL = "http://localhost:6008/v1"
_DEFAULT_LLM_API_KEY = "local-vllm-llm"
_DEFAULT_LLM_MODEL = "chat"


@dataclass(frozen=True)
class InfraSettings:
    """基础设施配置快照:Redis + PG + LLM。

    immutable dataclass,可安全在测试中直接构造。
    """
    redis_url: str
    redis_ttl_minutes: int | None
    redis_refresh_on_read: bool
    pg_dsn: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str


def load_infra_settings() -> InfraSettings:
    """从环境变量读取配置,缺失时回落到本地 90 默认值。无任何 I/O。"""
    # Redis URL
    redis_url = os.getenv("ASSISTANT_REDIS_URL") or _DEFAULT_REDIS_URL

    # TTL:空串/未设 → None;有值 → int
    raw_ttl = os.getenv("ASSISTANT_REDIS_CHECKPOINT_TTL_MINUTES", "").strip()
    redis_ttl_minutes: int | None = int(raw_ttl) if raw_ttl else None

    # refresh_on_read:默认 True;"false"/"0"/"" → False
    raw_ror = os.getenv("ASSISTANT_REDIS_CHECKPOINT_REFRESH_ON_READ", "true").strip().lower()
    redis_refresh_on_read = raw_ror not in ("false", "0", "")

    # PG DSN
    pg_dsn = os.getenv("SPA_STORAGE__POSTGRES_DSN") or _DEFAULT_PG_DSN

    # LLM
    llm_base_url = os.getenv("ASSISTANT_LLM_BASE_URL") or _DEFAULT_LLM_BASE_URL
    llm_api_key = os.getenv("ASSISTANT_LLM_API_KEY") or _DEFAULT_LLM_API_KEY
    llm_model = os.getenv("ASSISTANT_LLM_MODEL") or _DEFAULT_LLM_MODEL

    return InfraSettings(
        redis_url=redis_url,
        redis_ttl_minutes=redis_ttl_minutes,
        redis_refresh_on_read=redis_refresh_on_read,
        pg_dsn=pg_dsn,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
    )


# ── 便利工厂(仅构造,不连接) ──────────────────────────────────────────────────

def make_redis_store(settings: InfraSettings, *, key_prefix: str = "agentloop") -> "RedisConversationStore":
    """根据 settings 构造 RedisConversationStore(不建连)。"""
    from .redis_store import RedisConversationStore
    return RedisConversationStore(
        url=settings.redis_url,
        ttl_minutes=settings.redis_ttl_minutes,
        refresh_on_read=settings.redis_refresh_on_read,
        key_prefix=key_prefix,
    )


def make_model_caller(settings: InfraSettings) -> "OpenAIModelCaller":
    """根据 settings 构造 OpenAIModelCaller(不建连)。"""
    from .providers import OpenAIModelCaller
    return OpenAIModelCaller(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )
