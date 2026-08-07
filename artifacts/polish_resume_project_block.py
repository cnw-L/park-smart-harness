"""Final pass: remove unused bottom canvas while preserving the approved typography."""
from pathlib import Path


source_path = Path(__file__).with_name("render_resume_project_block.py")
source = source_path.read_text(encoding="utf-8")
source = source.replace("W, H = 1600, 1020", "W, H = 1600, 820")
exec(compile(source, str(source_path), "exec"), {"__file__": str(source_path)})
