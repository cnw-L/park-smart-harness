"""Second-pass renderer: refine the control boundary without mutating the base study."""
from pathlib import Path


source_path = Path(__file__).with_name("render_control_trace.py")
source = source_path.read_text(encoding="utf-8")
source = source.replace(
    'step(1010, 500, "05", "冻结控制提案", "target=24℃ · no handle to model", CYAN)\n'
    'arrow((1025, 500), (1080, 500), AMBER, 4)\n'
    'txt((1170, 545), "CONTROL AIR GAP", F22, AMBER, "ma")\n'
    'txt((1170, 578), "模型到此为止", F18, MUTED, "ma")',
    'step(960, 500, "05", "冻结控制提案", "24℃ · opaque handle", CYAN)\n'
    'arrow((975, 500), (1080, 500), AMBER, 4)\n'
    'txt((1170, 540), "CONTROL AIR GAP", F14, AMBER, "ma")\n'
    'txt((1170, 580), "模型不可越过", F26, TEXT, "ma")',
)
exec(compile(source, str(source_path), "exec"), {"__file__": str(source_path)})
