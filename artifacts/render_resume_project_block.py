from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


W, H = 1600, 1020
OUT = Path(__file__).with_name("park-harness-resume-project.png")
BG = "#FFFEFD"
INK = "#17212B"
NAVY = "#153E63"
MUTED = "#63717D"
RULE = "#D9DEE3"

CN = r"C:\Windows\Fonts\msyh.ttc"
CN_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(CN_BOLD if bold else CN, size=size)


F_SECTION = font(26, True)
F_TITLE = font(31, True)
F_META = font(23)
F_BODY = font(23)
F_BODY_BOLD = font(23, True)


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)


def wrap_text(text: str, f: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for ch in text:
        candidate = current + ch
        if current and d.textbbox((0, 0), candidate, font=f)[2] > max_width:
            lines.append(current.rstrip())
            current = ch.lstrip()
        else:
            current = candidate
    if current:
        lines.append(current.rstrip())
    return lines


def draw_wrapped(x: int, y: int, text: str, f: ImageFont.FreeTypeFont,
                 max_width: int, fill=INK, line_height=38) -> int:
    lines = wrap_text(text, f, max_width)
    for line in lines:
        d.text((x, y), line, font=f, fill=fill, anchor="la")
        y += line_height
    return y


margin = 64
d.text((margin, 28), "项目经历", font=F_SECTION, fill=INK)
d.line((margin, 72, W - margin, 72), fill=RULE, width=2)

# Project identity row
d.text((margin, 103), "园区智能体 Harness", font=F_TITLE, fill=NAVY)
d.text((520, 111), "大模型应用架构工程师", font=F_META, fill=INK)
d.text((W - margin, 111), "2026.06–至今", font=F_META, fill=MUTED, anchor="ra")

y = 162
content = (
    "面向智慧园区设备管理、运行事项查询、知识检索与设备控制场景，构建具备动态上下文、"
    "事务内圈、工具治理、人工确认和可恢复持久化能力的智能体 Harness，解决模型直接执行副作用、"
    "长会话失控、工具越权及结果不可审计等问题。"
)
d.text((margin, y), "内容：", font=F_BODY_BOLD, fill=INK)
y = draw_wrapped(138, y, content, F_BODY, W - 138 - margin, line_height=39) + 8

bullets = [
    "负责 Harness 核心架构设计，拆分 agent_loop、agent_context、agent_tools 与 harness_rag 四个独立子系统，以事务步进函数驱动 ASSEMBLE → MODEL → GATE → ACT → VERIFY → COMMIT，统一完成、等待确认、预算耗尽、失败和中断五类退出状态。",
    "设计动态上下文装配机制，将系统规则、Principal、长期记忆、精简历史、知识证据与当前计划按轮次构造成模型视图，并实现 token 预算、历史裁剪、摘要压缩及长会话降级策略。",
    "建设 deny-first 工具治理链路，基于 capability_code 与用户身份动态收缩工具集；对设备控制采用 propose → ASK 挂起 → 人工确认 → 幂等执行 → 状态读回，以 opaque handle 和类型约束避免模型伪造参数或绕过确认。",
    "封装设备、工单/告警、生活服务与知识检索四类工具域，对接园区 prod-api、Milvus、Embedding 与 Reranker；实现只读工具并发保序、自然语言时间窗解析、超时重试、输出预算和结果校验。",
    "实现 InMemory、Redis、PostgreSQL 三类会话与审计存储，支持事务边界原子提交、pending 恢复、幂等账本、中断回滚、持久化失败归一化及 RAG/记忆显式降级，并提供 FastAPI 演示链路。",
]

for i, item in enumerate(bullets, 1):
    d.text((73, y), f"{i}.", font=F_BODY, fill=INK)
    y = draw_wrapped(108, y, item, F_BODY, W - 108 - margin, line_height=37) + 10

# Outcome block
d.line((margin, y + 1, W - margin, y + 1), fill="#E9ECEF", width=1)
y += 22
achievement = (
    "形成 4 个核心 Python 包、4 类工具域、3 种会话存储与 5 类引擎退出状态；源码沉淀 500+ "
    "测试函数，覆盖上下文装配、工具治理、控制挂起/恢复、并发执行、预算与中断、Redis/PostgreSQL "
    "持久化及 RAG 降级等关键链路。"
)
d.text((margin, y), "业绩：", font=F_BODY_BOLD, fill=INK)
draw_wrapped(138, y, achievement, F_BODY, W - 138 - margin, line_height=39)

img.save(OUT, optimize=True)
print(OUT)
