from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1800, 2050
OUT = Path(__file__).with_name("park-smart-harness-workflow.png")

BG = "#F8FAFC"
NAVY = "#173B63"
BLUE = "#2C6598"
BLUE_FILL = "#E7F0F8"
GREEN = "#2F7D4A"
GREEN_FILL = "#E7F3E8"
ORANGE = "#C96A16"
ORANGE_FILL = "#FFF0DF"
GRAY = "#758293"
GRAY_FILL = "#F0F3F6"
INK = "#263443"
WHITE = "#FFFFFF"
LINE = "#D5DCE4"

FONT_CN = r"C:\Windows\Fonts\msyh.ttc"
FONT_CN_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_MONO = r"C:\Users\admin\.agents\skills\canvas-design\canvas-fonts\GeistMono-Regular.ttf"

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)


def font(size: int, bold: bool = False, mono: bool = False):
    path = FONT_MONO if mono else (FONT_CN_BOLD if bold else FONT_CN)
    return ImageFont.truetype(path, size=size)


def rounded(box, fill, outline, radius=18, width=2):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_center(box, title, subtitle="", *, color=INK, accent=NAVY,
                title_size=26, sub_size=17, gap=10):
    x1, y1, x2, y2 = box
    ft = font(title_size, bold=True)
    fs = font(sub_size)
    tb = d.multiline_textbbox((0, 0), title, font=ft, spacing=5, align="center")
    th = tb[3] - tb[1]
    sb = d.multiline_textbbox((0, 0), subtitle, font=fs, spacing=5, align="center") if subtitle else (0, 0, 0, 0)
    sh = sb[3] - sb[1]
    total = th + (gap + sh if subtitle else 0)
    y = y1 + (y2 - y1 - total) / 2
    d.multiline_text(((x1 + x2) / 2, y), title, font=ft, fill=accent,
                     anchor="ma", align="center", spacing=5)
    if subtitle:
        d.multiline_text(((x1 + x2) / 2, y + th + gap), subtitle, font=fs,
                         fill=color, anchor="ma", align="center", spacing=5)


def arrow(x1, y1, x2, y2, color=BLUE, width=3, head=10):
    d.line((x1, y1, x2, y2), fill=color, width=width)
    if abs(x2 - x1) > abs(y2 - y1):
        s = 1 if x2 > x1 else -1
        pts = [(x2, y2), (x2 - s * head, y2 - head * 0.65), (x2 - s * head, y2 + head * 0.65)]
    else:
        s = 1 if y2 > y1 else -1
        pts = [(x2, y2), (x2 - head * 0.65, y2 - s * head), (x2 + head * 0.65, y2 - s * head)]
    d.polygon(pts, fill=color)


def label_pill(x, y, text, fill, color):
    f = font(15, bold=True)
    b = d.textbbox((0, 0), text, font=f)
    w = b[2] - b[0] + 24
    h = 30
    rounded((x, y, x + w, y + h), fill, color, radius=15, width=1)
    d.text((x + w / 2, y + h / 2 - 1), text, font=f, fill=color, anchor="mm")


# Header
d.text((W / 2, 62), "园区智能体 Harness · 端到端调用链路", font=font(45, bold=True),
       fill=NAVY, anchor="ma")
d.text((W / 2, 128), "示例：查询南区空调状态，并将目标设备调至 24℃",
       font=font(24, bold=True), fill=INK, anchor="ma")
d.text((W / 2, 169), "身份鉴权 · 动态上下文 · 工具治理 · 人工确认 · 事务恢复",
       font=font(17), fill=GRAY, anchor="ma")

# User entry
user = (520, 215, 1280, 292)
rounded(user, BLUE_FILL, BLUE, radius=18, width=2)
text_center(user, "用户 / 园区应用", "已登录 · 携带会话 ID 与短期令牌", accent=NAVY, title_size=27)
arrow(900, 292, 900, 333)

# Input + identity
inp = (270, 345, 865, 470)
ident = (935, 345, 1530, 470)
rounded(inp, ORANGE_FILL, ORANGE, radius=19, width=2)
rounded(ident, BLUE_FILL, BLUE, radius=19, width=2)
text_center(inp, "① 入站与模态门", "落库用户消息 · pending 时仅接受确认 / 取消\n中断信号与消息序列修复", accent=ORANGE)
text_center(ident, "身份脊柱与能力快照", "Principal · tenant / user / token\nToolLoader 按 capability_code 收缩工具集", accent=NAVY)
arrow(900, 470, 900, 512)

# Context
ctx = (180, 525, 1620, 655)
rounded(ctx, GREEN_FILL, GREEN, radius=20, width=2)
text_center(ctx, "② 动态上下文装配", "系统规则 + 当前用户 + 长期记忆（可选） + 精简历史 + 当前计划\n知识结果标注为证据；控制结果不等于现状；超阈触发摘要压缩", accent=GREEN, title_size=29, sub_size=18)
arrow(900, 655, 900, 695, color=GREEN)

# Model loop
loop = (265, 708, 1535, 818)
rounded(loop, WHITE, GREEN, radius=20, width=3)
text_center(loop, "③ 事务内圈：ASSEMBLE → MODEL → GATE → ACT → VERIFY → COMMIT",
            "OpenAI-compatible Qwen · 工具调用重试 · token / iteration 预算 · stall / thrashing 看门狗",
            accent=GREEN, title_size=25, sub_size=17)
arrow(900, 818, 900, 865)

# Plan / gate band
plan = (315, 875, 1485, 975)
rounded(plan, GREEN_FILL, GREEN, radius=18, width=2)
text_center(plan, "模型生成文本或工具批次", "plan 仅是全量意图快照，不是完成权威；无工具且有正文才完成",
            accent=GREEN, title_size=25, sub_size=17)
arrow(900, 975, 900, 1018)

# Tool cards
cards = [
    ((80, 1040, 420, 1160), "设备管理 Agent", "device_status\npropose_control", GREEN, GREEN_FILL),
    ((510, 1040, 850, 1160), "运行事项查询", "工单 · 告警 · 事件\n设备健康 / 能耗", GREEN, GREEN_FILL),
    ((940, 1040, 1280, 1160), "生活服务", "会议室 · 停车\n餐厅查询", BLUE, BLUE_FILL),
    ((1370, 1040, 1710, 1160), "知识检索", "Milvus + Embedding\nReranker · 二次检索", BLUE, BLUE_FILL),
]
for box, title, sub, stroke, fillc in cards:
    rounded(box, fillc, stroke, radius=18, width=2)
    text_center(box, title, sub, accent=stroke, title_size=22, sub_size=16, gap=8)
    arrow((box[0]+box[2])/2, box[3], (box[0]+box[2])/2, 1200, color=stroke, width=2)

# Gate rail and outcomes
d.line((250, 1200, 1550, 1200), fill=LINE, width=3)
gate = (545, 1220, 1255, 1305)
rounded(gate, WHITE, NAVY, radius=18, width=3)
text_center(gate, "CatalogGate · deny-first", "未注册 / 无权限 → DENY ｜ 只读 → ALLOW ｜ 控制 → ASK",
            accent=NAVY, title_size=24, sub_size=16)

# Three branches
deny = (70, 1350, 470, 1480)
allow = (520, 1350, 1000, 1480)
ask = (1050, 1350, 1730, 1480)
rounded(deny, GRAY_FILL, GRAY, radius=18, width=2)
rounded(allow, GREEN_FILL, GREEN, radius=18, width=2)
rounded(ask, ORANGE_FILL, ORANGE, radius=18, width=2)
text_center(deny, "DENY · 安全阻断", "合成 [blocked] 结果\n模型可见并重新规划", accent=GRAY, title_size=23, sub_size=17)
text_center(allow, "ALLOW · 并发执行", "只读工具 asyncio.gather\n超时 / 重试 / 输出预算 / 结果校验", accent=GREEN, title_size=23, sub_size=17)
text_center(ask, "ASK · 控制确认红线", "从服务端提案冻结精确动作\n提交 pending Boundary → 返回确认卡", accent=ORANGE, title_size=23, sub_size=17)
arrow(755, 1305, 270, 1348, color=GRAY, width=2)
arrow(900, 1305, 760, 1348, color=GREEN, width=2)
arrow(1045, 1305, 1390, 1348, color=ORANGE, width=2)

# Control confirmation mini flow
confirm = (1120, 1518, 1660, 1628)
rounded(confirm, WHITE, ORANGE, radius=17, width=2)
text_center(confirm, "人工确认：APPROVE / REJECT", "批准后才 deviceCtrl / doorControl；拒绝则清提案",
            accent=ORANGE, title_size=22, sub_size=15)
arrow(1390, 1480, 1390, 1516, color=ORANGE, width=2)

readback = (1120, 1660, 1660, 1775)
rounded(readback, ORANGE_FILL, ORANGE, radius=17, width=2)
text_center(readback, "幂等账本 + 状态读回", "in_flight → done / failed\naccepted ≠ effective · 不确定时不盲目重发",
            accent=ORANGE, title_size=22, sub_size=15)
arrow(1390, 1628, 1390, 1658, color=ORANGE, width=2)

# Read-only backend boxes
backend = (120, 1525, 980, 1628)
rounded(backend, WHITE, GREEN, radius=17, width=2)
text_center(backend, "权威数据源", "园区 prod-api（设备 / 工单 / 告警） · 生活服务 · Milvus 知识库",
            accent=GREEN, title_size=22, sub_size=16)
arrow(760, 1480, 760, 1523, color=GREEN, width=2)

# Convergence
conv = (300, 1810, 1500, 1908)
rounded(conv, BLUE_FILL, BLUE, radius=19, width=2)
text_center(conv, "④ 结构化结果汇流 → 提交事务边界 → 继续循环或生成最终回答",
            "ConversationStore：InMemory / Redis ｜ PostgreSQL：幂等与审计 ｜ RAG / 记忆优雅降级",
            accent=NAVY, title_size=25, sub_size=16)
arrow(550, 1628, 550, 1808, color=GREEN, width=2)
arrow(1390, 1775, 1390, 1808, color=ORANGE, width=2)
arrow(270, 1480, 270, 1855, color=GRAY, width=2)

# Final return + footer sidecaps
final = (520, 1940, 1280, 2010)
rounded(final, BLUE_FILL, BLUE, radius=18, width=2)
text_center(final, "⑤ 返回用户：最终结论 / 确认卡 / 明确失败原因", accent=NAVY, title_size=23)
arrow(900, 1908, 900, 1938)

# small labels and legend
label_pill(90, 1970, "运行控制：中断 · 预算 · 压缩", GRAY_FILL, GRAY)
label_pill(1375, 1970, "观测：trace · 延迟 · token", GRAY_FILL, GRAY)

# top corner system tag
d.text((90, 78), "PARK / SMART / HARNESS", font=font(14, mono=True), fill=GRAY)
d.text((1710, 78), "FLOW 01", font=font(14, mono=True), fill=GRAY, anchor="ra")

img.save(OUT, quality=96)
print(OUT)
