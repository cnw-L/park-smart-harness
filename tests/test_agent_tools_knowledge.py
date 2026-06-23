"""knowledge_query 封装 —— 注入层(身份→field_filters)+ 渲染 + 权限口径策略。

★最该测的是注入层:filter 键名必须对齐 rag/filters.py 白名单,否则被静默丢弃 = 越权。
"""
from __future__ import annotations

import asyncio

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget
from agent_loop.tools import ToolContext
from agent_context.principal import Principal

from agent_tools.domains.knowledge import make_knowledge_query_tool
from agent_tools.retrieval import Evidence, FakeKnowledgeRetriever, KnowledgePermissionPolicy

# rag/filters.py 的白名单键(注入层必须用这些键,否则编译器丢弃)
_ALLOWED = {"department_scope", "role_scope", "permission_tags", "confidential_level", "park_id"}


def _ctx(principal=None):
    c = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=12)), depth=0)
    c.principal = principal
    return c


def _employee():
    return Principal(id="u1", name="小张", role="员工·物业运维", dept="园区运维部",
                     token="tk", permissions=("knowledge:read",))


def _manager():
    return Principal(id="u2", name="李主管", role="运维主管", dept="园区运维部", token="tk2")


# ── 注入层:键名对齐 + 身份编译 ───────────────────────────────────────────────
def test_filter_keys_align_with_compiler_whitelist():
    """注入的 field_filters 键必须全在 rag/filters.py 白名单内(否则被静默丢弃=越权)。"""
    f = KnowledgePermissionPolicy().field_filters(_employee())
    assert f and set(f).issubset(_ALLOWED)


def test_employee_sees_public_and_internal_not_confidential():
    """对齐真语料(英文枚举):员工档位含 public/internal、不含 confidential;中文别名兼容。"""
    f = KnowledgePermissionPolicy().field_filters(_employee())
    lv = f["confidential_level"]
    assert "internal" in lv and "public" in lv and "confidential" not in lv
    assert "内部" in lv                                          # 中英双写兼容
    # 默认不发 permission_tags(来源标签非 ACL)/ 不 fail-closed dept(整库未差异化)
    assert "permission_tags" not in f and "department_scope" not in f


def test_manager_sees_confidential_level():
    lv = KnowledgePermissionPolicy().field_filters(_manager())["confidential_level"]
    assert "confidential" in lv and "internal" in lv            # 管理=含机密


def test_anonymous_excludes_internal():
    """密级隔离真生效:匿名只看 public、看不到 internal(真机实测匿名命中 0)。"""
    lv = KnowledgePermissionPolicy().field_filters(None)["confidential_level"]
    assert "public" in lv and "internal" not in lv and "confidential" not in lv


def test_fail_closed_mode_emits_dept_role_scope():
    """口径可调:语料组织标签对齐后置 scope_fail_closed=True → 恢复部门/角色隔离。"""
    f = KnowledgePermissionPolicy(scope_fail_closed=True).field_filters(_employee())
    assert f["department_scope"] == ["园区运维部"] and f["role_scope"] == ["员工·物业运维"]


def test_emit_permission_tags_opt_in():
    """permission_tags 默认不发(误杀);需要时显式开启可发。"""
    f = KnowledgePermissionPolicy(emit_permission_tags=True).field_filters(_employee())
    assert f["permission_tags"] == ["knowledge:read"]


def test_policy_levels_are_one_line_editable():
    """口径集中可改:换档位常量即生效,工具不动。"""
    pol = KnowledgePermissionPolicy(employee_levels=("public",))
    assert pol.field_filters(_employee())["confidential_level"] == ["public"]


# ── 工具:注入层真的把身份传给了检索器 ────────────────────────────────────────
def test_tool_injects_identity_filters_into_retriever():
    fake = FakeKnowledgeRetriever()
    tool = make_knowledge_query_tool(fake)
    r = asyncio.run(tool.handler({"query": "空调维修"}, _ctx(_employee())))
    assert r.ok and "出处" in r.content
    assert fake.calls and "internal" in fake.calls[0]["confidential_level"]   # 身份注入到检索


def test_tool_anonymous_still_filters_minimal():
    fake = FakeKnowledgeRetriever()
    asyncio.run(make_knowledge_query_tool(fake).handler({"query": "x"}, _ctx(None)))
    assert "internal" not in fake.calls[0]["confidential_level"]  # 无身份=仅公开


# ── 渲染 / 兜底 ───────────────────────────────────────────────────────────────
def test_insufficient_evidence_is_honest():
    fake = FakeKnowledgeRetriever(Evidence(insufficient="no_hit"))
    r = asyncio.run(make_knowledge_query_tool(fake).handler({"query": "x"}, _ctx(_employee())))
    assert r.ok and "未检索到充分证据" in r.content


def test_retriever_failure_is_unavailable_not_fabricated():
    class _Boom:
        async def retrieve(self, query, *, field_filters, token=None):
            raise RuntimeError("milvus down")
    r = asyncio.run(make_knowledge_query_tool(_Boom()).handler({"query": "x"}, _ctx(_employee())))
    assert r.ok is False and "知识库不可用" in (r.error or "")


def test_empty_query_is_business_error():
    r = asyncio.run(make_knowledge_query_tool().handler({"query": "  "}, _ctx(_employee())))
    assert r.ok is False and "query" in (r.error or "")


def test_knowledge_query_is_read_only():
    assert make_knowledge_query_tool().is_control is False
