"""知识超域 —— 扁平工具 `knowledge_query`(RAG-as-tool,1 次检索)。

工具只做两件 harness 该做的事(RAG 内核全复用 assistant_core/rag):
① **注入层**:读 `ctx.principal` → `KnowledgePermissionPolicy.field_filters` → 可信过滤条件
   (身份来自登录态、绝不模型自报;补 RAG 权限"注入层"洞)。
② **渲染**:`Evidence` → 带出处简洁文本;不足老实说、失败不臆造(catalog 给 1500 预算封顶)。

真检索经 `KnowledgeRetriever` 注入(默认 Fake);真适配器包 assistant_core/rag,在接线边。
"""
from __future__ import annotations

from agent_loop.tools import LoopTool, ToolContext, ToolResult

from ..retrieval import FakeKnowledgeRetriever, KnowledgePermissionPolicy, KnowledgeRetriever


def make_knowledge_query_tool(retriever: KnowledgeRetriever | None = None, *,
                              policy: KnowledgePermissionPolicy | None = None) -> LoopTool:
    retriever = retriever or FakeKnowledgeRetriever()
    policy = policy or KnowledgePermissionPolicy()

    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        query = (args.get("query") or "").strip()
        if not query:
            return ToolResult(ok=False, content="", error="query 不能为空")
        principal = getattr(ctx, "principal", None)
        filters = policy.field_filters(principal)              # ① 注入层
        token = getattr(principal, "token", None)
        try:
            ev = await retriever.retrieve(query, field_filters=filters, token=token)
        except Exception:
            return ToolResult(ok=False, content="", error="知识库不可用")
        if ev.insufficient:
            return ToolResult(ok=True, content=f"[未检索到充分证据] {ev.insufficient}")
        if not ev.text:
            return ToolResult(ok=True, content="[未检索到相关知识]")
        cites = f"\n出处:{'、'.join(ev.citations)}" if ev.citations else ""
        return ToolResult(ok=True, content=ev.text + cites)    # ② 渲染

    return LoopTool(
        name="knowledge_query",
        description="检索园区知识库(设备手册/规章/FAQ),按你的权限范围返回带出处的参考资料。",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "要查的问题/关键词"}},
            "required": ["query"],
        },
        handler=handler,
        is_control=False,
    )
