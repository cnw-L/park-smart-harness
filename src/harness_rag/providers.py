"""Official-protocol provider adapters for assistant_core.

The core graph owns orchestration. These adapters only translate provider
protocols into small assistant_core ports.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Sequence
from typing import Any, Literal

import httpx

from .config import RagConfig as AssistantConfig
from .evidence import EvidenceItem


class OpenAIEmbeddingAdapter:
    """OpenAI-compatible embedding adapter used by Milvus retrieval."""

    def __init__(self, config: AssistantConfig, *, client: Any | None = None) -> None:
        if config.embedding_base_url is None and client is None:
            raise ValueError("embedding_base_url is required when no embedding client is injected")
        self.config = config
        self._client = client
        self._resolved_model: str | None = None

    @property
    def client(self) -> Any:
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.config.embedding_api_key,
                base_url=self.config.embedding_base_url,
                timeout=self.config.provider_timeout_seconds,
            )
        return self._client

    async def aembed_query(self, text: str) -> list[float]:
        input_text = _with_instruction(text, self.config.embedding_query_instruction)
        response = await self._create_embedding(input_text)
        vector = _embedding_from_response(response)
        if self.config.embedding_normalize:
            return _l2_normalize(vector)
        return vector

    async def _create_embedding(self, input_text: str) -> Any:
        kwargs: dict[str, Any] = {
            "model": self._resolved_model or self.config.embedding_model,
            "input": input_text,
        }
        if self.config.embedding_request_dimensions is not None:
            kwargs["dimensions"] = self.config.embedding_request_dimensions
        try:
            return await self.client.embeddings.create(**kwargs)
        except Exception as exc:
            if not _is_not_found_error(exc):
                raise
            for model in await self._discover_model_ids():
                if model == kwargs["model"]:
                    continue
                retry_kwargs = dict(kwargs, model=model)
                try:
                    response = await self.client.embeddings.create(**retry_kwargs)
                except Exception as retry_exc:
                    if _is_not_found_error(retry_exc):
                        continue
                    raise
                self._resolved_model = model
                return response
            raise

    async def _discover_model_ids(self) -> list[str]:
        models = getattr(self.client, "models", None)
        list_models = getattr(models, "list", None)
        if list_models is None:
            return []
        response = list_models()
        if hasattr(response, "__await__"):
            response = await response
        return _model_ids(response)

    async def aclose(self) -> None:
        close = getattr(self._client, "close", None) or getattr(self._client, "aclose", None)
        if close is None:
            return
        result = close()
        if hasattr(result, "__await__"):
            await result


def _embedding_from_response(response: Any) -> list[float]:
    data = getattr(response, "data", None) or []
    if not data:
        raise ValueError("embedding response did not contain vectors")
    embedding = getattr(data[0], "embedding", None)
    if embedding is None and isinstance(data[0], dict):
        embedding = data[0].get("embedding")
    if not isinstance(embedding, Sequence):
        raise ValueError("embedding response vector is invalid")
    return [float(value) for value in embedding]


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0 or math.isnan(norm):
        return vector
    return [value / norm for value in vector]


class QwenRerankerAdapter:
    """Qwen/vLLM-compatible reranker adapter for EvidenceItem lists."""

    def __init__(
        self,
        config: AssistantConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if config.reranker_base_url is None and client is None:
            raise ValueError("reranker_base_url is required when no HTTP client is injected")
        self.config = config
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=str(config.reranker_base_url).rstrip("/"),
            timeout=config.provider_timeout_seconds,
            trust_env=False,
        )
        self._resolved_model: str | None = None

    async def rerank(self, query: str, evidence: list[EvidenceItem], *, top_k: int) -> list[EvidenceItem]:
        if not evidence:
            return []
        endpoint = self.config.reranker_endpoint
        if endpoint == "rerank":
            try:
                ranked = await self._rerank_batch(query, evidence)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404:
                    raise
                ranked = await self._score_pairs(query, evidence)
        elif endpoint == "score":
            try:
                ranked = await self._score_pairs(query, evidence)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404:
                    raise
                ranked = await self._rerank_batch(query, evidence)
        return ranked[:top_k]

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _rerank_batch(self, query: str, evidence: list[EvidenceItem]) -> list[EvidenceItem]:
        payload: dict[str, Any] = {
            "model": self._resolved_model or self.config.reranker_model,
            "query": query,
            "documents": [item.answer_text for item in evidence],
            "top_n": len(evidence),
            "return_documents": False,
        }
        if self.config.reranker_instruction:
            payload["instruction"] = self.config.reranker_instruction
        response = await self._post_with_model_discovery(_rerank_paths(), payload)
        results = response.get("results") or response.get("data") or []
        scored: list[tuple[int, float]] = []
        for fallback_index, item in enumerate(results):
            if not isinstance(item, dict):
                continue
            index = int(item.get("index", fallback_index))
            score = _normalize_score(item.get("relevance_score", item.get("score", 0.0)))
            if 0 <= index < len(evidence):
                scored.append((index, score))
        return _rank_by_scores(evidence, scored)

    async def _score_pairs(self, query: str, evidence: list[EvidenceItem]) -> list[EvidenceItem]:
        semaphore = asyncio.Semaphore(self.config.reranker_max_concurrency)

        async def score_one(index: int, item: EvidenceItem) -> tuple[int, float]:
            async with semaphore:
                payload: dict[str, Any] = {
                    "model": self._resolved_model or self.config.reranker_model,
                    "text_1": query,
                    "text_2": item.answer_text,
                }
                if self.config.reranker_instruction:
                    payload["instruction"] = self.config.reranker_instruction
                response = await self._post_with_model_discovery(_score_paths(), payload)
                return index, _extract_score(response)

        scores = await asyncio.gather(*(score_one(index, item) for index, item in enumerate(evidence)))
        return _rank_by_scores(evidence, list(scores))

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {}
        if self.config.reranker_api_key and self.config.reranker_api_key != "EMPTY":
            headers["Authorization"] = f"Bearer {self.config.reranker_api_key}"
        response = await self._client.post(path, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("reranker response must be a JSON object")
        return data

    async def _post_with_model_discovery(
        self,
        paths: Sequence[str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            return await self._post_any(paths, payload)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise
            last_error = exc
        requested_model = str(payload.get("model", ""))
        for model in await self._discover_model_ids():
            if model == requested_model:
                continue
            retry_payload = dict(payload, model=model)
            try:
                response = await self._post_any(paths, retry_payload)
            except httpx.HTTPStatusError as retry_exc:
                if retry_exc.response.status_code == 404:
                    last_error = retry_exc
                    continue
                raise
            self._resolved_model = model
            return response
        raise last_error

    async def _post_any(self, paths: Sequence[str], payload: dict[str, Any]) -> dict[str, Any]:
        last_not_found: httpx.HTTPStatusError | None = None
        for path in paths:
            try:
                return await self._post(path, payload)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    last_not_found = exc
                    continue
                raise
        if last_not_found is not None:
            raise last_not_found
        raise ValueError("no reranker endpoint paths configured")

    async def _discover_model_ids(self) -> list[str]:
        headers = {}
        if self.config.reranker_api_key and self.config.reranker_api_key != "EMPTY":
            headers["Authorization"] = f"Bearer {self.config.reranker_api_key}"
        for path in ("/v1/models", "/models"):
            response = await self._client.get(path, headers=headers)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            return _model_ids(response.json())
        return []


def _rank_by_scores(evidence: list[EvidenceItem], scores: list[tuple[int, float]]) -> list[EvidenceItem]:
    score_by_index = {index: score for index, score in scores}
    ranked = [
        evidence[index].model_copy(update={"rerank_score": score})
        for index, score in score_by_index.items()
        if 0 <= index < len(evidence)
    ]
    ranked.sort(key=lambda item: item.rerank_score or 0.0, reverse=True)
    return ranked


def _rerank_paths() -> tuple[str, ...]:
    return ("/v1/rerank", "/rerank", "/v2/rerank")


def _score_paths() -> tuple[str, ...]:
    return ("/v1/score", "/score")


def _is_not_found_error(exc: Exception) -> bool:
    return getattr(exc, "status_code", None) == 404


def _model_ids(response: Any) -> list[str]:
    data = response.get("data") if isinstance(response, dict) else getattr(response, "data", None)
    if not isinstance(data, Sequence):
        return []
    ids: list[str] = []
    for item in data:
        model_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
        if isinstance(model_id, str) and model_id:
            ids.append(model_id)
    return ids


def _extract_score(data: dict[str, Any]) -> float:
    for key in ("score", "relevance_score"):
        if key in data:
            return _normalize_score(data[key])
    rows = data.get("data") or data.get("results") or []
    if isinstance(rows, list) and rows:
        first = rows[0]
        if isinstance(first, dict):
            return _normalize_score(first.get("score", first.get("relevance_score", 0.0)))
        return _normalize_score(first)
    return 0.0


def _normalize_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(score):
        return 0.0
    if 0.0 <= score <= 1.0:
        return score
    return max(0.0, min(1.0, score))


def _with_instruction(text: str, instruction: str) -> str:
    if not instruction.strip():
        return text
    return f"Instruct: {instruction.strip()}\nQuery: {text}"


RerankerEndpoint = Literal["score", "rerank"]
