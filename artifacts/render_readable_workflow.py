from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


W, H = 1800, 1050
OUT = Path(__file__).with_name("park-harness-readable-workflow.png")

BG = "#F7F9FC"
WHITE = "#FFFFFF"
NAVY = "#18324A"
TEXT = "#263746"
MUTED = "#708392"
LINE = "#C9D4DD"
BLUE = "#3278B5"
BLUE_BG = "#EAF3FB"
GREEN = "#2E8B64"
GREEN_BG = "#EAF6F0"
AMBER = "#D77916"
AMBER_BG = "#FFF2E3"
GRAY_BG = "#EEF2F5"
RED = "#B75046"

CN = r"C:\Windows\Fonts\msyh.ttc"
CN_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
MONO = r"C:\Users\admin\.agents\skills\canvas-design\canvas-fonts\GeistMono-Regular.ttf"


def font(size, bold=False, mono=False):
    return ImageFont.truetype(MONO if mono else (CN_BOLD if bold else CN), size)


F14 = font(14, mono=True)
F16 = font(16)
F18 = font(18)
F20 = font(20)
F22 = font(22, bold=True)
F26 = font(26, bold=True)
F34 = font(34, bold=True)
F50 = font(50, bold=True)


im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)


def rr(box, radius=18, fill=WHITE, outline=LINE, width=2):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(xy, value, f=F18, fill=TEXT, anchor="la"):
    d.text(xy, value, font=f, fill=fill, anchor=anchor)


def arrow(x1, y, x2, color=LINE, width=4):
    d.line((x1, y, x2 - 12, y), fill=color, width=width)
    d.polygon(((x2, y), (x2 - 14, y - 8), (x2 - 14, y + 8)), fill=color)


def pill(x, y, label, fill, fg=WHITE, w=None):
    tw = d.textbbox((0, 0), label, font=F16)[2]
    width = w or tw + 28
    rr((x, y, x + width, y + 34), 17, fill, fill, 1)
    text((x + width / 2, y + 17), label, F16, fg, "mm")
    return width


def icon_query(cx, cy, color):
    d.ellipse((cx - 18, cy - 18, cx + 10, cy + 10), outline=color, width=4)
    d.line((cx + 6, cy + 7, cx + 22, cy + 23), fill=color, width=4)


def icon_plan(cx, cy, color):
    for yy in (-15, 0, 15):
        d.ellipse((cx - 22, cy + yy - 3, cx - 16, cy + yy + 3), fill=color)
        d.line((cx - 8, cy + yy, cx + 22, cy + yy), fill=color, width=3)


def icon_user(cx, cy, color):
    d.ellipse((cx - 10, cy - 22, cx + 10, cy - 2), outline=color, width=4)
    d.arc((cx - 23, cy - 2, cx + 23, cy + 34), 190, 350, fill=color, width=4)


def icon_check(cx, cy, color):
    d.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), outline=color, width=4)
    d.line((cx - 12, cy, cx - 2, cy + 10, cx + 15, cy - 12), fill=color, width=4, joint="curve")


def icon_execute(cx, cy, color):
    d.line((cx - 22, cy, cx + 16, cy), fill=color, width=4)
    d.polygon(((cx + 24, cy), (cx + 10, cy - 10), (cx + 10, cy + 10)), fill=color)
    d.line((cx - 18, cy + 18, cx + 18, cy + 18), fill=color, width=3)


def icon_reply(cx, cy, color):
    rr((cx - 26, cy - 20, cx + 26, cy + 16), 8, WHITE, color, 3)
    d.polygon(((cx - 12, cy + 14), (cx - 18, cy + 27), (cx, cy + 15)), fill=color)


def step_card(x, number, title, lines, color, fill, icon_fn):
    y1, y2, w = 370, 620, 235
    rr((x, y1, x + w, y2), 24, WHITE, color, 3)
    d.ellipse((x + 20, y1 + 20, x + 62, y1 + 62), fill=color)
    text((x + 41, y1 + 41), number, F20, WHITE, "mm")
    icon_fn(x + w / 2, y1 + 93, color)
    text((x + w / 2, y1 + 140), title, F26, NAVY, "ma")
    for i, line in enumerate(lines):
        text((x + w / 2, y1 + 184 + i * 29), line, F18, MUTED, "ma")
    return (x, y1, x + w, y2)


# Header
text((80, 62), "PARK SMART HARNESS", F14, BLUE, "la")
text((1720, 62), "受控设备操作 · 端到端实例", F16, MUTED, "ra")
text((80, 112), "从一句话，到一次可信控制", F50, NAVY, "la")
text((80, 180), "模型负责理解和提案；系统负责权限、确认、执行与验证。", F22, MUTED, "la")

rr((80, 235, 1720, 315), 20, WHITE, LINE, 2)
pill(105, 258, "用户请求", BLUE, WHITE, 100)
text((235, 275), "先查南区 2 号楼空调机组；若高于 26℃，调到 24℃。", F22, TEXT, "lm")
text((1690, 275), "READ → DECIDE → CONTROL", F14, MUTED, "rm")

# Main six-step path
xs = [80, 365, 650, 935, 1220, 1505]
cards = [
    step_card(xs[0], "1", "理解请求", ["识别目标与条件", "装配身份、历史、工具"], BLUE, BLUE_BG, icon_plan),
    step_card(xs[1], "2", "查询现状", ["只读工具自动放行", "权威后端返回 28℃"], GREEN, GREEN_BG, icon_query),
    step_card(xs[2], "3", "生成提案", ["目标温度冻结为 24℃", "模型不能直接执行"], BLUE, BLUE_BG, icon_plan),
    step_card(xs[3], "4", "人工确认", ["系统挂起并展示卡片", "确认前没有设备动作"], AMBER, AMBER_BG, icon_user),
    step_card(xs[4], "5", "执行并读回", ["幂等下发控制命令", "再次查询确认 24℃"], GREEN, GREEN_BG, icon_execute),
    step_card(xs[5], "6", "回答与审计", ["只陈述已验证结果", "保存边界、轨迹与结果"], GREEN, GREEN_BG, icon_reply),
]

for i in range(5):
    color = AMBER if i == 2 else (GREEN if i in (0, 3, 4) else BLUE)
    arrow(cards[i][2] + 10, 495, cards[i + 1][0] - 10, color, 4)

# Connector verdicts: short and legible
pill(284, 333, "ALLOW", GREEN, WHITE, 72)
pill(854, 333, "ASK · 挂起", AMBER, WHITE, 112)
pill(1414, 333, "VERIFY", GREEN, WHITE, 82)

# Safety refusal branch
d.line((197, 620, 197, 688), fill=LINE, width=3)
d.polygon(((197, 700), (189, 686), (205, 686)), fill=LINE)
rr((80, 715, 600, 790), 18, GRAY_BG, LINE, 2)
text((105, 740), "异常出口", F16, RED, "la")
text((205, 740), "无权限 / 目标不存在 / 参数不合法", F18, TEXT, "la")
text((105, 770), "→ 安全拒绝或请求澄清，不进入控制链路", F16, MUTED, "la")

# Core invariant strip
rr((650, 690, 1720, 835), 24, NAVY, NAVY, 1)
text((680, 720), "这条链路为什么可信", F20, WHITE, "la")
facts = [
    ("模型不执行", "只生成提案"),
    ("人确认", "动作才恢复"),
    ("幂等下发", "避免重复控制"),
    ("读回验证", "区分已接受与已生效"),
]
for i, (head, body) in enumerate(facts):
    x = 680 + i * 255
    if i:
        d.line((x - 25, 750, x - 25, 812), fill="#36516A", width=2)
    text((x, 772), head, F22, WHITE, "la")
    text((x, 806), body, F16, "#B8C8D4", "la")

# Legend and footer
text((80, 892), "颜色语义", F16, MUTED, "la")
for x, c, label in [(180, BLUE, "理解 / 编排"), (355, GREEN, "事实 / 验证"), (530, AMBER, "确认 / 控制边界")]:
    d.ellipse((x, 891, x + 14, 905), fill=c)
    text((x + 24, 899), label, F16, TEXT, "lm")
d.line((80, 940, 1720, 940), fill=LINE, width=2)
text((80, 974), "核心链路", F14, MUTED, "la")
text((185, 974), "请求 → 查询 → 提案 → 确认 → 执行 → 验证 → 返回", F18, NAVY, "la")
text((1720, 974), "PROPOSE ≠ EXECUTE", F14, BLUE, "ra")

im.save(OUT, optimize=True)
print(OUT)
