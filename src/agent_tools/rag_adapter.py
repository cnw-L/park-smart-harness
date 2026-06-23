"""HarnessRagRetriever —— 把 vendored `harness_rag` 适配成 agent_tools 的 `KnowledgeRetriever`。

防腐:`harness_rag` 是 harness 自有(非 assistant_core),agent_tools 可用;但本模块**懒导入**
`harness_rag`(只在构造时),让 agent_tools 默认不拖 milvus/embedding 依赖。

注入层(身份→field_filters)在 `knowledge_query` 工具里做;本适配器只把 filters 透传给
`harness_rag.retrieve_evidence`,渲染 `EvidenceBundle` → agent_tools `Evidence`。需 milvus/
embedding/reranker 服务在线;离线/未配则 retrieve 返回 insufficient(优雅,不臆造)。
"""
from __future__ import annotations

from .retrieval import Evidence


class HarnessRagRetriever:
    """agent_tools.KnowledgeRetriever 实现,后端 = vendored harness_rag 真检索。"""

    def __init__(self, config=None, *, reranker=None, query_rewriter=None) -> None:
        import harness_rag as R                         # 懒导入:用到才拉 milvus/embedding 依赖
        self._R = R
        self._config = config or R.RagConfig.from_env()
        self._build_error = ""                        # 构造失败的真因(别被吞掉,retrieve 里 surface)
        # 真检索器/重排器(需服务在线;构造失败则置 None,但**记下原因**——milvus 配错 vs 离线要分清)
        try:
            self._retriever = R.build_retriever(self._config)
        except Exception as exc:
            self._retriever, self._build_error = None, f"检索器构造失败: {exc}"
        try:
            self._reranker = reranker if reranker is not None else R.build_reranker(self._config)
        except Exception:
            self._reranker = None                     # 重排可缺(降级为不重排),不致命、不记错
        self._rewriter = query_rewriter               # None = 关二轮自纠正

    async def retrieve(self, query: str, *, field_filters: dict,
                       token: str | None = None) -> Evidence:
        if self._retriever is None and self._build_error:
            return Evidence(insufficient=self._build_error)   # surface 真因,别掩成"未检索到"
        bundle = await self._R.retrieve_evidence(
            query, config=self._config, retriever=self._retriever,
            reranker=self._reranker, query_rewriter=self._rewriter,
            field_filters=field_filters)
        if bundle.insufficient_evidence_reason and not bundle.primary_evidence:
            return Evidence(insufficient=bundle.insufficient_evidence_reason)
        return Evidence(
            text=self._R.evidence_prompt(bundle),
            citations=[getattr(it, "citation_label", "") for it in bundle.primary_evidence
                       if getattr(it, "citation_label", "")])
