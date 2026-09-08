"""Faithful visual refinement of the existing park-smart-harness workflow renderer."""
from pathlib import Path


source_path = Path(__file__).with_name("render_harness_workflow.py")
source = source_path.read_text(encoding="utf-8")

replacements = {
    'OUT = Path(__file__).with_name("park-smart-harness-workflow.png")':
        'OUT = Path(__file__).with_name("park-smart-harness-workflow-optimized.png")',
    'BG = "#F8FAFC"': 'BG = "#F5F8FC"',
    'NAVY = "#173B63"': 'NAVY = "#123B66"',
    'BLUE = "#2C6598"': 'BLUE = "#2A6FAE"',
    'BLUE_FILL = "#E7F0F8"': 'BLUE_FILL = "#E9F2FA"',
    'GREEN = "#2F7D4A"': 'GREEN = "#2D8A54"',
    'GREEN_FILL = "#E7F3E8"': 'GREEN_FILL = "#EAF5EB"',
    'ORANGE = "#C96A16"': 'ORANGE = "#D56F0F"',
    'ORANGE_FILL = "#FFF0DF"': 'ORANGE_FILL = "#FFF1E2"',
    'GRAY = "#758293"': 'GRAY = "#6F7F8E"',
    'GRAY_FILL = "#F0F3F6"': 'GRAY_FILL = "#EFF3F6"',
    'INK = "#263443"': 'INK = "#243746"',
    'LINE = "#D5DCE4"': 'LINE = "#CBD6DF"',
    'fs = font(sub_size)': 'fs = font(sub_size + 1)',
    'width=width)': 'width=max(width, 3))',
    'fill=color, width=width)': 'fill=color, width=max(width, 3))',
    'f = font(15, bold=True)': 'f = font(16, bold=True)',
    'h = 30': 'h = 34',
    'font=font(45, bold=True)': 'font=font(48, bold=True)',
    'font=font(24, bold=True)': 'font=font(26, bold=True)',
    'img.save(OUT, quality=96)': 'img.save(OUT, quality=96, optimize=True)',
}
for old, new in replacements.items():
    source = source.replace(old, new)

source = source.replace(
    'd.line((250, 1200, 1550, 1200), fill=LINE, width=3)\n'
    'gate = (545, 1220, 1255, 1305)',
    'd.line((250, 1200, 1550, 1200), fill=LINE, width=3)\n'
    'arrow(900, 1200, 900, 1218, color=NAVY, width=3, head=8)\n'
    'gate = (545, 1220, 1255, 1305)',
)
source = source.replace(
    'arrow(270, 1480, 270, 1855, color=GRAY, width=2)',
    'd.line((270, 1480, 270, 1855), fill=GRAY, width=3)\n'
    'arrow(270, 1855, 298, 1855, color=GRAY, width=3, head=8)',
)

exec(compile(source, str(source_path), "exec"), {"__file__": str(source_path)})
