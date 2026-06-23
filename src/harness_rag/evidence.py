"""Evidence contracts for assistant_core RAG."""

from __future__ import annotations

from collections import Counter
from typing import Any, Literal

from pydantic import BaseModel, Field


EvidenceStage = Literal["first_pass", "repair_pass", "expansion"]


class EvidenceItem(BaseModel):
    """Answer-facing evidence returned by retrieval and reranking."""

    id: str
    chunk_id: str | None = None
    doc_id: str | None = None
    section_id: str | None = None
    parent_chunk_id: str | None = None
    chunk_text: str
    content_type: str = ""
    doc_type: str = ""
    knowledge_domain: str = ""
    source_title: str = ""
    section_title: str = ""
    source_page_start: int | None = None
    source_page_end: int | None = None
    source_locator: str = ""
    equipment_type: str = ""
    equipment_model: str = ""
    fault_code: str = ""
    fault_symptom: str = ""
    parameter_name: str = ""
    parameter_value: str = ""
    image_asset_id: str = ""
    linked_raw_chunk_ids: list[str] = Field(default_factory=list)
    linked_image_ids: list[str] = Field(default_factory=list)
    permission_tags: list[str] = Field(default_factory=list)
    role_scope: list[str] = Field(default_factory=list)
    department_scope: list[str] = Field(default_factory=list)
    confidential_level: str = ""
    query_variant: str = ""
    rerank_score: float | None = Field(default=None, ge=0, le=1)
    rank: int | None = None
    source_stage: EvidenceStage = "first_pass"
    extra_metadata: dict[str, Any] = Field(default_factory=dict)
    # small-to-big: when a fine-grained child chunk (e.g. one table row) is the
    # retrieval hit, expanded_text carries the larger parent block (whole table /
    # section) for the answer model. expanded_chunk_id dedupes siblings sharing it.
    expanded_text: str = ""
    expanded_chunk_id: str = ""

    @property
    def answer_text(self) -> str:
        return self.chunk_text.strip()

    @property
    def prompt_body(self) -> str:
        """Text fed to the answer model: parent block if expanded, else the chunk."""

        return self.expanded_text.strip() if self.expanded_text.strip() else self.answer_text

    @property
    def citation_label(self) -> str:
        parts = [self.source_title or self.doc_id or self.id]
        if self.source_page_start:
            page = str(self.source_page_start)
            if self.source_page_end and self.source_page_end != self.source_page_start:
                page = f"{page}-{self.source_page_end}"
            parts.append(f"p.{page}")
        if self.source_locator:
            parts.append(self.source_locator)
        return " / ".join(part for part in parts if part)


class RetrievalDiagnostics(BaseModel):
    """Small, stable diagnostics for QA and streaming events."""

    best_rerank_score: float | None = Field(default=None, ge=0, le=1)
    candidate_count: int = 0
    returned_count: int = 0
    evidence_count: int = 0
    matched_content_types: dict[str, int] = Field(default_factory=dict)
    missing_required_fields: list[str] = Field(default_factory=list)
    duplicate_count: int = 0
    reranker_used: bool = False
    second_pass_used: bool = False
    should_retry: bool = False
    retry_reason: str = ""
    retry_error: str = ""
    retrieval_passes: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: int = 0
    latency_budget_exhausted: bool = False
    skipped_reason: str = ""


class EvidenceBundle(BaseModel):
    """Final evidence package consumed by the QA answer node."""

    query: str
    items: list[EvidenceItem] = Field(default_factory=list)
    repair_items: list[EvidenceItem] = Field(default_factory=list)
    reason: str = ""
    policy: Any | None = None
    repair_policy: Any | None = None
    sufficiency_threshold: float = 0.7
    insufficient_evidence_reason: str = ""
    diagnostics: RetrievalDiagnostics | None = None

    @property
    def all_items(self) -> list[EvidenceItem]:
        return [*self.items, *self.repair_items]

    @property
    def primary_evidence(self) -> list[EvidenceItem]:
        return self.items

    @property
    def supplemental_context(self) -> list[EvidenceItem]:
        return self.repair_items

    @property
    def best_rerank_score(self) -> float | None:
        scores = [item.rerank_score for item in self.items if item.rerank_score is not None]
        return max(scores, default=None)

    @property
    def sufficient(self) -> bool:
        score = self.best_rerank_score
        return bool(self.items) and score is not None and score >= self.sufficiency_threshold


def dedupe_evidence(items: list[EvidenceItem]) -> tuple[list[EvidenceItem], int]:
    """Dedupe by stable chunk identity, then source/page/text fallback."""

    seen: set[tuple[Any, ...]] = set()
    deduped: list[EvidenceItem] = []
    duplicate_count = 0
    for item in items:
        key = _evidence_key(item)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        deduped.append(item)
    return deduped, duplicate_count


def merge_primary_and_supplemental(
    primary: list[EvidenceItem],
    supplemental: list[EvidenceItem],
) -> tuple[list[EvidenceItem], list[EvidenceItem], int]:
    """Keep reranked primary evidence first and attach deduped supplemental context."""

    merged_primary, primary_duplicates = dedupe_evidence(primary)
    primary_keys = {_evidence_key(item) for item in merged_primary}
    merged_supplemental: list[EvidenceItem] = []
    supplemental_duplicates = 0
    seen_supplemental: set[tuple[Any, ...]] = set()
    for item in supplemental:
        key = _evidence_key(item)
        if key in primary_keys or key in seen_supplemental:
            supplemental_duplicates += 1
            continue
        seen_supplemental.add(key)
        merged_supplemental.append(item)
    return merged_primary, merged_supplemental, primary_duplicates + supplemental_duplicates


def diagnose_evidence(
    items: list[EvidenceItem],
    *,
    candidate_count: int,
    duplicate_count: int = 0,
    reranker_used: bool = False,
    second_pass_used: bool = False,
    latency_ms: int = 0,
    latency_budget_exhausted: bool = False,
    retry_reason: str = "",
    retry_error: str = "",
    retrieval_passes: list[dict[str, Any]] | None = None,
    skipped_reason: str = "",
) -> RetrievalDiagnostics:
    scores = [item.rerank_score for item in items if item.rerank_score is not None]
    required_missing: list[str] = []
    if not items:
        required_missing.append("evidence")
    if items and not any(item.source_title or item.doc_id for item in items):
        required_missing.append("source")
    if items and not any(item.source_page_start or item.source_locator for item in items):
        required_missing.append("citation_locator")

    return RetrievalDiagnostics(
        best_rerank_score=max(scores, default=None),
        candidate_count=candidate_count,
        returned_count=len(items),
        evidence_count=len(items),
        matched_content_types=dict(Counter(item.content_type for item in items if item.content_type)),
        missing_required_fields=required_missing,
        duplicate_count=duplicate_count,
        reranker_used=reranker_used,
        second_pass_used=second_pass_used,
        should_retry=bool(retry_reason),
        retry_reason=retry_reason,
        retry_error=retry_error,
        retrieval_passes=retrieval_passes or [],
        latency_ms=latency_ms,
        latency_budget_exhausted=latency_budget_exhausted,
        skipped_reason=skipped_reason,
    )


def render_evidence_for_prompt(bundle: EvidenceBundle, *, limit: int = 6) -> str:
    """Render concise evidence snippets for the answer model."""

    if not bundle.all_items:
        return "No knowledge-base evidence was retrieved."
    seen_parents: set[str] = set()
    primary_limit = min(limit, len(bundle.items))
    prompt_primary = arrange_evidence_for_prompt(bundle.items[:primary_limit], focus=_bundle_focus(bundle))
    snippets = _render_section(prompt_primary, "primary", seen_parents, limit, with_score=True)
    remaining = limit - len(snippets)
    if remaining > 0:
        snippets += _render_section(
            bundle.repair_items, "supplemental", seen_parents, remaining, with_score=False
        )
    return "\n\n".join(snippets)


def _render_section(
    items: list[EvidenceItem],
    tag: str,
    seen_parents: set[str],
    limit: int,
    *,
    with_score: bool,
) -> list[str]:
    """Render up to `limit` snippets, skipping items whose expanded parent block
    was already rendered. Iterates the full list (not a pre-slice) so skipped
    duplicates don't waste a slot — a later distinct item still gets rendered.
    """

    out: list[str] = []
    for item in items:
        if len(out) >= limit:
            break
        if item.expanded_chunk_id and item.expanded_chunk_id in seen_parents:
            continue
        if item.expanded_chunk_id:
            seen_parents.add(item.expanded_chunk_id)
        score = (
            f" score={item.rerank_score:.3f}"
            if with_score and item.rerank_score is not None
            else ""
        )
        out.append(f"[{tag} {len(out) + 1}] {item.citation_label}{score}\n{item.prompt_body}")
    return out


def arrange_evidence_for_prompt(items: list[EvidenceItem], *, focus: str = "") -> list[EvidenceItem]:
    """Optimize prompt order without changing the reranked evidence order."""

    if len(items) <= 3 or focus in {"source", "procedure"}:
        return list(items)

    front: list[EvidenceItem] = []
    back: list[EvidenceItem] = []
    middle: list[EvidenceItem] = []
    for index, item in enumerate(items):
        if index == 0 or index % 2 == 0:
            front.append(item)
        elif index == 1:
            back.append(item)
        else:
            middle.append(item)
    return [*front, *middle, *reversed(back)]


def _bundle_focus(bundle: EvidenceBundle) -> str:
    policy = bundle.policy
    focus = getattr(policy, "retrieval_focus", "")
    return focus if isinstance(focus, str) else ""


def _evidence_key(item: EvidenceItem) -> tuple[Any, ...]:
    return (
        item.chunk_id or item.id,
        item.doc_id,
        item.source_page_start,
        item.answer_text[:160],
    )
