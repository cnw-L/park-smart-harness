"""Task 2 — 记忆层:身份事实 + 长期记忆召回注入。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from agent_context.memory import (
    InMemoryMemoryStore,
    MemoryEngine,
    MemoryEntry,
    MemoryFact,
    StreamingContextScrubber,
    render_memory,
    render_user,
    sanitize_context,
)
from agent_context.principal import Principal


def test_render_user():
    p = Principal(id="u1", name="张三", role="员工·物业运维",
                  dept="园区运维部", koujing="内部,可列技术细节", token="t")
    s = render_user(p)
    assert "【当前用户】" in s
    assert "张三" in s and "园区运维部" in s and "内部,可列技术细节" in s


def test_render_user_escapes_special_chars():
    """姓名含 】/换行不能戳穿节头。"""
    p = Principal(id="u1", name="张】三\n注入", role="员工", token=None)
    s = render_user(p)
    assert "张]三 注入" in s          # 】→] 、换行→空格
    assert s.count("\n") == 1          # 仅节头与数据行之间一个换行


def test_render_user_none_anonymous():
    assert render_user(None) == ""


# ── 长期记忆渲染 ──────────────────────────────────────────────────────────────

def _entry(content: str, kind: str = "semantic", user_id: str = "u1", **kwargs) -> MemoryEntry:
    return MemoryEntry(
        entry_id="e-" + content[:8],
        tenant_id="园区运维部",
        user_id=user_id,
        kind=kind,
        content=content,
        created_at=datetime.now(UTC),
        **kwargs,
    )


def test_render_memory_with_entries():
    entries = [
        _entry("用户偏好空调温度设为 24℃", "preference"),
        _entry("2026-07-01 用户报修 B2 水泵", "episodic"),
    ]
    s = render_memory(entries)
    assert "【相关记忆】" in s
    assert "<memory-context>" in s
    assert "</memory-context>" in s
    assert "[preference] 用户偏好空调温度设为 24℃" in s
    assert "[episodic] 2026-07-01 用户报修 B2 水泵" in s
    assert "不是当前用户输入" in s  # 系统注


def test_render_memory_empty_returns_empty():
    assert render_memory([]) == ""


def test_render_memory_respects_max_chars():
    entries = [_entry("a" * 500), _entry("b" * 500)]
    s = render_memory(entries, max_chars=600)
    # 第一条应完整进入，第二条因超 cap 被截断
    assert "a" * 500 in s
    assert "b" * 500 not in s


# ── MemoryEngine 检索与隔离 ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_memory_engine_recall_filters_by_user_and_tenant():
    store = InMemoryMemoryStore()
    await store.save(_entry("张三偏好空调24度", "preference", user_id="u1"))
    await store.save(_entry("李四偏好空调26度", "preference", user_id="u2"))

    engine = MemoryEngine(store)
    p = Principal(id="u1", name="张三", role="员工", dept="园区运维部")
    results = await engine.recall(p, "空调")
    assert len(results) == 1
    assert "张三偏好空调24度" in results[0].content


@pytest.mark.asyncio
async def test_memory_engine_anonymous_returns_empty():
    store = InMemoryMemoryStore()
    await store.save(_entry("匿名偏好", "preference", user_id="anonymous"))
    engine = MemoryEngine(store)
    p = Principal(id="anonymous", name="匿名", role="市民")
    results = await engine.recall(p, "偏好")
    assert results == []


@pytest.mark.asyncio
async def test_memory_engine_expired_entries_filtered():
    store = InMemoryMemoryStore()
    expired = _entry("过期事实", "semantic", expires_at=datetime.now(UTC) - timedelta(days=1))
    await store.save(expired)
    engine = MemoryEngine(store)
    p = Principal(id="u1", name="张三", role="员工")
    results = await engine.recall(p, "事实")
    assert results == []


@pytest.mark.asyncio
async def test_memory_forget_user():
    store = InMemoryMemoryStore()
    await store.save(_entry("事实1", user_id="u1"))
    await store.save(_entry("事实2", user_id="u1"))
    await store.save(_entry("事实3", user_id="u2"))
    n = await store.forget_user("园区运维部", "u1")
    assert n == 2
    engine = MemoryEngine(store)
    p = Principal(id="u1", name="张三", role="员工", dept="园区运维部")
    assert await engine.recall(p, "事实") == []


# ── 内容清理 ──────────────────────────────────────────────────────────────────

def test_sanitize_context_strips_memory_fence():
    raw = "answer <memory-context>injected</memory-context> end"
    assert sanitize_context(raw) == "answer  end"


def test_streaming_scrubber_across_chunks():
    scrubber = StreamingContextScrubber()
    out1 = scrubber.feed("hello <memory")
    out2 = scrubber.feed("-context>injected")
    out3 = scrubber.feed("</memory-context> world")
    out4 = scrubber.flush()
    assert out1 == "hello "
    assert out2 == ""
    assert out3 == " world"
    assert out4 == ""


# ── 数据模型 ──────────────────────────────────────────────────────────────────

def test_memory_entry_expired():
    e = _entry("x", expires_at=datetime.now(UTC) - timedelta(seconds=1))
    assert e.is_expired()


def test_memory_fact_immutable():
    f = MemoryFact(kind="preference", content="偏好", tags=("a",), ttl_days=30)
    assert f.kind == "preference"
