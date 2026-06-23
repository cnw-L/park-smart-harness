from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

HTML_PATTERN = re.compile(r"</?(table|thead|tbody|tr|td|th|img|html|body)\b", re.IGNORECASE)
IMAGE_PATH_PATTERN = re.compile(
    r"(?:(?:^|[/\\])(?:images?|assets?|figures?)[/\\].*|[/\\][^/\n\\]+\.(?:png|jpe?g|webp|gif|bmp|svg)\b|(?:^|\s)[^\s]+\.(?:png|jpe?g|webp|gif|bmp|svg)\b)",
    re.IGNORECASE,
)
PATH_TITLE_PATTERN = re.compile(
    r"(?:[/\\]|(?:^|\s)[^\s]+\.(?:png|jpe?g|webp|gif|bmp|svg)\b)",
    re.IGNORECASE,
)

PARENT_OPTIONAL_TYPES = {
    "",
    "doc_summary",
    "document",
    "doc",
    "section",
    "section_parent",
    "parent",
    "root",
}


def audit_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit Milvus knowledge chunk rows for typed-evidence field quality issues."""
    counters: Counter[str] = Counter()
    issues: list[dict[str, Any]] = []
    affected_rows: set[str] = set()

    def add_issue(row: dict[str, Any], code: str, field: str, message: str) -> None:
        counters[code] += 1
        row_ref = {
            "chunk_id": row.get("chunk_id"),
            "doc_id": row.get("doc_id"),
            "content_type": row.get("content_type"),
        }
        issues.append(
            {
                "code": code,
                "field": field,
                "message": message,
                "row": row_ref,
            }
        )
        affected_rows.add(str(row.get("chunk_id") or id(row)))

    for row in rows:
        content_type = _normalized(row.get("content_type"))
        chunk_text = _text(row.get("chunk_text"))
        retrieval_text = _text(row.get("retrieval_text"))

        if chunk_text and retrieval_text and chunk_text.strip() == retrieval_text.strip():
            add_issue(
                row,
                "chunk_text_equals_retrieval_text",
                "chunk_text,retrieval_text",
                "chunk_text should be LLM evidence text, not an exact copy of retrieval_text.",
            )

        if content_type not in PARENT_OPTIONAL_TYPES and _is_blank(row.get("parent_chunk_id")):
            add_issue(
                row,
                "missing_parent_chunk_id",
                "parent_chunk_id",
                "Typed evidence child rows should link to a parent chunk or section.",
            )

        if _has_html_pollution(chunk_text, retrieval_text):
            add_issue(
                row,
                "html_pollution",
                "chunk_text,retrieval_text",
                "Evidence fields should not contain raw HTML table or image markup.",
            )

        if _has_image_path_pollution(chunk_text, retrieval_text):
            add_issue(
                row,
                "image_path_pollution",
                "chunk_text,retrieval_text",
                "Text fields should describe image evidence, not expose parser asset paths.",
            )

        if content_type == "fault_code" and _is_blank(row.get("fault_code")):
            add_issue(
                row,
                "fault_code_missing_code",
                "fault_code",
                "fault_code rows must populate the normalized fault_code field.",
            )

        if content_type == "image_ref":
            if _is_blank(row.get("image_asset_id")):
                add_issue(
                    row,
                    "image_ref_missing_asset_id",
                    "image_asset_id",
                    "image_ref rows must link to a stable image_asset_id.",
                )
            if _looks_like_path(row.get("image_title")):
                add_issue(
                    row,
                    "image_title_looks_like_path",
                    "image_title",
                    "image_title should be a human title, not a parser asset path.",
                )

        if _invalid_source_page(row.get("source_page_start")) or _invalid_source_page(
            row.get("source_page_end")
        ):
            add_issue(
                row,
                "invalid_source_page",
                "source_page_start,source_page_end",
                "source page numbers must be positive when present.",
            )

        if content_type == "spec_item":
            if _is_blank(row.get("parameter_name")):
                add_issue(
                    row,
                    "spec_item_missing_parameter_name",
                    "parameter_name",
                    "spec_item rows must populate parameter_name.",
                )
            if _is_blank(row.get("parameter_value")):
                add_issue(
                    row,
                    "spec_item_missing_parameter_value",
                    "parameter_value",
                    "spec_item rows must populate parameter_value.",
                )

    return {
        "summary": {
            "row_count": len(rows),
            "issue_count": len(issues),
            "affected_row_count": len(affected_rows),
        },
        "counters": dict(counters),
        "issues": issues,
    }


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _normalized(value: Any) -> str:
    return _text(value).strip().lower()


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _has_html_pollution(*values: str) -> bool:
    return any(value and HTML_PATTERN.search(value) for value in values)


def _has_image_path_pollution(*values: str) -> bool:
    return any(value and IMAGE_PATH_PATTERN.search(value) for value in values)


def _looks_like_path(value: Any) -> bool:
    text = _text(value).strip()
    return bool(text and PATH_TITLE_PATTERN.search(text))


def _invalid_source_page(value: Any) -> bool:
    if _is_blank(value):
        return False
    try:
        return int(value) <= 0
    except (TypeError, ValueError):
        return True


def load_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        data = json.loads(stripped)
        if not isinstance(data, list):
            raise ValueError("JSON input must be a list of row objects")
        return data
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit Milvus knowledge_chunks field quality from JSON/JSONL rows."
    )
    parser.add_argument("--input", type=Path, required=True, help="JSON array or JSONL row export.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    report = audit_rows(load_rows(args.input))
    output = json.dumps(
        report,
        ensure_ascii=False,
        indent=2 if args.pretty else None,
        sort_keys=False,
    )
    print(output)
    return 1 if report["summary"]["issue_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
