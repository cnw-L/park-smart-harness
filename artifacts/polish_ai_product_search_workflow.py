"""Final pass: preserve the flow and add the project's verified offline-evaluation strip."""
from pathlib import Path


source_path = Path(__file__).with_name("render_ai_product_search_workflow.py")
source = source_path.read_text(encoding="utf-8")
source = source.replace("W, H = 1800, 2530", "W, H = 1800, 2620")
source = source.replace(
    'rr((340, 2480, 1460, 2520), 20, NAVY, NAVY, 2)\n'
    'txt((900, 2500), "返回用户：Top5 候选 + 两款对比表 + 推荐理由 + 约束说明", F20, WHITE, "mm")',
    'rr((340, 2480, 1460, 2545), 20, NAVY, NAVY, 2)\n'
    'txt((900, 2512), "返回用户：Top5 候选 + 两款对比表 + 推荐理由 + 约束说明", F20, WHITE, "mm")\n\n'
    'rr((190, 2570, 1610, 2608), 19, GRAY_BG, LINE, 2)\n'
    'txt((900, 2589), "离线评测：3万+ SKU · 3000+ Query · Top5 78%→92% · 零结果 12%→5% · 长尾首屏无关结果 -30%", F17, NAVY, "mm")',
)
exec(compile(source, str(source_path), "exec"), {"__file__": str(source_path)})
