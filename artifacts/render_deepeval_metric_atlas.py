from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


W, H = 1800, 2300
OUT = Path(__file__).with_name("deepeval-metric-atlas.png")

BG = "#F5F8FC"
WHITE = "#FFFFFF"
NAVY = "#123B66"
TEXT = "#243746"
MUTED = "#718191"
LINE = "#D7E0E8"

BLUE = "#2A6FAE"
BLUE_BG = "#E9F2FA"
GREEN = "#2D8A54"
GREEN_BG = "#EAF5EB"
ORANGE = "#D56F0F"
ORANGE_BG = "#FFF1E2"
GRAY = "#71818F"
GRAY_BG = "#EFF3F6"

CN = r"C:\Windows\Fonts\msyh.ttc"
CN_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
MONO = r"C:\Users\admin\.agents\skills\canvas-design\canvas-fonts\GeistMono-Regular.ttf"


def font(size: int, bold: bool = False, mono: bool = False):
    return ImageFont.truetype(MONO if mono else (CN_BOLD if bold else CN), size=size)


F14M = font(14, mono=True)
F16M = font(16, mono=True)
F17 = font(17)
F18 = font(18)
F20 = font(20)
F21B = font(21, True)
F23B = font(23, True)
F25B = font(25, True)
F29B = font(29, True)
F34B = font(34, True)
F54B = font(54, True)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)


def rr(box, radius=18, fill=WHITE, outline=LINE, width=2):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def txt(xy, value, f=F20, fill=TEXT, anchor="la"):
    d.text(xy, value, font=f, fill=fill, anchor=anchor)


def line(points, fill=LINE, width=3):
    d.line(points, fill=fill, width=width, joint="curve")


def arrow(a, b, color=BLUE, width=4, head=11):
    x1, y1 = a
    x2, y2 = b
    d.line((x1, y1, x2, y2), fill=color, width=width)
    if abs(x2 - x1) >= abs(y2 - y1):
        s = 1 if x2 > x1 else -1
        pts = ((x2, y2), (x2 - s * head, y2 - 7), (x2 - s * head, y2 + 7))
    else:
        s = 1 if y2 > y1 else -1
        pts = ((x2, y2), (x2 - 7, y2 - s * head), (x2 + 7, y2 - s * head))
    d.polygon(pts, fill=color)


def pill(x, y, label, fill, fg=WHITE, font_obj=F16M, px=15, h=34):
    bounds = d.textbbox((0, 0), label, font=font_obj)
    w = bounds[2] - bounds[0] + px * 2
    rr((x, y, x + w, y + h), h // 2, fill, fill, 1)
    txt((x + w / 2, y + h / 2), label, font_obj, fg, "mm")
    return w


def stat_box(rect, number, label, color):
    x1, y1, x2, y2 = rect
    rr(rect, 18, WHITE, LINE, 2)
    txt((x1 + 24, (y1 + y2) / 2), number, F34B, color, "lm")
    txt((x1 + 102, (y1 + y2) / 2), label, F18, MUTED, "lm")


def section_header(y, num, title, subtitle, color):
    line((70, y, 1730, y), "#E1E8EE", 2)
    d.ellipse((70, y - 20, 110, y + 20), fill=color)
    txt((90, y), num, F16M, WHITE, "mm")
    txt((132, y - 2), title, F29B, color, "lm")
    txt((1728, y), subtitle, F16M, MUTED, "rm")


def panel(rect, title, subtitle, color, fill):
    x1, y1, x2, y2 = rect
    rr(rect, 24, WHITE, color, 3)
    rr((x1 + 18, y1 + 18, x2 - 18, y1 + 72), 15, fill, fill, 1)
    txt((x1 + 38, y1 + 45), title, F25B, color, "lm")
    txt((x2 - 38, y1 + 45), subtitle, F16M, MUTED, "rm")


def metric_card(rect, index, name, description, color, fill, tag=None, compact=False):
    x1, y1, x2, y2 = rect
    rr(rect, 17, fill, color, 2)
    d.ellipse((x1 + 18, y1 + 18, x1 + 54, y1 + 54), fill=color)
    txt((x1 + 36, y1 + 36), f"{index:02d}", F14M, WHITE, "mm")
    title_font = F21B if compact else F23B
    txt((x1 + 70, y1 + 27), name, title_font, color, "la")
    txt((x1 + 70, y1 + (59 if compact else 65)), description, F17 if compact else F18, TEXT, "la")
    if tag:
        pill(x1 + 18, y2 - 45, tag, color, WHITE, F14M, 12, 28)


# Header
txt((70, 62), "DEEPEVAL  /  METRIC ATLAS", F16M, MUTED, "la")
txt((1730, 62), "EVAL 01  ·  CORE METRICS", F16M, MUTED, "ra")
txt((900, 122), "DeepEval 核心指标地图", F54B, NAVY, "ma")
txt((900, 185), "从最终回答到 Agent、RAG、多轮对话与安全治理", F25B, TEXT, "ma")
txt((900, 224), "按测试对象组织 21 项常用指标 · 分数通常为 0–1 · 阈值决定是否通过", F18, MUTED, "ma")

# Summary stats
stats_y1, stats_y2 = 265, 350
stat_box((70, stats_y1, 445, stats_y2), "21", "项核心指标", BLUE)
stat_box((468, stats_y1, 843, stats_y2), "09", "类测试对象", GREEN)
stat_box((866, stats_y1, 1241, stats_y2), "03", "评估机制", ORANGE)
stat_box((1264, stats_y1, 1730, stats_y2), "0–1", "分数 + 评分理由", GRAY)

# Evaluation pipeline
rr((115, 390, 1685, 505), 24, WHITE, NAVY, 3)
txt((145, 414), "EVALUATION PATH", F14M, MUTED, "la")
pipeline = [
    (240, "INPUT", "问题 / 目标"),
    (565, "EVIDENCE", "Trace / Context"),
    (900, "METRIC", "Judge / Rule"),
    (1235, "SCORE", "0–1 / Reason"),
    (1560, "GATE", "PASS / FAIL"),
]
for i, (cx, label, sub) in enumerate(pipeline):
    fill = [BLUE_BG, GREEN_BG, ORANGE_BG, GRAY_BG, BLUE_BG][i]
    color = [BLUE, GREEN, ORANGE, GRAY, NAVY][i]
    rr((cx - 113, 430, cx + 113, 485), 16, fill, color, 2)
    txt((cx, 449), label, F16M, color, "mm")
    txt((cx, 471), sub, F17, TEXT, "mm")
    if i < len(pipeline) - 1:
        arrow((cx + 113, 458), (pipeline[i + 1][0] - 122, 458), NAVY, 3, 9)

# Section 01
section_header(555, "01", "结果质量与 Agent 执行", "OUTPUT  /  AGENTIC", BLUE)

panel((70, 600, 570, 1080), "最终回答", "OUTPUT", BLUE, BLUE_BG)
metric_card((92, 690, 548, 850), 1, "Answer Relevancy", "回答是否真正针对用户问题", BLUE, BLUE_BG, "LLM-JUDGE")
metric_card((92, 875, 548, 1055), 2, "G-Eval", "按自定义标准评估正确性、完整性与专业性", BLUE, BLUE_BG, "CUSTOM RUBRIC")

panel((600, 600, 1730, 1080), "Agent 执行", "AGENTIC", GREEN, GREEN_BG)
agent_cards = [
    (3, "Task Completion", "是否真正完成用户任务"),
    (4, "Tool Correctness", "是否调用正确工具"),
    (5, "Argument Correctness", "工具参数是否正确"),
    (6, "Step Efficiency", "是否存在重复或无效步骤"),
    (7, "Plan Quality", "计划是否合理、可执行"),
    (8, "Plan Adherence", "实际执行是否遵循计划"),
]
ax = [622, 987, 1352]
ay = [690, 870]
for idx, (num, name, desc) in enumerate(agent_cards):
    col, row = idx % 3, idx // 3
    metric_card((ax[col], ay[row], ax[col] + 343, ay[row] + 160), num, name, desc, GREEN, GREEN_BG, compact=True)

# Section 02
section_header(1135, "02", "检索事实与对话连续性", "RAG  /  CONVERSATION", GREEN)

panel((70, 1180, 1110, 1690), "RAG 检索与生成", "RETRIEVER → GENERATOR", GREEN, GREEN_BG)
rag_cards = [
    (9, "Contextual Relevancy", "召回内容是否与问题相关", "RETRIEVAL"),
    (10, "Contextual Precision", "相关内容是否排在前面", "RETRIEVAL"),
    (11, "Contextual Recall", "应召回的信息是否遗漏", "RETRIEVAL"),
    (12, "Faithfulness", "回答是否忠于检索上下文、有没有编造", "GENERATION"),
]
rx = [92, 603]
ry = [1270, 1470]
for idx, (num, name, desc, tag) in enumerate(rag_cards):
    col, row = idx % 2, idx // 2
    metric_card((rx[col], ry[row], rx[col] + 485, ry[row] + 175), num, name, desc, GREEN, GREEN_BG, tag)

panel((1140, 1180, 1730, 1690), "多轮对话", "MULTI-TURN", BLUE, BLUE_BG)
conversation_cards = [
    (13, "Knowledge Retention", "是否记得前面对话事实"),
    (14, "Role Adherence", "是否始终遵循角色与系统约束"),
    (15, "Conversation Completeness", "是否完整处理对话目标"),
]
cy = [1270, 1405, 1540]
for y, (num, name, desc) in zip(cy, conversation_cards):
    metric_card((1162, y, 1708, y + 115), num, name, desc, BLUE, BLUE_BG, compact=True)

# Section 03
section_header(1745, "03", "安全治理、结构与确定性检查", "SAFETY  /  RULES", ORANGE)

panel((70, 1790, 960, 2185), "安全治理", "SAFETY", ORANGE, ORANGE_BG)
safety_cards = [
    (16, "Bias / Toxicity", "偏见与有害内容"),
    (17, "PII Leakage", "是否泄露个人敏感信息"),
    (18, "Misuse / Role Violation", "是否发生越权、滥用或角色违规"),
]
sy = [1880, 1980, 2080]
for y, (num, name, desc) in zip(sy, safety_cards):
    metric_card((92, y, 938, y + 82), num, name, desc, ORANGE, ORANGE_BG, compact=True)

panel((990, 1790, 1730, 2185), "结构与确定性", "DETERMINISTIC", GRAY, GRAY_BG)
quality_cards = [
    (19, "JSON Correctness", "JSON 输出是否符合约定", "FORMAT"),
    (20, "Pattern Match", "正则、固定格式与关键词是否满足", "RULE"),
    (21, "Summarization", "摘要覆盖度与忠实度", "SUMMARY"),
]
qy = [1880, 1980, 2080]
for y, (num, name, desc, tag) in zip(qy, quality_cards):
    metric_card((1012, y, 1708, y + 82), num, name, desc, GRAY, GRAY_BG, compact=True)
    pill(1592, y + 27, tag, GRAY, WHITE, F14M, 11, 28)

# Footer
line((70, 2230, 1730, 2230), LINE, 2)
txt((70, 2262), "SOURCE  ·  DeepEval official metrics documentation", F14M, MUTED, "la")
txt((1730, 2262), "建议：每个测试套件选择 3–5 个最相关指标，并用人工标注集校准阈值", F17, NAVY, "ra")

img.save(OUT, optimize=True)
print(OUT)
