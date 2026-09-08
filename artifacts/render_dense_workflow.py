from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


W, H = 1800, 2320
OUT = Path(__file__).with_name("park-harness-dense-workflow.png")

BG = "#F6F8FB"
WHITE = "#FFFFFF"
NAVY = "#173B60"
TEXT = "#263B4C"
MUTED = "#708391"
LINE = "#CAD4DD"
BLUE = "#2D6FA9"
BLUE_BG = "#E8F1F8"
GREEN = "#2F8A55"
GREEN_BG = "#E8F4EA"
AMBER = "#D97915"
AMBER_BG = "#FFF0DF"
GRAY = "#7D8C99"
GRAY_BG = "#EEF2F5"
RED = "#B8554D"

CN = r"C:\Windows\Fonts\msyh.ttc"
CN_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
MONO = r"C:\Users\admin\.agents\skills\canvas-design\canvas-fonts\GeistMono-Regular.ttf"


def font(size, bold=False, mono=False):
    return ImageFont.truetype(MONO if mono else (CN_BOLD if bold else CN), size)


F15 = font(15, mono=True)
F17 = font(17)
F18 = font(18)
F20 = font(20)
F22 = font(22)
F24 = font(24, bold=True)
F28 = font(28, bold=True)
F32 = font(32, bold=True)
F54 = font(54, bold=True)


im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)


def rr(box, radius=18, fill=WHITE, outline=LINE, width=2):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def txt(xy, value, f=F20, fill=TEXT, anchor="la"):
    d.text(xy, value, font=f, fill=fill, anchor=anchor)


def arrow(a, b, color=BLUE, width=4, head=11):
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


def stage(y, number, label, package, color):
    d.line((60, y, 1740, y), fill="#E3E8ED", width=2)
    d.ellipse((58, y - 18, 94, y + 18), fill=color)
    txt((76, y), number, F17, WHITE, "mm")
    txt((112, y), label, F18, color, "lm")
    txt((1738, y), package, F15, MUTED, "rm")


def box(box, title, lines, color=BLUE, fill=WHITE, tag=None, title_size=F24):
    x1, y1, x2, y2 = box
    rr(box, 20, fill, color, 2)
    txt(((x1 + x2) / 2, y1 + 34), title, title_size, color, "mm")
    start = y1 + 66
    for i, line in enumerate(lines):
        txt(((x1 + x2) / 2, start + i * 28), line, F18, TEXT if i == 0 else MUTED, "ma")
    if tag:
        pill(x1 + 18, y1 + 15, tag, color, WHITE)


# Header
txt((65, 60), "PARK  /  SMART  /  HARNESS", F15, MUTED, "la")
txt((1735, 60), "FLOW 02  ·  IMPLEMENTATION VIEW", F15, MUTED, "ra")
txt((900, 118), "园区智能体 Harness · 端到端治理链路", F54, NAVY, "ma")
txt((900, 178), "示例：查询南区空调状态，并将目标设备调至 24℃", F28, TEXT, "ma")
txt((900, 220), "身份鉴权 · 动态上下文 · 事务内圈 · deny-first 工具治理 · 人工确认 · 事务恢复", F20, MUTED, "ma")

# Entry
rr((420, 270, 1380, 350), 20, BLUE_BG, BLUE, 2)
txt((900, 300), "用户 / 园区应用", F28, NAVY, "mm")
txt((900, 331), "已登录 · 携带会话 ID 与短期令牌", F18, MUTED, "mm")
arrow((900, 350), (900, 382), BLUE, 4)
stage(405, "01", "入口与身份", "agent_loop · agent_tools.identity", BLUE)

box((120, 445, 830, 575), "入站与恢复门", ["追加用户消息；pending 时仅接受批准 / 拒绝", "中断信号、消息序列修复、恢复入口分离"], AMBER, AMBER_BG)
box((970, 445, 1680, 575), "身份脊柱与能力快照", ["Principal：tenant / user / token", "ToolLoader 按 capability_code 收缩本轮工具集"], BLUE, BLUE_BG)
d.line((475, 575, 475, 605, 900, 605), fill=BLUE, width=3)
d.line((1325, 575, 1325, 605, 900, 605), fill=BLUE, width=3)
arrow((900, 605), (900, 642), BLUE, 4)

# Context
stage(665, "02", "上下文视图", "agent_context", GREEN)
box((145, 705, 1655, 850), "动态上下文装配", [
    "系统规则 + 当前 Principal + 长期记忆（可选）+ 精简历史 + 当前计划",
    "知识结果作为证据；控制结果不等于现状；超预算触发摘要与压缩",
], GREEN, GREEN_BG, title_size=F28)
pill(180, 790, "SYSTEM", GREEN)
pill(310, 790, "MEMORY", GREEN)
pill(448, 790, "HISTORY", GREEN)
pill(590, 790, "PLAN", GREEN)
pill(700, 790, "KNOWLEDGE", GREEN)
pill(878, 790, "TOKEN BUDGET", GREEN)
arrow((900, 850), (900, 892), GREEN, 4)

# Inner loop
stage(915, "03", "事务内圈", "agent_loop.run_loop", GREEN)
rr((250, 955, 1550, 1065), 22, WHITE, GREEN, 3)
txt((900, 990), "ASSEMBLE  →  MODEL  →  GATE  →  ACT  →  VERIFY  →  COMMIT", F28, GREEN, "mm")
txt((900, 1033), "模型重试 · token / iteration 预算 · stall / thrashing 看门狗 · 每轮防御性 repair", F18, MUTED, "mm")
arrow((900, 1065), (900, 1100), BLUE, 4)

box((300, 1115, 1500, 1215), "模型生成文本或工具批次", ["plan 只是全量意图快照；有工具调用时继续推进，无工具且正文非空时完成"], GREEN, GREEN_BG, title_size=F26)
arrow((900, 1215), (900, 1247), BLUE, 4)

# Tool portfolio
stage(1270, "04", "工具组合与准入", "agent_tools · harness_rag", BLUE)
tool_y1, tool_y2 = 1310, 1435
box((65, tool_y1, 425, tool_y2), "设备管理 Agent", ["device_status", "propose_control"], GREEN, GREEN_BG)
box((500, tool_y1, 860, tool_y2), "运行事项查询", ["工单 · 告警 · 事件", "设备健康 / 能耗"], GREEN, GREEN_BG)
box((935, tool_y1, 1295, tool_y2), "生活服务", ["会议室 · 停车", "餐厅查询"], BLUE, BLUE_BG)
box((1370, tool_y1, 1730, tool_y2), "知识检索", ["Milvus + Embedding", "Reranker · 二次检索"], BLUE, BLUE_BG)
centers = [245, 680, 1115, 1550]
for cx, color in zip(centers, [GREEN, GREEN, BLUE, BLUE]):
    arrow((cx, tool_y2), (cx, 1475), color, 3, 9)
d.line((245, 1475, 1550, 1475), fill=LINE, width=3)
arrow((900, 1475), (900, 1502), NAVY, 4)

rr((420, 1515, 1380, 1605), 20, WHITE, NAVY, 3)
txt((900, 1546), "CatalogGate · deny-first", F28, NAVY, "mm")
txt((900, 1580), "未注册 / 无权限 → DENY　|　只读 → ALLOW　|　控制 → ASK", F18, TEXT, "mm")

# Governance fork
d.line((900, 1605, 900, 1630), fill=NAVY, width=3)
d.line((290, 1630, 1415, 1630), fill=NAVY, width=3)
for cx, color in [(290, GRAY), (775, GREEN), (1415, AMBER)]:
    arrow((cx, 1630), (cx, 1660), color, 3, 9)

box((65, 1670, 515, 1800), "DENY · 安全阻断", ["合成 [blocked] 工具结果", "模型可见并重新规划"], GRAY, GRAY_BG)
box((550, 1670, 1000, 1800), "ALLOW · 并发只读", ["asyncio.gather 保序执行", "超时 / 重试 / 输出预算 / 结果校验"], GREEN, GREEN_BG)
box((1035, 1670, 1735, 1800), "ASK · 控制确认红线", ["冻结精确动作与 opaque handle", "提交 pending boundary，返回确认卡"], AMBER, AMBER_BG)

# Branch fulfilment
arrow((775, 1800), (775, 1835), GREEN, 3)
box((550, 1845, 1000, 1955), "权威数据源", ["园区 prod-api：设备 / 工单 / 告警 / 生活服务", "Milvus 知识库；身份与租户范围透传"], GREEN, WHITE)

arrow((1415, 1800), (1415, 1835), AMBER, 3)
box((1070, 1845, 1760, 1945), "人工确认：APPROVE / REJECT", ["批准后才调用 deviceCtrl / doorControl；拒绝则清理提案"], AMBER, WHITE, title_size=F26)
arrow((1415, 1945), (1415, 1975), AMBER, 3)
box((1070, 1985, 1760, 2095), "幂等恢复 + 状态读回", ["idem_key 防止重连或重放导致重复下发", "accepted ≠ effective；读回失败显式返回"], AMBER, AMBER_BG, title_size=F26)

# Convergence
d.line((290, 1800, 290, 2145, 360, 2145), fill=GRAY, width=3)
d.line((775, 1955, 775, 2145), fill=GREEN, width=3)
d.line((1415, 2095, 1415, 2145), fill=AMBER, width=3)
stage(2130, "05", "提交、持久化与返回", "ConversationStore · audit", BLUE)
box((290, 2170, 1510, 2260), "结构化结果汇流 → 原子提交事务边界 → 继续循环或形成退出原因", ["InMemory / Redis / PostgreSQL · pending 与幂等账本 · RAG / 记忆降级 · 运行审计"], BLUE, BLUE_BG, title_size=F26)
arrow((900, 2260), (900, 2280), BLUE, 4, 9)

# A compact terminal bar inside the bottom margin
rr((420, 2282, 1380, 2312), 15, NAVY, NAVY, 1)
txt((900, 2297), "返回用户：最终结论 / 确认卡 / 明确失败原因", F18, WHITE, "mm")
pill(65, 2278, "中断 · 预算 · 压缩", GRAY_BG, GRAY, 210)
pill(1510, 2278, "trace · latency · token", GRAY_BG, GRAY, 225)

im.save(OUT, optimize=True)
print(OUT)
