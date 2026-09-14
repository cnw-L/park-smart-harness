from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


W, H = 2000, 1320
OUT = Path(__file__).with_name("park-harness-control-trace.png")

BG = "#07131E"
PANEL = "#0C1C29"
PANEL_2 = "#102433"
GRID = "#173142"
TEXT = "#EAF4F6"
MUTED = "#7F9AA8"
CYAN = "#35C7D8"
CYAN_SOFT = "#123A49"
GREEN = "#63D49C"
GREEN_SOFT = "#12392F"
AMBER = "#FFB44A"
AMBER_SOFT = "#432D15"
RED = "#FF7369"
WHITE = "#FFFFFF"

CN_REG = r"C:\Windows\Fonts\msyh.ttc"
CN_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
MONO = r"C:\Users\admin\.agents\skills\canvas-design\canvas-fonts\GeistMono-Regular.ttf"


def font(size, bold=False, mono=False):
    return ImageFont.truetype(MONO if mono else (CN_BOLD if bold else CN_REG), size)


F12 = font(12, mono=True)
F14 = font(14, mono=True)
F16 = font(16)
F18 = font(18)
F20 = font(20, bold=True)
F22 = font(22, bold=True)
F26 = font(26, bold=True)
F34 = font(34, bold=True)
F48 = font(48, bold=True)
F74 = font(74, bold=True)


im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)


def rr(box, radius=18, fill=None, outline=None, width=2):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def txt(xy, s, f=F18, fill=TEXT, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def line(points, fill=GRID, width=2):
    d.line(points, fill=fill, width=width, joint="curve")


def arrow(a, b, fill=CYAN, width=4, head=10):
    d.line((*a, *b), fill=fill, width=width)
    x1, y1 = a
    x2, y2 = b
    if abs(x2 - x1) >= abs(y2 - y1):
        sign = 1 if x2 > x1 else -1
        pts = [(x2, y2), (x2 - sign * head, y2 - head * .65), (x2 - sign * head, y2 + head * .65)]
    else:
        sign = 1 if y2 > y1 else -1
        pts = [(x2, y2), (x2 - head * .65, y2 - sign * head), (x2 + head * .65, y2 - sign * head)]
    d.polygon(pts, fill=fill)


def dot(x, y, color, r=7, ring=False):
    if ring:
        d.ellipse((x-r-5, y-r-5, x+r+5, y+r+5), outline=color, width=2)
    d.ellipse((x-r, y-r, x+r, y+r), fill=color)


def pill(x, y, label, color, width=None):
    tw = d.textbbox((0, 0), label, font=F14)[2]
    pw = width or tw + 28
    rr((x, y, x + pw, y + 28), 14, fill=color)
    txt((x + pw / 2, y + 14), label, F14, BG, "mm")
    return pw


def step(x, y, number, title, subtitle, color=CYAN, align="center"):
    dot(x, y, color, 8, ring=True)
    txt((x, y - 48), number, F14, color, "mm")
    if align == "left":
        txt((x + 22, y - 5), title, F20, TEXT, "lm")
        txt((x + 22, y + 23), subtitle, F14, MUTED, "lm")
    else:
        txt((x, y + 38), title, F20, TEXT, "ma")
        txt((x, y + 66), subtitle, F14, MUTED, "ma")


# Fine operational grid
for x in range(80, W - 79, 40):
    line((x, 285, x, H - 110), GRID, 1)
for y in range(300, H - 109, 40):
    line((80, y, W - 80, y), GRID, 1)

# Header
txt((80, 58), "PARK / AGENT HARNESS", F14, CYAN, "la")
txt((1920, 58), "CONTROL TRACE  ·  7A2C-24", F14, MUTED, "ra")
txt((80, 104), "一次受控调温，", F74, TEXT, "la")
txt((80, 188), "如何安全发生", F74, CYAN, "la")
txt((1908, 135), "模型提出", F18, MUTED, "ra")
txt((1908, 166), "系统裁决", F18, MUTED, "ra")
txt((1908, 197), "人类授权", F18, AMBER, "ra")
txt((1908, 228), "后端证实", F18, GREEN, "ra")
line((80, 258, 1920, 258), CYAN, 2)

# Request card
rr((80, 300, 1920, 405), 22, PANEL, GRID, 2)
pill(106, 326, "USER REQUEST", CYAN)
txt((330, 351), "“先查南区 2 号楼空调机组；若高于 26℃，调到 24℃。”", F26, TEXT, "lm")
txt((1888, 351), "复合请求 / READ + CONTROL", F14, MUTED, "rm")

# Lane labels
lanes = [(500, "01 / THINK", "模型与上下文", CYAN), (735, "02 / TRUST", "权限与人工确认", AMBER), (970, "03 / REALITY", "权威后端与事实", GREEN)]
for y, code, name, color in lanes:
    txt((95, y - 20), code, F14, color, "la")
    txt((95, y + 12), name, F16, MUTED, "la")
    line((250, y, 1900, y), GRID, 2)

# Three gate columns as subtle zones
rr((350, 447, 570, 1047), 22, fill="#0A1823", outline=GRID, width=1)
rr((1040, 447, 1300, 1047), 22, fill="#211A13", outline=AMBER_SOFT, width=2)
rr((1560, 447, 1835, 1047), 22, fill="#0B211C", outline=GREEN_SOFT, width=2)
txt((460, 464), "GATE 01", F14, CYAN, "ma")
txt((1170, 464), "GATE 02", F14, AMBER, "ma")
txt((1698, 464), "GATE 03", F14, GREEN, "ma")

# Lane 1: intent to plan
arrow((275, 500), (370, 500), CYAN, 4)
step(275, 500, "00", "进入会话", "principal / history", CYAN)
step(460, 500, "01", "能力收缩", "employee · scoped", CYAN)
arrow((475, 500), (655, 500), CYAN, 4)
step(670, 500, "02", "组装上下文", "memory · plan · tools", CYAN)
arrow((685, 500), (855, 500), CYAN, 4)
step(870, 500, "03", "生成计划", "查状态 → 条件判断 → 提案", CYAN)

# Read-only branch descends to backend and returns fact
line((870, 518, 870, 970), CYAN, 3)
dot(870, 735, GREEN, 6)
pill(740, 690, "ALLOW / READ", GREEN)
step(870, 970, "04", "查询设备状态", "authoritative dictionary", GREEN)
arrow((885, 970), (1000, 970), GREEN, 4)
rr((1015, 918, 1275, 1022), 18, GREEN_SOFT, GREEN, 2)
txt((1040, 945), "FACT", F14, GREEN, "la")
txt((1040, 983), "当前温度 28℃", F26, WHITE, "la")
txt((1247, 987), "> 26℃", F14, GREEN, "ra")
line((1145, 918, 1145, 548), GREEN, 3)
arrow((1145, 548), (1030, 548), GREEN, 3)
txt((1128, 578), "条件成立", F14, GREEN, "ra")

# Proposal enters control air gap
step(1010, 500, "05", "冻结控制提案", "target=24℃ · no handle to model", CYAN)
arrow((1025, 500), (1080, 500), AMBER, 4)
txt((1170, 545), "CONTROL AIR GAP", F22, AMBER, "ma")
txt((1170, 578), "模型到此为止", F18, MUTED, "ma")
line((1080, 620, 1260, 620), AMBER, 2)
for x in range(1090, 1260, 22):
    line((x, 610, x + 12, 630), AMBER, 2)

# Trust lane: gate verdict and suspend
dot(1170, 735, AMBER, 11, ring=True)
txt((1170, 682), "ASK", F34, AMBER, "mm")
txt((1170, 772), "挂起 · 持久化 pending", F18, TEXT, "ma")
txt((1170, 802), "预算停止消耗 / 动作尚未执行", F14, MUTED, "ma")
arrow((1300, 735), (1400, 735), AMBER, 4)
rr((1415, 665, 1550, 805), 24, AMBER_SOFT, AMBER, 2)
txt((1482, 695), "06", F14, AMBER, "ma")
txt((1482, 733), "人工确认", F22, WHITE, "mm")
txt((1482, 770), "24℃", F26, AMBER, "mm")

# Resume drops into reality lane
arrow((1482, 805), (1482, 890), AMBER, 4)
pill(1365, 858, "RESUME", AMBER)
step(1482, 970, "07", "幂等执行", "frozen action · idem key", GREEN)
arrow((1497, 970), (1590, 970), GREEN, 4)

# Verification gate
dot(1698, 970, GREEN, 10, ring=True)
txt((1698, 916), "READBACK", F14, GREEN, "mm")
txt((1698, 1008), "effective = 24℃", F20, WHITE, "ma")
arrow((1713, 970), (1870, 970), GREEN, 4)
step(1870, 970, "08", "边界提交", "completed · audited", GREEN)

# Connect verified result upward to final response
line((1870, 950, 1870, 500), GREEN, 3)
arrow((1870, 500), (1810, 500), GREEN, 3)
rr((1580, 452, 1810, 548), 18, GREEN_SOFT, GREEN, 2)
txt((1605, 478), "FINAL", F14, GREEN, "la")
txt((1605, 516), "已调至 24℃", F22, WHITE, "la")

# Audit strip
rr((80, 1090, 1920, 1235), 24, PANEL_2, GRID, 2)
txt((108, 1120), "INVARIANTS", F14, CYAN, "la")
items = [
    ("模型", "只提出", CYAN),
    ("闸门", "先裁决", AMBER),
    ("人", "再授权", AMBER),
    ("后端", "才执行", GREEN),
    ("读回", "证实生效", GREEN),
]
x = 108
for i, (a, b, c) in enumerate(items):
    if i:
        txt((x - 28, 1181), "×", F22, MUTED, "mm")
    txt((x, 1167), a, F14, c, "la")
    txt((x, 1197), b, F20, TEXT, "la")
    x += 250 if i < 3 else 300
txt((1888, 1180), "ALLOW ≠ EXECUTE", F16, RED, "ra")
txt((1888, 1208), "TRACE / AUDIT / REPLAY", F14, MUTED, "ra")

# Footer
txt((80, 1270), "PARK-SMART-HARNESS  /  GOVERNED CONTROL PATH", F14, MUTED, "la")
txt((1920, 1270), "PROPOSE → SUSPEND → CONFIRM → EXECUTE → VERIFY", F14, CYAN, "ra")

im.save(OUT, quality=96, optimize=True)
print(OUT)
