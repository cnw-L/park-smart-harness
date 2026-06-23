"""Knowledge-only Milvus hybrid-search adapter for assistant_core RAG."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .milvus import Embedder, MilvusClientConfig, MilvusSearchClient
from .evidence import EvidenceItem
from .filters import compile_milvus_filter
from .policy import RetrievalPolicy


DEFAULT_OUTPUT_FIELDS = [
    "chunk_id",
    "doc_id",
    "parent_chunk_id",
    "section_id",
    "content_type",
    "doc_type",
    "knowledge_domain",
    "retrieval_text",
    "chunk_text",
    "source_title",
    "section_title",
    "source_page_start",
    "source_page_end",
    "image_asset_id",
    "image_title",
    "image_ocr_text",
    "fault_code",
    "fault_symptom",
    "parameter_name",
    "parameter_value",
    "linked_raw_chunk_ids",
    "linked_image_ids",
    "metadata",
    "permission_tags",
    "role_scope",
    "department_scope",
    "confidential_level",
    "park_id",
    "building_id",
    "system_type",
    "equipment_type",
    "equipment_model",
    "vendor",
    "doc_version",
    "parser_mode",
    "source_format",
    "conversion_used",
    "status",
    "review_status",
    "source_locator",
]


@dataclass(frozen=True)
class MilvusSearchConfig:
    """Knowledge collection retrieval config."""

    uri: str
    token: str | None = None
    timeout_seconds: float | None = None
    collection_name: str = "knowledge_chunks"
    dense_dim: int = 1024
    dense_index_type: str = "GPU_CAGRA"
    dense_metric_type: str = "IP"
    sparse_metric_type: str = "BM25"
    max_workers: int = 8
    max_in_flight: int = 16
    queue_timeout_seconds: float = 0.01
    allowed_collections: tuple[str, ...] = ("knowledge_chunks",)
    output_fields: list[str] = field(default_factory=lambda: DEFAULT_OUTPUT_FIELDS.copy())


class MilvusHybridKnowledgeRetriever:
    """Thin adapter around MilvusClient.hybrid_search."""

    def __init__(
        self,
        *,
        config: MilvusSearchConfig,
        embedder: Embedder,
        client: Any | None = None,
    ) -> None:
        self.config = config
        self.embedder = embedder
        self.search_client = MilvusSearchClient(
            MilvusClientConfig(
                uri=config.uri,
                token=config.token,
                timeout_seconds=config.timeout_seconds,
                max_workers=config.max_workers,
                max_in_flight=config.max_in_flight,
                queue_timeout_seconds=config.queue_timeout_seconds,
            ),
            client=client,
        )

    async def retrieve(self, policy: RetrievalPolicy) -> list[EvidenceItem]:
        dense_vector = await self.embedder.aembed_query(policy.query)
        if len(dense_vector) != self.config.dense_dim:
            raise ValueError(f"dense vector dimension must be {self.config.dense_dim}, got {len(dense_vector)}")

        collection_name = self._collection_name(policy)
        bound_policy = policy.model_copy(update={"collection": collection_name})
        expr = compile_milvus_filter(bound_policy)
        results = await self.search_client.hybrid_search(
            collection_name=collection_name,
            query_text=bound_policy.query,
            dense_vector=dense_vector,
            dense_field=bound_policy.dense_field,
            sparse_field=bound_policy.sparse_field,
            dense_metric_type=bound_policy.dense_metric_type,
            sparse_metric_type=bound_policy.sparse_metric_type,
            ranker=bound_policy.ranker,
            weighted_scores=bound_policy.weighted_scores,
            candidate_limit=bound_policy.candidate_limit,
            final_limit=bound_policy.candidate_limit,
            output_fields=self.config.output_fields,
            filter_expr=expr,
        )
        return _hits_to_evidence(results, source_stage="first_pass")

    async def afetch_chunk_texts(self, chunk_ids: list[str]) -> dict[str, str]:
        """Batch-fetch chunk_text by chunk_id, for small-to-big parent expansion."""

        unique_ids = list(dict.fromkeys(cid for cid in chunk_ids if cid))
        if not unique_ids:
            return {}
        rows = await self.search_client.query_by_ids(
            collection_name=self.config.collection_name,
            ids=unique_ids,
            output_fields=["chunk_id", "chunk_text"],
        )
        texts: dict[str, str] = {}
        for row in rows or []:
            cid = str(row.get("chunk_id") or "")
            text = str(row.get("chunk_text") or "")
            if cid and text:
                texts[cid] = text
        return texts

    def _collection_name(self, policy: RetrievalPolicy) -> str:
        if policy.collection == "knowledge_chunks":
            return self.config.collection_name
        if policy.collection in self.config.allowed_collections:
            return policy.collection
        return self.config.collection_name


def _hits_to_evidence(results: Any, *, source_stage: str) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for group in results or []:
        for hit in group:
            fields = _hit_value(hit, "entity", {}) or {}
            if hasattr(fields, "to_dict"):
                fields = fields.to_dict()
            if not isinstance(fields, dict):
                fields = {}
            chunk_id = str(fields.get("chunk_id") or _hit_value(hit, "id", ""))
            text = str(fields.get("chunk_text") or "")
            if not chunk_id or not text:
                continue
            items.append(
                EvidenceItem(
                    id=chunk_id,
                    chunk_id=chunk_id,
                    doc_id=_str_or_none(fields.get("doc_id")),
                    section_id=_str_or_none(fields.get("section_id")),
                    parent_chunk_id=_str_or_none(fields.get("parent_chunk_id")),
                    chunk_text=text,
                    content_type=str(fields.get("content_type") or ""),
                    doc_type=str(fields.get("doc_type") or ""),
                    knowledge_domain=str(fields.get("knowledge_domain") or ""),
                    source_title=str(fields.get("source_title") or ""),
                    section_title=str(fields.get("section_title") or ""),
                    source_page_start=_int_or_none(fields.get("source_page_start")),
                    source_page_end=_int_or_none(fields.get("source_page_end")),
                    source_locator=str(fields.get("source_locator") or ""),
                    equipment_type=str(fields.get("equipment_type") or ""),
                    equipment_model=str(fields.get("equipment_model") or ""),
                    fault_code=str(fields.get("fault_code") or ""),
                    fault_symptom=str(fields.get("fault_symptom") or ""),
                    parameter_name=str(fields.get("parameter_name") or ""),
                    parameter_value=str(fields.get("parameter_value") or ""),
                    image_asset_id=str(fields.get("image_asset_id") or ""),
                    linked_raw_chunk_ids=_string_list(fields.get("linked_raw_chunk_ids")),
                    linked_image_ids=_string_list(fields.get("linked_image_ids")),
                    permission_tags=_string_list(fields.get("permission_tags")),
                    role_scope=_string_list(fields.get("role_scope")),
                    department_scope=_string_list(fields.get("department_scope")),
                    confidential_level=str(fields.get("confidential_level") or ""),
                    source_stage=source_stage,  # type: ignore[arg-type]
                    extra_metadata=_metadata(fields.get("metadata")),
                )
            )
    return items


def _hit_value(hit: Any, key: str, default: Any = None) -> Any:
    if isinstance(hit, dict):
        return hit.get(key, default)
    try:
        return hit[key]
    except (KeyError, TypeError, AttributeError):
        return getattr(hit, key, default)


def _str_or_none(value: Any) -> str | None:
    return None if value in (None, "") else str(value)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list | tuple | set):
        return [str(item) for item in value if item not in (None, "")]
    return []


def _metadata(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
