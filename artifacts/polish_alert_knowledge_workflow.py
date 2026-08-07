"""Final pass: strengthen only the active ALLOW path for the alert example."""
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
renderer = renderer.replace(
    'exec(compile(source, str(source_path), "exec"), {"__file__": str(source_path)})',
    'source = source.replace("arrow(900, 1305, 760, 1348, color=GREEN, width=2)", '
    '"arrow(900, 1305, 760, 1348, color=GREEN, width=4)")\n'
    'source = source.replace("arrow(760, 1480, 760, 1523, color=GREEN, width=2)", '
    '"arrow(760, 1480, 760, 1523, color=GREEN, width=4)")\n'
    'source = source.replace("arrow(550, 1628, 550, 1808, color=GREEN, width=2)", '
    '"arrow(550, 1628, 550, 1808, color=GREEN, width=4)")\n'
    'exec(compile(source, str(source_path), "exec"), {"__file__": str(source_path)})',
)
exec(compile(renderer, str(renderer_path), "exec"), {"__file__": str(renderer_path)})
