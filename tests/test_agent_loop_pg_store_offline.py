"""离线测试 PgStore / PgControlCapability — 仅验证构造与配置解析，不做任何 I/O。

此文件**无** AGENT_LOOP_LIVE_INFRA 门槛（不含 pytestmark），CI/离线必跑。
真实 Postgres 行为在 test_agent_loop_pg_store.py（live，gated）。

学自 P2 redis 离线测试教训：module 级 pytestmark skipif 会把同文件所有测试都跳过，
所以离线测试必须放独立文件。
"""
from __future__ import annotations

import os

import pytest

from agent_loop.pg_store import (
    PgControlCapability,
    PgIdempotencyLedger,
    PgStore,
    _DEFAULT_DSN,
    _resolve_dsn,
)


# ---------------------------------------------------------------------------
# _resolve_dsn 函数
# ---------------------------------------------------------------------------

def test_resolve_dsn_explicit_arg(monkeypatch):
    """参数直接指定时优先级最高，忽略 env。"""
    monkeypatch.setenv("SPA_STORAGE__POSTGRES_DSN", "postgresql://env/env_db")
    result = _resolve_dsn("postgresql://explicit/db")
    assert result == "postgresql://explicit/db"


def test_resolve_dsn_from_env(monkeypatch):
    """参数为 None → 读 SPA_STORAGE__POSTGRES_DSN env。"""
    monkeypatch.setenv("SPA_STORAGE__POSTGRES_DSN", "postgresql://envhost:5432/envdb")
    result = _resolve_dsn(None)
    assert result == "postgresql://envhost:5432/envdb"


def test_resolve_dsn_default(monkeypatch):
    """env 也未设置时返回内置默认 DSN。"""
    monkeypatch.delenv("SPA_STORAGE__POSTGRES_DSN", raising=False)
    result = _resolve_dsn(None)
    assert result == _DEFAULT_DSN


# ---------------------------------------------------------------------------
# PgStore 构造（零 I/O）
# ---------------------------------------------------------------------------

def test_pg_store_explicit_dsn_no_pool_created():
    """dsn 参数直接指定：_pool 为 None（懒建），_schema_ready=False。"""
    store = PgStore(dsn="postgresql://localhost:5432/testdb")
    assert store._dsn == "postgresql://localhost:5432/testdb"
    assert store._pool is None, "构造时不应建立连接"
    assert store._pool_owned is True
    assert store._schema_ready is False


def test_pg_store_env_dsn(monkeypatch):
    """dsn=None → 从 env 读取。"""
    monkeypatch.setenv("SPA_STORAGE__POSTGRES_DSN", "postgresql://envhost/envdb")
    store = PgStore()
    assert store._dsn == "postgresql://envhost/envdb"
    assert store._pool is None


def test_pg_store_default_dsn(monkeypatch):
    """dsn=None，env 未设 → 内置默认。"""
    monkeypatch.delenv("SPA_STORAGE__POSTGRES_DSN", raising=False)
    store = PgStore()
    assert store._dsn == _DEFAULT_DSN


def test_pg_store_injected_pool_not_owned():
    """注入 pool → _pool_owned=False（不应由 store 关闭）。"""
    fake_pool = object()
    store = PgStore(dsn="postgresql://x:5432/y", pool=fake_pool)
    assert store._pool is fake_pool
    assert store._pool_owned is False


def test_pg_store_injected_pool_is_set_immediately():
    """注入的 pool 在构造后即可访问，无需任何 I/O。"""
    fake_pool = object()
    store = PgStore(pool=fake_pool)
    assert store._pool is fake_pool


# ---------------------------------------------------------------------------
# PgIdempotencyLedger 构造（零 I/O）
# ---------------------------------------------------------------------------

def test_pg_ledger_wraps_store():
    """PgIdempotencyLedger 持有传入的 store 引用。"""
    store = PgStore(dsn="postgresql://x/y")
    ledger = PgIdempotencyLedger(store)
    assert ledger._store is store


# ---------------------------------------------------------------------------
# PgControlCapability 构造与 freeze（零 I/O）
# ---------------------------------------------------------------------------

def test_pg_control_freeze_returns_pending():
    """freeze 同步且无 I/O：应铸造带非空 idem_key 的 PendingAction。"""
    from agent_loop.messages import ToolCallReq

    store = PgStore(dsn="postgresql://x/y")
    cap = PgControlCapability(store)

    call = ToolCallReq(id="tc-offline-1", name="open_gate", arguments={"gate_id": "G1"})
    pending = cap.freeze(call)

    assert pending.idem_key, "idem_key 不应为空"
    assert pending.tool_call_id == "tc-offline-1"
    assert pending.frozen_action["name"] == "open_gate"
    assert pending.frozen_action["arguments"] == {"gate_id": "G1"}


def test_pg_control_freeze_copies_arguments():
    """frozen_action 是 arguments 的副本：外部修改不污染冻结状态。"""
    from agent_loop.messages import ToolCallReq

    store = PgStore(dsn="postgresql://x/y")
    cap = PgControlCapability(store)

    args = {"gate_id": "G1"}
    call = ToolCallReq(id="tc-offline-2", name="open_gate", arguments=args)
    pending = cap.freeze(call)

    args["gate_id"] = "MUTATED"
    assert pending.frozen_action["arguments"]["gate_id"] == "G1"


def test_pg_control_freeze_unique_idem_keys():
    """两次 freeze 产生不同 idem_key（UUID 碰撞概率可忽略）。"""
    from agent_loop.messages import ToolCallReq

    store = PgStore(dsn="postgresql://x/y")
    cap = PgControlCapability(store)

    call = ToolCallReq(id="tc-offline-3", name="open_gate", arguments={})
    p1 = cap.freeze(call)
    p2 = cap.freeze(call)
    assert p1.idem_key != p2.idem_key


def test_pg_control_execute_count_starts_zero():
    """构造后 execute_count 为 0。"""
    store = PgStore(dsn="postgresql://x/y")
    cap = PgControlCapability(store)
    assert cap.execute_count == 0


def test_pg_store_pool_none_until_io():
    """注入池为 None 时，_pool 保持 None 直到首次 I/O（不会在构造时触发）。"""
    store = PgStore(dsn="postgresql://localhost/nonexistent_db_offline")
    # 构造后 pool 为 None，schema_ready 为 False — 无任何 I/O 发生
    assert store._pool is None
    assert store._schema_ready is False


def test_pg_ledger_has_update_method():
    """WAL 第二阶段:PgIdempotencyLedger 需有 update(in_flight→done/failed)。"""
    from agent_loop.pg_store import PgIdempotencyLedger
    assert hasattr(PgIdempotencyLedger, "update")
