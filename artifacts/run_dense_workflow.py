"""Patched entry point for the dense workflow renderer."""
from pathlib import Path


source_path = Path(__file__).with_name("render_dense_workflow.py")
source = source_path.read_text(encoding="utf-8")
source = source.replace(
    'F24 = font(24, bold=True)\nF28 = font(28, bold=True)',
    'F24 = font(24, bold=True)\nF26 = font(26, bold=True)\nF28 = font(28, bold=True)',
)
exec(compile(source, str(source_path), "exec"), {"__file__": str(source_path)})
