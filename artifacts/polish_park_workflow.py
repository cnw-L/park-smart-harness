"""Final typography pass over the faithful optimized renderer."""
from pathlib import Path


optimizer_path = Path(__file__).with_name("optimize_park_workflow.py")
optimizer = optimizer_path.read_text(encoding="utf-8")
optimizer = optimizer.replace(
    'exec(compile(source, str(source_path), "exec"), {"__file__": str(source_path)})',
    'source = source.replace("title_size=22", "title_size=23")\n'
    'source = source.replace("title_size=23", "title_size=24")\n'
    'exec(compile(source, str(source_path), "exec"), {"__file__": str(source_path)})',
)
exec(compile(optimizer, str(optimizer_path), "exec"), {"__file__": str(optimizer_path)})
