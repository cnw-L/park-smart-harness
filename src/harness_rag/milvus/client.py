"""Small MilvusClient wrapper shared by knowledge and memory retrieval."""

from __future__ import annotations

import json
from dataclasses import dataclass
from threading import Lock
from typing import Any, Protocol

from .executor import BoundedMilvusExecutor, MilvusExecutorConfig


class Embedder(Protocol):
    async def aembed_query(self, text: str) -> list[float]:
        ...


@dataclass(frozen=True)
class MilvusClientConfig:
    uri: str
    token: str | None = None
    timeout_seconds: float | None = None
    max_workers: int = 8
    max_in_flight: int = 16
    queue_timeout_seconds: float = 0.01
    cache_loaded_collections: bool = True


class MilvusSearchClient:
    """Official PyMilvus search shapes, without business semantics."""

    def __init__(
        self,
        config: MilvusClientConfig,
        client: Any | None = None,
        executor: BoundedMilvusExecutor | None = None,
    ) -> None:
        self.config = config
        self._client = client
        self._owns_executor = executor is None
        self._executor = executor or BoundedMilvusExecutor(
            MilvusExecutorConfig(
                max_workers=config.max_workers,
                max_in_flight=config.max_in_flight,
                queue_timeout_seconds=config.queue_timeout_seconds,
            )
        )
        self._loaded_collections: set[str] = set()
        self._load_lock = Lock()

    @property
    def client(self):
        if self._client is None:
            from pymilvus import MilvusClient

            kwargs: dict[str, Any] = {"uri": self.config.uri}
            if self.config.token:
                kwargs["token"] = self.config.token
            if self.config.timeout_seconds is not None:
                kwargs["timeout"] = self.config.timeout_seconds
            self._client = MilvusClient(**kwargs)
        return self._client

    async def hybrid_search(
        self,
        *,
        collection_name: str,
        query_text: str,
        dense_vector: list[float],
        dense_field: str,
        sparse_field: str,
        dense_metric_type: str,
        sparse_metric_type: str,
        ranker: str,
        weighted_scores: tuple[float, float],
        candidate_limit: int,
        final_limit: int,
        output_fields: list[str],
        filter_expr: str | None = None,
    ) -> Any:
        return await self._executor.run(
            self._hybrid_search_sync,
            collection_name,
            query_text,
            dense_vector,
            dense_field,
            sparse_field,
            dense_metric_type,
            sparse_metric_type,
            ranker,
            weighted_scores,
            candidate_limit,
            final_limit,
            output_fields,
            filter_expr,
            queue_timeout_seconds=self.config.queue_timeout_seconds,
        )

    def _hybrid_search_sync(
        self,
        collection_name: str,
        query_text: str,
        dense_vector: list[float],
        dense_field: str,
        sparse_field: str,
        dense_metric_type: str,
        sparse_metric_type: str,
        ranker: str,
        weighted_scores: tuple[float, float],
        candidate_limit: int,
        final_limit: int,
        output_fields: list[str],
        filter_expr: str | None,
    ) -> Any:
        from pymilvus import AnnSearchRequest

        dense_request = AnnSearchRequest(
            data=[dense_vector],
            anns_field=dense_field,
            param={"metric_type": dense_metric_type, "params": {}},
            limit=candidate_limit,
            expr=filter_expr,
        )
        sparse_request = AnnSearchRequest(
            data=[query_text],
            anns_field=sparse_field,
            param={"metric_type": sparse_metric_type, "params": {}},
            limit=candidate_limit,
            expr=filter_expr,
        )
        self._load_collection_once(collection_name)
        kwargs: dict[str, Any] = {}
        if self.config.timeout_seconds is not None:
            kwargs["timeout"] = self.config.timeout_seconds
        return self.client.hybrid_search(
            collection_name=collection_name,
            reqs=[dense_request, sparse_request],
            ranker=self._ranker(ranker, weighted_scores),
            limit=final_limit,
            output_fields=output_fields,
            **kwargs,
        )

    async def dense_search(
        self,
        *,
        collection_name: str,
        dense_vector: list[float],
        dense_field: str,
        metric_type: str,
        limit: int,
        output_fields: list[str],
        filter_expr: str | None = None,
    ) -> Any:
        return await self._executor.run(
            self._dense_search_sync,
            collection_name,
            dense_vector,
            dense_field,
            metric_type,
            limit,
            output_fields,
            filter_expr,
            queue_timeout_seconds=self.config.queue_timeout_seconds,
        )

    def _dense_search_sync(
        self,
        collection_name: str,
        dense_vector: list[float],
        dense_field: str,
        metric_type: str,
        limit: int,
        output_fields: list[str],
        filter_expr: str | None,
    ) -> Any:
        self._load_collection_once(collection_name)
        kwargs: dict[str, Any] = {}
        if self.config.timeout_seconds is not None:
            kwargs["timeout"] = self.config.timeout_seconds
        return self.client.search(
            collection_name=collection_name,
            data=[dense_vector],
            anns_field=dense_field,
            search_params={"metric_type": metric_type, "params": {}},
            filter=filter_expr or "",
            limit=limit,
            output_fields=output_fields,
            **kwargs,
        )

    async def query_by_ids(
        self,
        *,
        collection_name: str,
        ids: list[str],
        output_fields: list[str],
        id_field: str = "chunk_id",
    ) -> Any:
        if not ids:
            return []
        return await self._executor.run(
            self._query_by_ids_sync,
            collection_name,
            ids,
            output_fields,
            id_field,
            queue_timeout_seconds=self.config.queue_timeout_seconds,
        )

    def _query_by_ids_sync(
        self,
        collection_name: str,
        ids: list[str],
        output_fields: list[str],
        id_field: str,
    ) -> Any:
        self._load_collection_once(collection_name)
        kwargs: dict[str, Any] = {}
        if self.config.timeout_seconds is not None:
            kwargs["timeout"] = self.config.timeout_seconds
        expr = f"{id_field} in {json.dumps(list(ids), ensure_ascii=False)}"
        return self.client.query(
            collection_name=collection_name,
            filter=expr,
            output_fields=output_fields,
            limit=len(ids),
            **kwargs,
        )

    @staticmethod
    def _ranker(ranker: str, weighted_scores: tuple[float, float]):
        from pymilvus import RRFRanker, WeightedRanker

        if ranker == "weighted":
            return WeightedRanker(*weighted_scores)
        return RRFRanker()

    def _load_collection_once(self, collection_name: str) -> None:
        if not self.config.cache_loaded_collections:
            self.client.load_collection(collection_name=collection_name)
            return
        if collection_name in self._loaded_collections:
            return
        with self._load_lock:
            if collection_name in self._loaded_collections:
                return
            self.client.load_collection(collection_name=collection_name)
            self._loaded_collections.add(collection_name)

    def close(self) -> None:
        if self._owns_executor:
            self._executor.close()
