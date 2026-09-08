"""Render a second, code-accurate example in the approved workflow visual system."""
from pathlib import Path


source_path = Path(__file__).with_name("render_harness_workflow.py")
source = source_path.read_text(encoding="utf-8")

# Preserve the approved geometry and apply the same visual refinement pass.
visual = {
    'OUT = Path(__file__).with_name("park-smart-harness-workflow.png")':
        'OUT = Path(__file__).with_name("park-harness-alert-knowledge-workflow.png")',
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
    'f = font(15, bold=True)': 'f = font(16, bold=True)',
    'h = 30': 'h = 34',
    'font=font(45, bold=True)': 'font=font(48, bold=True)',
    'font=font(24, bold=True)': 'font=font(26, bold=True)',
    'title_size=22': 'title_size=24',
    'title_size=23': 'title_size=24',
    'img.save(OUT, quality=96)': 'img.save(OUT, quality=96, optimize=True)',
}
for old, new in visual.items():
    source = source.replace(old, new)

# Example-specific content: a real record query plus RAG evidence retrieval.
content = {
    '园区智能体 Harness · 端到端调用链路': '园区智能体 Harness · 告警研判调用链路',
    '示例：查询南区空调状态，并将目标设备调至 24℃':
        '示例：查询本周南区未处理告警，并结合知识库给出排查建议',
    '身份鉴权 · 动态上下文 · 工具治理 · 人工确认 · 事务恢复':
        '身份鉴权 · 时间窗解析 · 并行只读 · 证据检索 · 结构化汇总',
    '系统规则 + 当前用户 + 长期记忆（可选） + 精简历史 + 当前计划\n知识结果标注为证据；控制结果不等于现状；超阈触发摘要压缩':
        '系统规则 + 当前用户 + 长期记忆（可选） + 精简历史 + 当前计划\n时间窗与状态口径进入上下文；知识结果标注为证据；超阈触发摘要压缩',
    'plan 只是全量意图快照，不是完成权威；无工具且有正文才完成':
        'plan：查询告警 → 检索知识 → 对齐告警类型与证据 → 生成排查建议',
    '"设备管理 Agent", "device_status\npropose_control", GREEN, GREEN_FILL':
        '"设备管理（备用）", "device_status\npropose_control", GRAY, GRAY_FILL',
    '"运行事项查询", "工单 · 告警 · 事件\n设备健康 / 能耗", GREEN, GREEN_FILL':
        '"运行事项查询", "record_query\n告警 · status · time", GREEN, GREEN_FILL',
    '"生活服务", "会议室 · 停车\n餐厅查询", BLUE, BLUE_FILL':
        '"生活服务（备用）", "meeting / parking\nrestaurant_query", GRAY, GRAY_FILL',
    '"知识检索", "Milvus + Embedding\nReranker · 二次检索", BLUE, BLUE_FILL':
        '"知识检索", "knowledge_query\nMilvus · Reranker", GREEN, GREEN_FILL',
    '只读工具 asyncio.gather\n超时 / 重试 / 输出预算 / 结果校验':
        'record_query + knowledge_query\n时间窗解析 / 输出预算 / 结果校验',
    'ASK · 控制确认红线': 'ASK · 本例不触发',
    '从服务端提案冻结精确动作\n提交 pending Boundary → 返回确认卡':
        '当前请求不含控制动作\n误调用控制工具仍会挂起并返回确认卡',
    '人工确认：APPROVE / REJECT': '控制路径（备用）',
    '批准后才 deviceCtrl / doorControl；拒绝则清提案':
        '若后续产生控制动作，仍需 APPROVE / REJECT',
    'in_flight → done / failed\naccepted ≠ effective · 不确定时不盲目重发':
        '本例未进入控制执行\n只读查询不创建控制票据，也不产生设备副作用',
    '园区 prod-api（设备 / 工单 / 告警） · 生活服务 · Milvus 知识库':
        'prod-api alarmPage（告警） · Milvus 知识库\n时间窗 / status / tenant 范围贯穿两路检索',
    '④ 结构化结果汇流 → 提交事务边界 → 继续循环或生成最终回答':
        '④ 告警事实 + 知识证据汇流 → 提交事务边界 → 生成排查建议',
    'ConversationStore：InMemory / Redis ｜ PostgreSQL：幂等与审计 ｜ RAG / 记忆优雅降级':
        'ConversationStore：InMemory / Redis ｜ PostgreSQL：边界与审计 ｜ RAG 失败显式降级',
    '⑤ 返回用户：最终结论 / 确认卡 / 明确失败原因':
        '⑤ 返回用户：未处理告警清单 + 分项排查建议（含证据）',
}
for old, new in content.items():
    source = source.replace(old, new)

# Complete the same two connector defects fixed in the approved baseline.
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
