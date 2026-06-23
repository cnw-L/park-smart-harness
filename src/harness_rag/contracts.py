"""RAG tool contracts independent of LangGraph and API transport."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .evidence import EvidenceBundle, EvidenceItem, RetrievalDiagnostics


class RetrievalContext(BaseModel):
    """Backend-owned context used to build filters, not prompt text."""

    user_id: str = ""
    tenant_id: str = ""
    park_id: str = ""
    building_id: str = ""
    permission_tags: list[str] = Field(default_factory=list)
    role_scope: list[str] = Field(default_factory=list)
    department_scope: list[str] = Field(default_factory=list)
    confidential_level: str = ""
    field_filters: dict[str, str | int | float | bool | list[str]] = Field(default_factory=dict)
    conversation_summary: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class RetrievalRequest(BaseModel):
    """Stable request contract for the QA node to call RAG as a tool."""

    query: str
    focus: str = ""
    context: RetrievalContext = Field(default_factory=RetrievalContext)
    top_k: int | None = None
    candidate_limit: int | None = None
    deadline_ms: int | None = None
    allow_second_pass: bool = True


class RetrievalResponse(BaseModel):
    """Stable response contract returned by the RAG tool."""

    evidence: EvidenceBundle

    @property
    def evidence_items(self) -> list[EvidenceItem]:
        return self.evidence.items

    @property
    def diagnostics(self) -> RetrievalDiagnostics | None:
        return self.evidence.diagnostics
