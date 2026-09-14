"""Execute the alert example renderer with literal source-level line breaks preserved."""
from pathlib import Path


renderer_path = Path(__file__).with_name("render_alert_knowledge_workflow.py")
lines = renderer_path.read_text(encoding="utf-8").splitlines()
inside_content = False
patched: list[str] = []
for line in lines:
    if line.startswith("content = {"):
        inside_content = True
    elif inside_content and line == "}":
        inside_content = False
    if inside_content and "\\n" in line:
        indent = len(line) - len(line.lstrip())
        line = line[:indent] + line[indent:].replace("'", "r'", 1)
    patched.append(line)

renderer = "\n".join(patched) + "\n"
exec(compile(renderer, str(renderer_path), "exec"), {"__file__": str(renderer_path)})
