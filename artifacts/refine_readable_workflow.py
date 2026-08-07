"""Second-pass renderer: increase only the essential step copy for small-screen reading."""
from pathlib import Path


source_path = Path(__file__).with_name("render_readable_workflow.py")
source = source_path.read_text(encoding="utf-8")
source = source.replace(
    'text((x + w / 2, y1 + 184 + i * 29), line, F18, MUTED, "ma")',
    'text((x + w / 2, y1 + 184 + i * 31), line, F20, MUTED, "ma")',
)
exec(compile(source, str(source_path), "exec"), {"__file__": str(source_path)})
