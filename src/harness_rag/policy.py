"""Retrieval policy and LLM query-rewrite contracts."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .config import RagConfig as AssistantConfig
from .evidence import EvidenceItem, RetrievalDiagnostics


CollectionName = Literal["knowledge_chunks"]
PassStage = Literal["first_pass", "repair_pass"]
RankerName = Literal["rrf", "weighted"]


class QueryRewriteStrategy(str, Enum):
    """LLM-selected query rewrite strategy for QA repair."""

    BACKTRACK = "backtrack"
    SUBQUESTIONS = "subquestions"
    SPECIFICATION = "specification"


class QueryRewritePlan(BaseModel):
    """Structured LLM output used only inside QA second-pass retrieval."""

    strategy: QueryRewriteStrategy
    original_query: str = ""
    rewritten_queries: list[str] = Field(min_length=1, max_length=5)
    reason: str = ""


class RetrievalPolicy(BaseModel):
    """Backend-owned retrieval policy for Milvus hybrid search."""

    query: str
    collection: CollectionName = "knowledge_chunks"
    pass_stage: PassStage = "first_pass"
    content_types: list[str] = Field(default_factory=list)
    field_filters: dict[str, str | int | float | bool | list[str]] = Field(default_factory=dict)
    candidate_limit: int = 40
    top_k: int = 8
    rerank_top_k: int = 5
    dense_field: str = "dense"
    sparse_field: str = "sparse"
    text_field: str = "retrieval_text"
    dense_metric_type: str = "IP"
    sparse_metric_type: str = "BM25"
    ranker: RankerName = "rrf"
    weighted_scores: tuple[float, float] = (0.65, 0.35)
    max_expanded_chunks: int = 6
    latency_budget_ms: int = 1800
    original_query: str = ""
    rewritten_queries: list[str] = Field(default_factory=list)
    rewrite_strategy: str = ""
    retrieval_focus: str = ""
    policy_reason: str = ""

    @field_validator("weighted_scores")
    @classmethod
    def validate_weighted_scores(cls, value: tuple[float, float]) -> tuple[float, float]:
        if len(value) != 2:
            raise ValueError("weighted_scores must contain dense and sparse weights")
        if any(score < 0 or score > 1 for score in value):
            raise ValueError("weighted_scores must be between 0 and 1")
        if sum(value) <= 0:
            raise ValueError("weighted_scores must include at least one positive weight")
        return value


def build_initial_policy(query: str, config: AssistantConfig, *, focus: str = "") -> RetrievalPolicy:
    """Build a first-pass policy with optional QA semantic focus.

    Focus is a soft QA hint from the supervisor. It can widen the first-pass
    candidate window, but it never becomes a Milvus filter or query rewrite.
    """

    normalized_focus = _normalize_focus(focus)
    candidate_limit = config.retrieval_candidate_limit
    top_k = config.retrieval_top_k
    if normalized_focus in {"procedure", "fault", "parameter"}:
        candidate_limit = max(candidate_limit, min(candidate_limit + 10, 60))
    elif normalized_focus == "source":
        candidate_limit = max(candidate_limit, min(candidate_limit + 20, 80))
        top_k = max(top_k, min(top_k + 2, 12))

    return RetrievalPolicy(
        query=query,
        original_query=query,
        rewritten_queries=[query],
        candidate_limit=candidate_limit,
        top_k=top_k,
        rerank_top_k=config.rerank_top_k,
        latency_budget_ms=config.retrieval_latency_budget_ms,
        retrieval_focus=normalized_focus,
        policy_reason=_initial_policy_reason(normalized_focus),
    )


def should_repair(
    items: list[EvidenceItem],
    diagnostics: RetrievalDiagnostics,
    config: AssistantConfig,
    *,
    focus: str = "",
) -> tuple[bool, str]:
    """Decide whether QA should pay for LLM query rewrite and second retrieval."""

    if not items:
        return True, "no_evidence"
    score = diagnostics.best_rerank_score
    if score is not None and score < config.retry_low_threshold:
        return True, "rerank_score_too_low"
    if _has_critical_missing_fields(diagnostics):
        return True, "missing_critical_source"
    if _summary_only(items):
        return True, "summary_only"
    normalized_focus = _normalize_focus(focus)
    if normalized_focus == "parameter" and not _has_parameter_evidence(items):
        return True, "missing_parameter_evidence"
    if normalized_focus == "fault" and not _has_fault_evidence(items):
        return True, "missing_fault_evidence"
    if normalized_focus == "procedure" and not _has_procedure_evidence(items):
        return True, "missing_procedure_evidence"
    return False, ""


def build_repair_policy(
    policy: RetrievalPolicy,
    *,
    rewrite_plan: QueryRewritePlan,
    candidate_limit: int,
) -> RetrievalPolicy:
    """Build the second-pass retrieval policy from an LLM rewrite plan."""

    queries = _clean_queries(rewrite_plan.rewritten_queries, fallback=policy.original_query or policy.query)
    return policy.model_copy(
        update={
            "query": queries[0],
            "pass_stage": "repair_pass",
            "candidate_limit": candidate_limit,
            "rewrite_strategy": rewrite_plan.strategy.value,
            "rewritten_queries": queries,
            "policy_reason": f"llm query rewrite: {rewrite_plan.reason}".strip(),
        }
    )


def _clean_queries(queries: list[str], *, fallback: str) -> list[str]:
    cleaned = [query.strip() for query in queries if query.strip()]
    return list(dict.fromkeys(cleaned))[:5] or [fallback]


def _normalize_focus(focus: str) -> str:
    normalized = focus.strip().lower()
    return normalized if normalized in {"general", "procedure", "fault", "parameter", "source"} else ""


def _initial_policy_reason(focus: str) -> str:
    if not focus or focus == "general":
        return "first-pass original query retrieval"
    return f"first-pass original query retrieval; qa_focus={focus}"


def _summary_only(items: list[EvidenceItem]) -> bool:
    return bool(items) and all(item.content_type.endswith("summary") for item in items)


def _has_critical_missing_fields(diagnostics: RetrievalDiagnostics) -> bool:
    missing = set(diagnostics.missing_required_fields)
    return bool(missing.intersection({"evidence", "source"}))


def _has_parameter_evidence(items: list[EvidenceItem]) -> bool:
    return any(
        item.content_type == "spec_item" or item.parameter_name or item.parameter_value
        for item in items
    )


def _has_fault_evidence(items: list[EvidenceItem]) -> bool:
    return any(
        item.content_type in {"fault_code", "procedure_step", "warning_item"} or item.fault_code
        for item in items
    )


def _has_procedure_evidence(items: list[EvidenceItem]) -> bool:
    return any(item.content_type in {"procedure_step", "warning_item"} for item in items)
