"""RagConfig —— harness 自有的 RAG 配置(替 assistant_core.AssistantConfig 的 RAG 切片)。

vendored RAG 与 assistant_core **互不影响**:这里只放 RAG 管线/检索器/重排/嵌入读的字段,
不拖 assistant_core 的 llm/asr/mineru/redis 等无关配置。字段名与默认值对齐原 AssistantConfig
(policy.py/service.py/providers.py 逐字 copy,靠属性名一致而非类型)。改 RAG 行为改这里。
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RagConfig:
    # ── 检索策略(policy.build_initial_policy 读)─────────────────────────────
    retrieval_top_k: int = 8
    retrieval_candidate_limit: int = 40
    repair_rewrite_query_limit: int = 5
    repair_candidate_limit_per_query: int = 25
    repair_merged_candidate_limit: int = 80
    rerank_top_k: int = 5
    second_pass_threshold: float = 0.72
    retry_low_threshold: float = 0.25
    retrieval_latency_budget_ms: int = 1800
    # ── 嵌入(providers.OpenAIEmbeddingAdapter 读)────────────────────────────
    embedding_model: str = "qwen3-embedding"
    embedding_base_url: str | None = "http://localhost:6009/v1"
    embedding_api_key: str = "local-vllm"
    embedding_dimensions: int = 1024
    embedding_request_dimensions: int | None = None
    embedding_query_instruction: str = ""
    embedding_normalize: bool = True
    # ── 重排(providers.QwenRerankerAdapter 读)──────────────────────────────
    reranker_model: str = "qwen3-reranker"
    reranker_base_url: str | None = "http://localhost:6010"
    reranker_api_key: str = "local-vllm"
    reranker_endpoint: str = "score"                  # 'score' | 'rerank'
    reranker_instruction: str = ""
    reranker_max_concurrency: int = 8
    # ── Milvus 连接(build_retriever 组 MilvusSearchConfig 用)────────────────
    milvus_uri: str | None = "http://localhost:19530"
    milvus_token: str | None = None
    milvus_collection_name: str = "knowledge_chunks"
    milvus_timeout_seconds: float | None = None
    # ── 公共 ────────────────────────────────────────────────────────────────
    provider_timeout_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "RagConfig":
        """环境变量覆盖(对齐原 ASSISTANT_* 名;未设则用默认)。"""
        def _s(name, default):
            return os.getenv(name) or default

        def _f(name, default):
            v = os.getenv(name)
            return float(v) if v else default

        def _i(name, default):
            v = os.getenv(name)
            return int(v) if v else default

        return cls(
            embedding_model=_s("ASSISTANT_EMBEDDING_MODEL", cls.embedding_model),
            embedding_base_url=_s("ASSISTANT_EMBEDDING_BASE_URL", cls.embedding_base_url),
            embedding_api_key=_s("ASSISTANT_EMBEDDING_API_KEY", cls.embedding_api_key),
            embedding_dimensions=_i("ASSISTANT_EMBEDDING_DIMENSIONS", cls.embedding_dimensions),
            reranker_model=_s("ASSISTANT_RERANKER_MODEL", cls.reranker_model),
            reranker_base_url=_s("ASSISTANT_RERANKER_BASE_URL", cls.reranker_base_url),
            reranker_api_key=_s("ASSISTANT_RERANKER_API_KEY", cls.reranker_api_key),
            reranker_endpoint=_s("ASSISTANT_RERANKER_ENDPOINT", cls.reranker_endpoint),
            milvus_uri=_s("ASSISTANT_MILVUS_URI", cls.milvus_uri),
            milvus_token=os.getenv("ASSISTANT_MILVUS_TOKEN") or cls.milvus_token,
            milvus_collection_name=_s("ASSISTANT_MILVUS_COLLECTION", cls.milvus_collection_name),
            provider_timeout_seconds=_f("ASSISTANT_PROVIDER_TIMEOUT_SECONDS", cls.provider_timeout_seconds),
        )
