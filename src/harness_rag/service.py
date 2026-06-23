"""RAG retrieval service used by the QA node."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Protocol

from .config import RagConfig as AssistantConfig
from .contracts import RetrievalRequest, RetrievalResponse
from .evidence import (
    EvidenceBundle,
    EvidenceItem,
    RetrievalDiagnostics,
    dedupe_evidence,
    diagnose_evidence,
    merge_primary_and_supplemental,
    render_evidence_for_prompt,
)
from .policy import QueryRewritePlan, RetrievalPolicy, build_initial_policy, build_repair_policy, should_repair
from .rerank import Reranker, rerank_or_keep


class KnowledgeRetriever(Protocol):
    async def retrieve(self, policy: RetrievalPolicy) -> list[EvidenceItem] | EvidenceBundle:
        ...


class QueryRewriter(Protocol):
    async def rewrite(
        self,
        *,
        query: str,
        reason: str,
        evidence: list[EvidenceItem],
        diagnostics: RetrievalDiagnostics,
        max_queries: int,
    ) -> QueryRewritePlan:
        ...


@dataclass(frozen=True)
class RetrievedCandidates:
    items: list[EvidenceItem]
    query_traces: list[dict[str, object]]


async def retrieve_evidence(
    query: str,
    *,
    config: AssistantConfig,
    retriever: KnowledgeRetriever | None,
    reranker: Reranker | None = None,
    query_rewriter: QueryRewriter | None = None,
    field_filters: dict[str, str | int | float | bool | list[str]] | None = None,
    focus: str = "",
) -> EvidenceBundle:
    """Retrieve primary evidence, optionally attach one supplemental context pass."""

    request = RetrievalRequest(
        query=query,
        focus=focus,
        context={"field_filters": field_filters or {}},
    )
    response = await retrieve_with_request(
        request,
        config=config,
        retriever=retriever,
        reranker=reranker,
        query_rewriter=query_rewriter,
    )
    return response.evidence


async def retrieve_with_request(
    request: RetrievalRequest,
    *,
    config: AssistantConfig,
    retriever: KnowledgeRetriever | None,
    reranker: Reranker | None = None,
    query_rewriter: QueryRewriter | None = None,
) -> RetrievalResponse:
    """Retrieve evidence through the stable RAG tool request contract."""

    started = monotonic()
    policy = build_initial_policy(request.query, config, focus=request.focus)
    policy_updates = {}
    context_filters = _context_filters(request)
    if context_filters:
        policy_updates["field_filters"] = context_filters
    if request.top_k is not None:
        policy_updates["top_k"] = request.top_k
    if request.candidate_limit is not None:
        policy_updates["candidate_limit"] = request.candidate_limit
    if request.deadline_ms is not None:
        policy_updates["latency_budget_ms"] = request.deadline_ms
    if policy_updates:
        policy = policy.model_copy(update=policy_updates)
    if retriever is None:
        diagnostics = diagnose_evidence(
            [],
            candidate_count=0,
            latency_ms=_elapsed_ms(started),
            skipped_reason="knowledge_retriever_not_configured",
        )
        return RetrievalResponse(
            evidence=EvidenceBundle(
                query=request.query,
                reason="Knowledge retriever is not configured.",
                policy=policy,
                insufficient_evidence_reason="knowledge_retriever_not_configured",
                diagnostics=diagnostics,
            )
        )

    first_result = await _retrieve_candidates(retriever, policy, source_stage="first_pass", max_queries=1)
    first_candidates = first_result.items
    first_ranked, first_reranker_used = await rerank_or_keep(
        request.query,
        first_candidates,
        reranker=reranker,
        top_k=max(policy.top_k, policy.rerank_top_k),
    )
    initial_diagnostics = diagnose_evidence(
        first_ranked,
        candidate_count=len(first_candidates),
        reranker_used=first_reranker_used,
        latency_ms=_elapsed_ms(started),
        retrieval_passes=[_pass_trace(policy, first_result.query_traces, pass_index=1)],
    )
    repair_items: list[EvidenceItem] = []
    repair_ranked: list[EvidenceItem] = []
    repair_traces: list[dict[str, object]] = []
    repair_duplicates = 0
    repair_used = False
    repair_reranker_used = False
    retry_reason = ""
    repair_policy: RetrievalPolicy | None = None
    rewrite_plan: QueryRewritePlan | None = None
    retry_error = ""

    should_retry, retry_reason = should_repair(
        first_ranked,
        initial_diagnostics,
        config,
        focus=policy.retrieval_focus,
    )
    if (
        request.allow_second_pass
        and should_retry
        and query_rewriter is not None
        and _has_budget(started, policy.latency_budget_ms)
    ):
        try:
            rewrite_plan = await query_rewriter.rewrite(
                query=request.query,
                reason=retry_reason,
                evidence=first_ranked,
                diagnostics=initial_diagnostics,
                max_queries=config.repair_rewrite_query_limit,
            )
            repair_policy = build_repair_policy(
                policy,
                rewrite_plan=rewrite_plan,
                candidate_limit=config.repair_candidate_limit_per_query,
            )
            repair_result = await _retrieve_candidates(
                retriever,
                repair_policy,
                source_stage="repair_pass",
                max_queries=config.repair_rewrite_query_limit,
            )
            repair_items = repair_result.items
            repair_candidates, repair_duplicates = dedupe_evidence(repair_items)
            repair_candidates = repair_candidates[: config.repair_merged_candidate_limit]
            repair_ranked, repair_reranker_used = await rerank_or_keep(
                _repair_rerank_query(request.query, rewrite_plan),
                repair_candidates,
                reranker=reranker,
                top_k=max(repair_policy.top_k, repair_policy.rerank_top_k),
            )
            repair_traces = repair_result.query_traces
            repair_used = True
        except Exception as exc:
            retry_reason = "query_rewrite_failed"
            retry_error = f"{exc.__class__.__name__}: {exc}"
    elif should_retry and not request.allow_second_pass:
        retry_reason = "second_pass_disabled"
    elif should_retry and query_rewriter is None:
        retry_reason = "query_rewriter_not_configured"
    elif should_retry:
        retry_reason = "latency_budget_exhausted"

    repair_promoted = _should_promote_repair(first_ranked, initial_diagnostics, repair_ranked, config)
    primary_seed = repair_ranked[: policy.top_k] if repair_promoted else first_ranked[: policy.top_k]
    supplemental_seed = first_ranked[: policy.top_k] if repair_promoted else repair_ranked
    primary_items, supplemental_items, duplicate_count = merge_primary_and_supplemental(primary_seed, supplemental_seed)
    # Expand both tiers so supplemental rows of the same table get tagged with the
    # parent's expanded_chunk_id too — render-time dedup is cross-tier, so this
    # stops a table appearing as a whole-block (primary) and stray rows (supplemental).
    # Fetch parents once across both tiers (overlapping parent ids hit Milvus only once).
    parent_texts = await _fetch_parent_texts(primary_items + supplemental_items, retriever, config)
    primary_items = _apply_parent_texts(primary_items, parent_texts)
    supplemental_items = _apply_parent_texts(supplemental_items, parent_texts)
    duplicate_count += repair_duplicates if repair_used else 0
    pass_traces = [_pass_trace(policy, first_result.query_traces, pass_index=1)]
    if repair_policy is not None:
        pass_traces.append(_pass_trace(repair_policy, repair_traces, pass_index=2))
    diagnostics = diagnose_evidence(
        primary_items,
        candidate_count=len(first_candidates) + len(repair_items),
        duplicate_count=duplicate_count,
        reranker_used=first_reranker_used or repair_reranker_used,
        second_pass_used=repair_used,
        latency_ms=_elapsed_ms(started),
        latency_budget_exhausted=not _has_budget(started, policy.latency_budget_ms),
        retry_reason=retry_reason,
        retry_error=retry_error,
        retrieval_passes=pass_traces,
    )
    bundle = EvidenceBundle(
        query=request.query,
        items=primary_items,
        repair_items=supplemental_items,
        reason=_reason(diagnostics),
        policy=policy,
        repair_policy=repair_policy,
        sufficiency_threshold=config.second_pass_threshold,
        diagnostics=diagnostics,
    )
    return RetrievalResponse(
        evidence=bundle.model_copy(
            update={"insufficient_evidence_reason": "" if bundle.sufficient else _reason(diagnostics)}
        )
    )


def evidence_prompt(bundle: EvidenceBundle) -> str:
    return render_evidence_for_prompt(bundle)


def _context_filters(request: RetrievalRequest) -> dict[str, str | int | float | bool | list[str]]:
    # ★harness fork:`field_filters` 来自**可信注入层**(knowledge 工具据登录态 principal 编译,
    #   模型绝不经手)→ 其中的密级/作用域字段就是权限口径,必须**透传到 Milvus**,不能丢。
    #   上游原版会剥离这几个"protected scope"字段(防调用方经 field_filters 伪造),但那针对的是
    #   不可信入参;本仓注入层可信,剥离会导致**零权限隔离**(实测:伪造密级档位仍返全部)。
    #   compile_milvus_filter 已按 ALLOWED/JSON 白名单兜底,无任意字段注入风险。
    #   dedicated context.* 仍可覆盖(优先级更高)。confidential_level 支持多档位列表(IN 匹配)。
    filters: dict[str, str | int | float | bool | list[str]] = dict(request.context.field_filters)
    if request.context.park_id:
        filters.setdefault("park_id", request.context.park_id)
    if request.context.building_id:
        filters.setdefault("building_id", request.context.building_id)
    if request.context.permission_tags:
        filters["permission_tags"] = request.context.permission_tags
    if request.context.role_scope:
        filters["role_scope"] = request.context.role_scope
    if request.context.department_scope:
        filters["department_scope"] = request.context.department_scope
    if request.context.confidential_level:
        filters["confidential_level"] = request.context.confidential_level
    return filters


async def _retrieve_candidates(
    retriever: KnowledgeRetriever,
    policy: RetrievalPolicy,
    *,
    source_stage: str,
    max_queries: int,
) -> RetrievedCandidates:
    queries = policy.rewritten_queries or [policy.query]
    items: list[EvidenceItem] = []
    query_traces: list[dict[str, object]] = []
    for variant_index, rewritten_query in enumerate(queries[:max_queries], start=1):
        result = await retriever.retrieve(policy.model_copy(update={"query": rewritten_query}))
        if isinstance(result, EvidenceBundle):
            query_items = result.items
        else:
            query_items = result
        query_items = [
            item.model_copy(update={"source_stage": source_stage, "query_variant": rewritten_query})
            for item in query_items
        ]
        items.extend(query_items)
        query_traces.append(
            {
                "variant_index": variant_index,
                "query": rewritten_query,
                "item_count": len(query_items),
            }
        )
    return RetrievedCandidates(items=items, query_traces=query_traces)


def _parent_id(item: EvidenceItem) -> str:
    # small-to-big回捞目标: use linked_raw_chunk_ids (the whole table/block the row
    # was split from), not parent_chunk_id — the latter can point to a smaller
    # section summary. Current ingestion links each typed chunk to exactly one
    # raw_child, so [0] is the whole-table/section parent; if ingestion ever writes
    # multiple raw ids, only the first is expanded here — revisit.
    pid = item.linked_raw_chunk_ids[0] if item.linked_raw_chunk_ids else ""
    return pid if pid and pid != item.chunk_id else ""


async def _fetch_parent_texts(
    items: list[EvidenceItem],
    retriever: KnowledgeRetriever | None,
    config: AssistantConfig,
) -> dict[str, str]:
    """Fetch parent-block texts for all items' parents in one Milvus round-trip.

    Returns {} (caller treats as no-op) when disabled, the retriever can't fetch,
    there are no targets, or the fetch fails. Splitting fetch from apply lets the
    caller dedupe targets across evidence tiers and fetch them only once.
    """

    if not getattr(config, "rag_parent_expansion", True) or not items:
        return {}
    fetch = getattr(retriever, "afetch_chunk_texts", None)
    if fetch is None:
        return {}
    targets = list(dict.fromkeys(pid for item in items if (pid := _parent_id(item))))
    if not targets:
        return {}
    try:
        return await fetch(targets)
    except Exception:
        return {}


def _apply_parent_texts(
    items: list[EvidenceItem], parent_texts: dict[str, str]
) -> list[EvidenceItem]:
    """Attach the parent block as expanded_text for each item (sync, pure)."""

    if not parent_texts:
        return items
    expanded: list[EvidenceItem] = []
    for item in items:
        pid = _parent_id(item)
        parent_text = parent_texts.get(pid, "") if pid else ""
        if parent_text.strip():
            expanded.append(
                item.model_copy(update={"expanded_text": parent_text, "expanded_chunk_id": pid})
            )
        else:
            expanded.append(item)
    return expanded


async def _expand_parents(
    items: list[EvidenceItem],
    retriever: KnowledgeRetriever | None,
    config: AssistantConfig,
) -> list[EvidenceItem]:
    """small-to-big for one tier: fetch parent blocks then attach them."""

    parent_texts = await _fetch_parent_texts(items, retriever, config)
    return _apply_parent_texts(items, parent_texts)


def _has_budget(started: float, budget_ms: int) -> bool:
    return _elapsed_ms(started) < budget_ms


def _elapsed_ms(started: float) -> int:
    return int((monotonic() - started) * 1000)


def _reason(diagnostics) -> str:
    if not diagnostics.evidence_count:
        return "No evidence retrieved."
    if diagnostics.reranker_used and diagnostics.best_rerank_score is not None:
        return f"Best reranker score: {diagnostics.best_rerank_score:.3f}."
    return "Evidence retrieved without external reranker."


def _should_promote_repair(
    first_ranked: list[EvidenceItem],
    initial_diagnostics,
    repair_ranked: list[EvidenceItem],
    config: AssistantConfig,
) -> bool:
    """Promote repair evidence only when first-pass evidence is absent or unusable."""

    if not repair_ranked:
        return False
    repair_scores = [item.rerank_score for item in repair_ranked if item.rerank_score is not None]
    if not repair_scores or max(repair_scores) < config.second_pass_threshold:
        return False
    first_score = initial_diagnostics.best_rerank_score
    return not first_ranked or first_score is None or first_score < config.retry_low_threshold


def _repair_rerank_query(original_query: str, rewrite_plan: QueryRewritePlan) -> str:
    rewritten = "\n".join(rewrite_plan.rewritten_queries)
    return f"{original_query}\n{rewritten}" if rewritten else original_query


def _pass_trace(
    policy: RetrievalPolicy,
    query_traces: list[dict[str, object]],
    *,
    pass_index: int,
) -> dict[str, object]:
    return {
        "pass_index": pass_index,
        "pass_stage": policy.pass_stage,
        "rewrite_strategy": policy.rewrite_strategy,
        "candidate_limit": policy.candidate_limit,
        "candidate_count": sum(int(trace.get("item_count", 0)) for trace in query_traces),
        "content_types": policy.content_types,
        "retrieval_focus": policy.retrieval_focus,
        "queries": query_traces,
    }
