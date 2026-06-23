"""Milvus collection contract for assistant_core knowledge retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .milvus import ensure_collection


@dataclass(frozen=True)
class MilvusKnowledgeSchemaConfig:
    """Configurable Milvus schema/index settings.

    Production favors GPU_CAGRA for dense retrieval latency. Local and CI
    environments can override the dense index type without changing RAG code.
    """

    collection_name: str = "knowledge_chunks"
    dense_dim: int = 1024
    varchar_max_length: int = 512
    retrieval_text_max_length: int = 65535
    evidence_text_max_length: int = 65535
    dense_field: str = "dense"
    sparse_field: str = "sparse"
    text_field: str = "retrieval_text"
    language_field: str = "language"
    dense_index_type: str = "GPU_CAGRA"
    dense_metric_type: str = "IP"
    sparse_index_type: str = "SPARSE_INVERTED_INDEX"
    sparse_metric_type: str = "BM25"
    dense_index_params: dict[str, Any] = field(
        default_factory=lambda: {
            "intermediate_graph_degree": 96,
            "graph_degree": 64,
            "build_algo": "IVF_PQ",
        }
    )
    sparse_index_params: dict[str, Any] = field(default_factory=dict)
    analyzer_params: dict[str, Any] = field(
        default_factory=lambda: {
            "analyzers": {
                "english": {"type": "english"},
                "chinese": {"type": "chinese"},
                "default": {"tokenizer": "icu"},
            },
            "by_field": "language",
            "alias": {"cn": "chinese", "zh": "chinese", "en": "english"},
        }
    )


def build_knowledge_schema(config: MilvusKnowledgeSchemaConfig | None = None):
    """Build an official BM25-enabled Milvus schema."""

    from pymilvus import DataType, Function, FunctionType, MilvusClient

    config = config or MilvusKnowledgeSchemaConfig()
    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field(
        field_name="chunk_id",
        datatype=DataType.VARCHAR,
        is_primary=True,
        max_length=config.varchar_max_length,
    )
    for field_name in _varchar_fields(config):
        schema.add_field(
            field_name=field_name,
            datatype=DataType.VARCHAR,
            max_length=config.varchar_max_length,
            nullable=True,
        )
    schema.add_field(
        field_name=config.text_field,
        datatype=DataType.VARCHAR,
        max_length=config.retrieval_text_max_length,
        enable_analyzer=True,
        multi_analyzer_params=config.analyzer_params,
    )
    schema.add_field(
        field_name="chunk_text",
        datatype=DataType.VARCHAR,
        max_length=config.evidence_text_max_length,
        nullable=True,
    )
    schema.add_field(
        field_name="image_ocr_text",
        datatype=DataType.VARCHAR,
        max_length=config.evidence_text_max_length,
        nullable=True,
    )
    schema.add_field(field_name="source_page_start", datatype=DataType.INT64, nullable=True)
    schema.add_field(field_name="source_page_end", datatype=DataType.INT64, nullable=True)
    schema.add_field(field_name="linked_raw_chunk_ids", datatype=DataType.JSON, nullable=True)
    schema.add_field(field_name="linked_image_ids", datatype=DataType.JSON, nullable=True)
    schema.add_field(field_name="metadata", datatype=DataType.JSON, nullable=True)
    schema.add_field(field_name="department_scope", datatype=DataType.JSON, nullable=True)
    schema.add_field(field_name="role_scope", datatype=DataType.JSON, nullable=True)
    schema.add_field(field_name="permission_tags", datatype=DataType.JSON, nullable=True)
    schema.add_field(
        field_name="confidential_level",
        datatype=DataType.VARCHAR,
        max_length=config.varchar_max_length,
        nullable=True,
    )
    schema.add_field(field_name=config.dense_field, datatype=DataType.FLOAT_VECTOR, dim=config.dense_dim)
    schema.add_field(field_name=config.sparse_field, datatype=DataType.SPARSE_FLOAT_VECTOR)
    schema.add_function(
        Function(
            name="bm25",
            input_field_names=[config.text_field],
            output_field_names=[config.sparse_field],
            function_type=FunctionType.BM25,
        )
    )
    return schema


def build_knowledge_index_params(config: MilvusKnowledgeSchemaConfig | None = None):
    """Build dense and BM25 sparse indexes for the knowledge collection."""

    from pymilvus import MilvusClient

    config = config or MilvusKnowledgeSchemaConfig()
    index_params = MilvusClient.prepare_index_params()
    index_params.add_index(
        field_name=config.dense_field,
        index_type=config.dense_index_type,
        metric_type=config.dense_metric_type,
        params=config.dense_index_params,
    )
    index_params.add_index(
        field_name=config.sparse_field,
        index_type=config.sparse_index_type,
        metric_type=config.sparse_metric_type,
        params=config.sparse_index_params,
    )
    return index_params


def ensure_knowledge_collection(
    client: Any,
    config: MilvusKnowledgeSchemaConfig | None = None,
    *,
    drop_existing: bool = False,
):
    """Create the knowledge collection with official MilvusClient APIs."""

    config = config or MilvusKnowledgeSchemaConfig()
    return ensure_collection(
        client=client,
        collection_name=config.collection_name,
        schema=build_knowledge_schema(config),
        index_params=build_knowledge_index_params(config),
        drop_existing=drop_existing,
    )


def _varchar_fields(config: MilvusKnowledgeSchemaConfig) -> list[str]:
    return [
        "doc_id",
        "parent_chunk_id",
        "section_id",
        "content_type",
        "doc_type",
        "knowledge_domain",
        config.language_field,
        "parser_mode",
        "source_format",
        "conversion_used",
        "park_id",
        "building_id",
        "system_type",
        "equipment_type",
        "equipment_model",
        "vendor",
        "fault_code",
        "fault_symptom",
        "parameter_name",
        "parameter_value",
        "source_title",
        "section_title",
        "doc_version",
        "status",
        "review_status",
        "image_asset_id",
        "image_title",
        "source_locator",
    ]
