"""任务层 · 中圈渲染与历史排除(设计 §六)。

- `render_plan`:把当前 plan 渲成人话的【当前计划】(content+status+result),规模上限 + 长 plan 折叠。
  **不 dump spec dict**(spec 是执行细节,不进给模型的视图)。
- `exclude_plan_calls`:把 plan 工具调用从**历史视图**里排除(plan 已在尾部单独渲染,历史里再留=双份)。
  **两 case**:① 那轮只调 plan → 整对删;② 混调别的工具 → 只摘 plan 项 + 删对应 result,保 role 配对。
  **只改视图副本,不动入参/日志**;`derive_plan` 仍读日志全量,不受影响。
"""
from __future__ import annotations

from dataclasses import replace as _dc_replace

from agent_loop.messages import Message

_SYM = {"done": "✓", "doing": "▶", "todo": " "}


# ── 渲染当前 plan(人话) ──────────────────────────────────────────────────────

def render_plan(plan, *, max_items: int = 12, max_result_chars: int = 60) -> str:
    """plan → 【当前计划】(人话);空 plan → 空串。长 plan 把开头连续 done 折成计数。

    plan 在尾部"保真不压",但单步 `result` 若被模型写成长段会撑大近窗(recency 高注意力区),
    故 `result` 渲染时按 `max_result_chars` 截断(只截显示,不动 plan 本体)。"""
    items = list(getattr(plan, "items", []) or [])
    if not items:
        return ""

    lead_done = 0
    for it in items:
        if it.status == "done":
            lead_done += 1
        else:
            break

    folded = ""
    shown = items
    if len(items) > max_items and lead_done > 2:
        folded = f"(前 {lead_done} 步已完成)"
        shown = items[lead_done:]

    lines = ["【当前计划】"]
    if folded:
        lines.append(folded)
    next_step = None
    for it in shown:
        sym = _SYM.get(it.status, " ")
        line = f"[{sym}] {it.content}"
        if it.result:
            r = it.result if len(it.result) <= max_result_chars else it.result[:max_result_chars] + "…"
            line += f" → {r}"
        lines.append(line)
        if next_step is None and it.status != "done":
            next_step = it.content
    # 执行指令(对齐 Claude Code TodoWrite 的 "continue / proceed" nudge):计划已登记在此,
    # **别再重复调用 plan 重列同一份计划**——否则弱模型(qwen)会盯着计划原地反复重列直到 stall。
    # 计划工具的调用已从历史排除,模型看不到"我刚列过",故必须由这条尾部指令推它去执行下一步。
    if next_step is not None:
        lines.append(
            f"\n↑ 计划已登记并已展示给用户。**立即调用对应工具执行下一步:「{next_step}」**"
            f"(查询 / 控制 / 检索等用相应工具)。"
            f"**不要再调用 plan**——计划与进度已自动展示,无需重列计划来更新状态;"
            f"只有当步骤本身要增删时才重新 plan。做完所有步骤直接用一段话汇报结果。")
    else:
        lines.append("\n↑ 计划所有步骤已完成。现在**直接用一段话向用户汇报结果**,不要再调任何工具。")
    return "\n".join(lines)


# ── 从历史视图排除 plan 工具调用 ──────────────────────────────────────────────

def exclude_plan_calls(messages: list[Message]) -> list[Message]:
    """返回排除了 plan 工具调用的**新列表**(视图副本);入参不变。

    case①:assistant 那轮只调 plan(无别的工具、无 content)→ 整条删(连同其 tool result)。
    case②:assistant 还调了别的工具(或有 content)→ 保留消息但从 tool_calls 摘掉 plan 项,
           并删掉 plan 那条 tool result;别的工具 + 其 result 原样留。
    """
    plan_result_ids: set[str] = set()
    out: list[Message] = []

    for m in messages:
        if m.role == "assistant" and m.tool_calls:
            plan_tcs = [tc for tc in m.tool_calls if tc.name == "plan"]
            if plan_tcs:
                plan_result_ids.update(tc.id for tc in plan_tcs)
                non_plan = [tc for tc in m.tool_calls if tc.name != "plan"]
                has_content = bool((m.content or "").strip()) or bool((m.reasoning or "").strip())
                if not non_plan and not has_content:
                    continue                      # case①:整条删
                out.append(_dc_replace(m, tool_calls=non_plan))   # case②:摘掉 plan 项
                continue
        if m.role == "tool" and m.tool_call_id in plan_result_ids:
            continue                              # 删 plan 的 tool result(配对一起走)
        out.append(m)

    return out
