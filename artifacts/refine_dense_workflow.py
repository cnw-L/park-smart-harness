"""Second-pass renderer: clarify the final three-branch convergence."""
from pathlib import Path


source_path = Path(__file__).with_name("render_dense_workflow.py")
source = source_path.read_text(encoding="utf-8")
source = source.replace(
    'F24 = font(24, bold=True)\nF28 = font(28, bold=True)',
    'F24 = font(24, bold=True)\nF26 = font(26, bold=True)\nF28 = font(28, bold=True)',
)
source = source.replace(
    'd.line((1415, 2095, 1415, 2145), fill=AMBER, width=3)\n'
    'stage(2130, "05", "提交、持久化与返回", "ConversationStore · audit", BLUE)',
    'd.line((1415, 2095, 1415, 2145), fill=AMBER, width=3)\n'
    'for cx, color in [(360, GRAY), (775, GREEN), (1415, AMBER)]:\n'
    '    arrow((cx, 2145), (cx, 2167), color, 3, 7)\n'
    'stage(2130, "05", "提交、持久化与返回", "ConversationStore · audit", BLUE)',
)
exec(compile(source, str(source_path), "exec"), {"__file__": str(source_path)})
