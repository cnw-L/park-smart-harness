"""harness_rag —— vendored RAG 知识底座(从 assistant_core/rag fork,**互不影响**)。

milvus 管线/检索/重排/二轮/父块回捞逐字 copy(代码固定);config/models 等非 RAG 跨域件换成
harness 自有(`RagConfig` + 注入式 `ChatCompleter`)。公开 API 与原 assistant_core.rag 对齐。

工厂 `build_retriever(config)` 组装 真 Milvus 检索器 + 嵌入器(需 milvus/embedding 服务在线);
`build_reranker(config)` 组装重排器。检索入口 = `retrieve_evidence(...)`。
"""
from __future__ import annotations

from .config import RagConfig
from .contracts import RetrievalContext, RetrievalRequest, RetrievalResponse
from .evidence import EvidenceBundle, EvidenceItem, RetrievalDiagnostics, render_evidence_for_prompt
from .policy import QueryRewritePlan, QueryRewriteStrategy, RetrievalPolicy, build_initial_policy
from .providers import OpenAIEmbeddingAdapter, QwenRerankerAdapter
from .rerank import Reranker
from .retriever import MilvusHybridKnowledgeRetriever, MilvusSearchConfig
from .rewrite import ChatCompleter, LlmQueryRewriter
from .schema import MilvusKnowledgeSchemaConfig, ensure_knowledge_collection
from .service import (KnowledgeRetriever, QueryRewriter, evidence_prompt,
                      retrieve_evidence, retrieve_with_request)

__all__ = [
    "RagConfig", "RetrievalContext", "RetrievalRequest", "RetrievalResponse",
    "EvidenceBundle", "EvidenceItem", "RetrievalDiagnostics", "render_evidence_for_prompt",
    "QueryRewritePlan", "QueryRewriteStrategy", "RetrievalPolicy", "build_initial_policy",
    "OpenAIEmbeddingAdapter", "QwenRerankerAdapter", "Reranker",
    "MilvusHybridKnowledgeRetriever", "MilvusSearchConfig",
    "ChatCompleter", "LlmQueryRewriter",
    "MilvusKnowledgeSchemaConfig", "ensure_knowledge_collection",
    "KnowledgeRetriever", "QueryRewriter", "evidence_prompt",
    "retrieve_evidence", "retrieve_with_request",
    "build_retriever", "build_reranker",
]


def build_retriever(config: RagConfig) -> MilvusHybridKnowledgeRetriever:
    """RagConfig → 真 Milvus 混合检索器(嵌入器+检索器)。需 milvus/embedding 服务在线。"""
    search_config = MilvusSearchConfig(
        uri=config.milvus_uri or "",
        token=config.milvus_token,
        timeout_seconds=config.milvus_timeout_seconds,
        collection_name=config.milvus_collection_name,
        dense_dim=config.embedding_dimensions,
    )
    embedder = OpenAIEmbeddingAdapter(config)
    return MilvusHybridKnowledgeRetriever(config=search_config, embedder=embedder)


def build_reranker(config: RagConfig) -> QwenRerankerAdapter:
    """RagConfig → 真重排器。需 reranker 服务在线。"""
    return QwenRerankerAdapter(config)
