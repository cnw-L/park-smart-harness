"""QA-internal LLM query rewrite for second-pass retrieval.

harness 版:不依赖 assistant_core 的 models/config/langchain。改写所需的 LLM 调用经注入的
`ChatCompleter`(`async (system, user) -> str`)——harness 接线边给(复用自家 model caller),
保持 vendored RAG 与 assistant_core 互不影响。二轮自纠正可选(service 里 rewriter=None 即关)。
"""

from __future__ import annotations

from typing import Protocol

from .evidence import EvidenceItem, RetrievalDiagnostics
from .policy import QueryRewritePlan, QueryRewriteStrategy
from .prompts import QA_QUERY_REWRITE_PROMPT


class ChatCompleter(Protocol):
    async def __call__(self, *, system: str, user: str) -> str: ...


class LlmQueryRewriter:
    """文本协议的 query 改写器。LLM 调用经注入的 `chat`(harness 自家 model caller 包成)。"""

    def __init__(self, chat: ChatCompleter) -> None:
        self._chat = chat

    async def rewrite(
        self,
        *,
        query: str,
        reason: str,
        evidence: list[EvidenceItem],
        diagnostics: RetrievalDiagnostics,
        max_queries: int,
    ) -> QueryRewritePlan:
        output = await self._chat(
            system=QA_QUERY_REWRITE_PROMPT,
            user=_rewrite_prompt(query, reason, evidence, diagnostics, max_queries),
        )
        return parse_rewrite_plan(output, original_query=query, max_queries=max_queries)


def parse_rewrite_plan(text: str, *, original_query: str, max_queries: int) -> QueryRewritePlan:
    strategy = QueryRewriteStrategy.BACKTRACK
    queries: list[str] = []
    reason = ""
    for raw in text.splitlines():
        line = raw.strip().lstrip("-*0123456789.、 ")
        if not line:
            continue
        if ":" in line or "：" in line:
            key, value = _split_key_value(line)
            if key in {"strategy", "策略"}:
                strategy = _parse_strategy(value) or strategy
                continue
            if key in {"query", "queries", "检索词", "问题"}:
                queries.extend(_split_queries(value))
                continue
            if key in {"reason", "原因"}:
                reason = value
                continue
        if "|" in line:
            parts = [part.strip() for part in line.split("|") if part.strip()]
            if parts:
                maybe_strategy = _parse_strategy(parts[0])
                if maybe_strategy:
                    strategy = maybe_strategy
                    queries.extend(parts[1:])
                else:
                    queries.extend(parts)
                continue
        queries.append(line)
    cleaned = list(dict.fromkeys(query for query in queries if query.strip()))[:max_queries]
    if not cleaned:
        cleaned = [original_query]
    return QueryRewritePlan(
        strategy=strategy,
        original_query=original_query,
        rewritten_queries=cleaned,
        reason=reason,
    )


def _rewrite_prompt(
    query: str,
    reason: str,
    evidence: list[EvidenceItem],
    diagnostics: RetrievalDiagnostics,
    max_queries: int,
) -> str:
    snippets = "\n".join(f"- {item.citation_label}: {item.answer_text[:180]}" for item in evidence[:3])
    best_score = getattr(diagnostics, "best_rerank_score", None)
    return (
        f"原始问题：\n{query}\n\n"
        f"首轮检索失败原因：\n{reason}\n"
        f"最佳 reranker 分数：{best_score}\n"
        f"最多改写 query 数量：{max_queries}\n\n"
        f"首轮片段：\n{snippets or '无'}"
    )


def _split_key_value(line: str) -> tuple[str, str]:
    if ":" in line:
        key, value = line.split(":", 1)
    else:
        key, value = line.split("：", 1)
    return key.strip().lower(), value.strip()


def _split_queries(value: str) -> list[str]:
    if not value:
        return []
    for separator in ["；", ";", "，", ","]:
        value = value.replace(separator, "\n")
    return [part.strip() for part in value.splitlines() if part.strip()]


def _parse_strategy(value: str) -> QueryRewriteStrategy | None:
    normalized = value.strip().lower()
    if normalized in {"subquestions", "subquestion", "子问题"}:
        return QueryRewriteStrategy.SUBQUESTIONS
    if normalized in {"specification", "specific", "具体化"}:
        return QueryRewriteStrategy.SPECIFICATION
    if normalized in {"backtrack", "回溯"}:
        return QueryRewriteStrategy.BACKTRACK
    return None
