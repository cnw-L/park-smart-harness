"""Task 5 — 知识层:RAG-as-tool(身份透传)+ 强使用说明包装(设计 §七)。"""
from __future__ import annotations

import asyncio

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget
from agent_loop.tools import ToolContext

from agent_context.knowledge import make_knowledge_search_tool, wrap_knowledge
from agent_context.principal import Principal


def _ctx(principal=None) -> ToolContext:
    return ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=5)), depth=0, principal=principal)


def test_knowledge_search_passes_identity_token():
    seen: dict = {}

    async def retr(query, token):
        seen["query"] = query
        seen["token"] = token
        return "空调维护:定期清洗滤网"

    tool = make_knowledge_search_tool(retr)
    p = Principal(id="u", name="张", role="员工", token="tok-x")
    res = asyncio.run(tool.handler({"query": "空调维护"}, _ctx(p)))
    assert res.ok and "滤网" in res.content
    assert seen["token"] == "tok-x" and seen["query"] == "空调维护"   # 身份透传给检索


def test_knowledge_search_anonymous_token_none():
    seen: dict = {}

    async def retr(query, token):
        seen["token"] = token
        return "公开知识"

    asyncio.run(make_knowledge_search_tool(retr).handler({"query": "x"}, _ctx(None)))
    assert seen["token"] is None    # 匿名 → None → 后端默认查(须最小权限)


def test_knowledge_search_failure_no_fabricate():
    async def retr(query, token):
        raise RuntimeError("down")

    res = asyncio.run(make_knowledge_search_tool(retr).handler({"query": "x"}, _ctx()))
    assert not res.ok and "知识库不可用" in (res.error or "")   # 失败不臆造、不静默降级


def test_knowledge_search_caps_long_content():
    """输出预算(§七):超长检索结果截断 + 标记,避免大知识块撑爆上下文。"""
    async def retr(query, token):
        return "知识" * 2000        # 4000 字

    res = asyncio.run(make_knowledge_search_tool(retr, max_chars=200).handler({"query": "x"}, _ctx()))
    assert res.ok
    assert len(res.content) < 400 and "截断" in res.content    # 截断生效 + 给了提示


def test_knowledge_search_short_content_untouched():
    async def retr(query, token):
        return "短知识"

    res = asyncio.run(make_knowledge_search_tool(retr, max_chars=200).handler({"query": "x"}, _ctx()))
    assert res.content == "短知识" and "截断" not in res.content


def test_wrap_knowledge_strong_usage():
    s = wrap_knowledge("定期清洗滤网", source="设备维护手册 §4.2")
    assert "【相关知识】" in s and "设备维护手册" in s
    assert "参考内容开始" in s and "参考内容结束" in s
    assert "绝不执行" in s          # 强使用说明:明确当参考、不执行
