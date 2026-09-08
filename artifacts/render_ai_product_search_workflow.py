from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


W, H = 1800, 2530
OUT = Path(__file__).with_name("ai-product-search-workflow.png")

BG = "#F5F8FC"
WHITE = "#FFFFFF"
NAVY = "#123B66"
TEXT = "#243746"
MUTED = "#6F7F8E"
LINE = "#CBD6DF"
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


F15 = font(15, mono=True)
F17 = font(17)
F18 = font(18)
F20 = font(20)
F22 = font(22)
F24 = font(24, True)
F27 = font(27, True)
F30 = font(30, True)
F50 = font(50, True)


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)


def rr(box, radius=18, fill=WHITE, outline=LINE, width=3):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def txt(xy, value, f=F20, fill=TEXT, anchor="la"):
    d.text(xy, value, font=f, fill=fill, anchor=anchor)


def arrow(a, b, color=BLUE, width=4, head=10):
    x1, y1 = a
    x2, y2 = b
    d.line((x1, y1, x2, y2), fill=color, width=width)
    if abs(x2 - x1) > abs(y2 - y1):
        s = 1 if x2 > x1 else -1
        pts = ((x2, y2), (x2 - s * head, y2 - 7), (x2 - s * head, y2 + 7))
    else:
        s = 1 if y2 > y1 else -1
        pts = ((x2, y2), (x2 - 7, y2 - s * head), (x2 + 7, y2 - s * head))
    d.polygon(pts, fill=color)


def pill(x, y, label, fill, fg=WHITE, width=None):
    tw = d.textbbox((0, 0), label, font=F17)[2]
    w = width or tw + 28
    rr((x, y, x + w, y + 34), 17, fill, fill, 1)
    txt((x + w / 2, y + 17), label, F17, fg, "mm")
    return w


def box(rect, title, lines, color=BLUE, fill=WHITE, title_font=F24, body_font=F18):
    x1, y1, x2, y2 = rect
    rr(rect, 20, fill, color, 3)
    txt(((x1 + x2) / 2, y1 + 36), title, title_font, color, "mm")
    start = y1 + 69
    for i, line in enumerate(lines):
        txt(((x1 + x2) / 2, start + i * 29), line, body_font, TEXT if i == 0 else MUTED, "ma")


def stage(y, number, label, package, color):
    d.line((62, y, 1738, y), fill="#E2E8ED", width=2)
    d.ellipse((60, y - 18, 96, y + 18), fill=color)
    txt((78, y), number, F17, WHITE, "mm")
    txt((114, y), label, F18, color, "lm")
    txt((1735, y), package, F15, MUTED, "rm")


# Header
txt((65, 60), "AI  /  COMMERCE  /  SEARCH", F15, MUTED, "la")
txt((1735, 60), "FLOW 01  ·  AGENT SEARCH", F15, MUTED, "ra")
txt((900, 115), "AI 商品搜索 Agent · 端到端检索与导购链路", F50, NAVY, "ma")
txt((900, 173), "示例：找一款 3000 元内、适合拍 Vlog、今天有货的轻便相机，对比两款并说明推荐理由", F27, TEXT, "ma")
txt((900, 214), "自然语言理解 · 商品知识结构化 · 混合召回 · 硬约束优先 · 多特征重排 · 可解释推荐", F20, MUTED, "ma")

# User request
rr((380, 255, 1420, 340), 20, BLUE_BG, BLUE, 3)
txt((900, 286), "用户 / 电商导购入口", F27, NAVY, "mm")
txt((900, 319), "自然语言请求 · 会话上下文 · 用户偏好（可选）", F18, MUTED, "mm")
arrow((900, 340), (900, 375), BLUE)

# Query understanding
stage(400, "01", "请求理解", "Search Agent", BLUE)
box((120, 440, 830, 570), "请求预处理", ["文本清洗 · 会话指代消解 · Query 分类", "识别搜索 / 筛选 / 对比 / FAQ / 相似推荐"], BLUE, BLUE_BG)
box((970, 440, 1680, 570), "意图识别与槽位抽取", ["品类=相机 · 价格≤3000 · 场景=Vlog", "便携=是 · 库存=今天有货 · 输出=两款对比"], BLUE, BLUE_BG)
d.line((475, 570, 475, 600, 900, 600), fill=BLUE, width=3)
d.line((1325, 570, 1325, 600, 900, 600), fill=BLUE, width=3)
arrow((900, 600), (900, 635), BLUE)

box((260, 650, 1540, 755), "② 条件完备性 Gate", ["检查必填槽位、硬约束冲突与可检索性；区分缺失条件、有效请求和异常表达"], ORANGE, WHITE, F27)

# Completeness outcomes
d.line((900, 755, 900, 790), fill=ORANGE, width=3)
d.line((290, 790, 1510, 790), fill=ORANGE, width=3)
for cx, c in [(290, ORANGE), (900, GREEN), (1510, GRAY)]:
    arrow((cx, 790), (cx, 830), c, 3)

box((80, 845, 500, 970), "MISSING · 缺失澄清", ["生成最小澄清问题", "用户补充后重新解析槽位"], ORANGE, ORANGE_BG)
box((550, 845, 1250, 970), "READY · 进入检索", ["冻结结构化 SearchSpec", "硬约束与软偏好分离，进入召回链路"], GREEN, GREEN_BG)
box((1300, 845, 1720, 970), "FALLBACK · 安全降级", ["保留关键词检索", "放宽软约束但不突破价格 / 库存"], GRAY, GRAY_BG)

# Clarification loop back to user
d.line((80, 905, 45, 905, 45, 298, 378, 298), fill=ORANGE, width=3)
arrow((45, 298), (378, 298), ORANGE, 3, 9)
pill(65, 860, "CLARIFY", ORANGE)

# Ready/fallback rejoin
d.line((900, 970, 900, 1005), fill=GREEN, width=4)
d.line((1510, 970, 1510, 1005, 900, 1005), fill=GRAY, width=3)
arrow((900, 1005), (900, 1035), GREEN, 4)

# Product knowledge
stage(1060, "02", "商品知识底座", "Product Schema · Index", GREEN)
box((135, 1100, 1665, 1235), "商品知识结构化", [
    "标题 · 类目 · 品牌 · 规格参数 · 价格 · 库存 · 卖点 · 评价摘要",
    "字段标准化、同义词归一与属性映射，为语义召回、条件过滤和商品对比提供统一数据基础",
], GREEN, GREEN_BG, F27)
arrow((900, 1235), (900, 1275), GREEN)

# Query engineering
stage(1300, "03", "检索增强", "Query Pipeline", BLUE)
box((250, 1340, 1550, 1445), "Query Rewrite → 同义词扩展 → 子查询拆解", [
    "“拍 Vlog”扩展为防抖 / 翻转屏 / 收音 / 轻便；将品类、场景、价格、库存拆成可执行检索计划",
], BLUE, WHITE, F27)
arrow((900, 1445), (900, 1480), BLUE)

# Hybrid recall
recalls = [
    ((70, 1500, 430, 1625), "关键词召回", ["BM25 / 倒排索引", "标题 · 类目 · 品牌"]),
    ((505, 1500, 865, 1625), "语义召回", ["Embedding / ANN", "场景与长尾表达"]),
    ((940, 1500, 1300, 1625), "结构化过滤", ["价格区间 · 库存", "品牌 · 规格参数"]),
    ((1375, 1500, 1735, 1625), "相似商品召回", ["类目邻域 / 同款", "补充候选与替代款"]),
]
for rect, title, lines in recalls:
    box(rect, title, lines, GREEN, GREEN_BG)
    cx = (rect[0] + rect[2]) / 2
    arrow((cx, rect[3]), (cx, 1665), GREEN, 3, 9)
d.line((250, 1665, 1555, 1665), fill=LINE, width=3)
arrow((900, 1665), (900, 1695), GREEN, 4)

box((420, 1710, 1380, 1795), "候选池融合与去重", ["多路召回归一化 · SKU 去重 · 召回来源与分数保留"], GREEN, WHITE, F27)
arrow((900, 1795), (900, 1830), GREEN)

# Constraint gate and rerank
box((250, 1845, 1550, 1950), "④ 硬约束优先过滤", [
    "先校验类目、价格区间和库存状态；硬约束不满足的候选不得进入推荐结果",
], ORANGE, ORANGE_BG, F27)
arrow((900, 1950), (900, 1985), ORANGE)

box((180, 2000, 1620, 2115), "多特征融合重排", [
    "约束满足度 + 标题/属性匹配 + 价格区间 + 库存 + 卖点 + 评价摘要 + 语义相关性",
    "优先保留硬约束完全满足的候选，再对软偏好与推荐价值进行综合排序",
], GREEN, GREEN_BG, F27)
arrow((900, 2115), (900, 2150), GREEN)

# Agent tools
stage(2170, "05", "工具组合", "Agent Tools", BLUE)
tools = [
    (65, "商品搜索", "search"),
    (355, "价格筛选", "price_filter"),
    (645, "库存查询", "stock_query"),
    (935, "商品对比", "compare"),
    (1225, "售后 FAQ", "faq"),
    (1515, "相似推荐", "similar"),
]
for x, title, sub in tools:
    rr((x, 2210, x + 220, 2310), 17, BLUE_BG, BLUE, 3)
    txt((x + 110, 2244), title, F22, NAVY, "mm")
    txt((x + 110, 2280), sub, F17, MUTED, "mm")

# Quality gate / retry
arrow((900, 2310), (900, 2340), BLUE)
rr((350, 2355, 1450, 2440), 20, WHITE, ORANGE, 3)
txt((900, 2384), "⑥ 答案质检 Gate", F27, ORANGE, "mm")
txt((900, 2417), "事实来自商品字段 · 硬约束无违背 · 对比口径一致 · 推荐理由可解释", F18, TEXT, "mm")

# Retry loop stays outside main flow
d.line((350, 2398, 60, 2398, 60, 1392, 248, 1392), fill=ORANGE, width=3)
arrow((60, 1392), (248, 1392), ORANGE, 3, 9)
pill(78, 2320, "LOW CONFIDENCE · REWRITE", ORANGE)

# Final answer
arrow((900, 2440), (900, 2470), GREEN)
rr((340, 2480, 1460, 2520), 20, NAVY, NAVY, 2)
txt((900, 2500), "返回用户：Top5 候选 + 两款对比表 + 推荐理由 + 约束说明", F20, WHITE, "mm")

img.save(OUT, optimize=True)
print(OUT)
