"""Safe Milvus filter expression compiler."""

from __future__ import annotations

import json
from typing import Any

from .policy import RetrievalPolicy


ALLOWED_FILTER_FIELDS = {
    "doc_id",
    "doc_type",
    "park_id",
    "building_id",
    "system_type",
    "equipment_type",
    "equipment_model",
    "vendor",
    "section_id",
    "knowledge_domain",
    "fault_code",
    "parameter_name",
    "parameter_value",
    "status",
    "review_status",
    "confidential_level",
    "content_type",
    "language",
}

JSON_SCOPE_FIELDS = {"permission_tags", "role_scope", "department_scope"}


def compile_milvus_filter(policy: RetrievalPolicy) -> str | None:
    """Compile backend-owned field filters to a Milvus expression."""

    parts: list[str] = []
    if policy.content_types:
        parts.append(_in_expr("content_type", policy.content_types))
    for field_name, value in policy.field_filters.items():
        if field_name in JSON_SCOPE_FIELDS:
            expr = _json_contains_any_expr(field_name, value)
        elif field_name in ALLOWED_FILTER_FIELDS:
            expr = _value_expr(field_name, value)
        else:
            continue
        if expr:
            parts.append(expr)
    return " and ".join(parts) if parts else None


def _value_expr(field_name: str, value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list | tuple | set):
        values = [str(item) for item in value if item is not None]
        return _in_expr(field_name, values) if values else None
    if isinstance(value, bool):
        return f"{field_name} == {'true' if value else 'false'}"
    if isinstance(value, int | float):
        return f"{field_name} == {value}"
    return f"{field_name} == {_quote(value)}"


def _in_expr(field_name: str, values: list[str]) -> str:
    quoted = ", ".join(_quote(value) for value in values)
    return f"{field_name} in [{quoted}]"


def _json_contains_any_expr(field_name: str, value: Any) -> str | None:
    if value in (None, "", [], {}):
        return None
    values = (
        [str(item) for item in value]
        if isinstance(value, list | tuple | set)
        else [str(value)]
    )
    values = list(dict.fromkeys([item for item in values if item]))
    if not values:
        return None
    if "*" not in values:
        values.append("*")
    return f"json_contains_any({field_name}, {json.dumps(values, ensure_ascii=False)})"


def _quote(value: Any) -> str:
    escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"
