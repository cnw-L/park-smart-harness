"""External reranker ports and helpers."""

from __future__ import annotations

from typing import Protocol

from .evidence import EvidenceItem


class Reranker(Protocol):
    async def rerank(self, query: str, evidence: list[EvidenceItem], *, top_k: int) -> list[EvidenceItem]:
        ...


async def rerank_or_keep(
    query: str,
    items: list[EvidenceItem],
    *,
    reranker: Reranker | None,
    top_k: int,
) -> tuple[list[EvidenceItem], bool]:
    """Run the external reranker once, falling back to current order."""

    if reranker is None or not items:
        return _with_rank(items[:top_k]), False
    try:
        ranked = await reranker.rerank(query, items, top_k=top_k)
    except Exception:
        return _with_rank(items[:top_k]), False
    return _with_rank(ranked[:top_k]), True


def _with_rank(items: list[EvidenceItem]) -> list[EvidenceItem]:
    return [item.model_copy(update={"rank": index}) for index, item in enumerate(items, start=1)]
