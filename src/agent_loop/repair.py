"""repair.py — 每轮防御性消息序列修复(移植自 Hermes repair_message_sequence)。

在每轮迭代顶部调用,纠正外部传入或会话恢复后可能携带的畸形 role 交替,
避免提供商因序列违规返回静默空响应触发无效重试循环。

两轮修复(与 Hermes 一致):
  Pass 1 — 丢弃孤立 tool 消息(tool_call_id 不匹配任何前置 assistant tool_call)。
  Pass 2 — 合并连续 user 消息(以 '\\n\\n' 分隔,不丢失任何用户输入)。

不处理的合法模式:assistant(tool_calls)+tool 后紧跟 user 的进行中对话 —— 这是
合法的重定向模式(Hermes 文档明确指出),不予回滚。
"""
from __future__ import annotations

from .messages import Message


def repair_messages(messages: list[Message]) -> int:
    """原地修复消息列表的 role 交替违规,返回修复次数(0 = 无需修复)。

    仅在 repairs > 0 时才执行 in-place 重写(messages[:] = merged),
    确保下游路径(持久化、返回值、会话 DB flush)看到修复后的序列。
    """
    if not messages:
        return 0

    repairs = 0

    # ── Pass 1:丢弃孤立 tool 消息 ─────────────────────────────────────────
    # 维护滚动集合:每遇到 assistant 消息就刷新为该轮 tool_calls 的 id 集合;
    # 每遇到 user 消息则清空(关闭当前 tool-result 运行)。
    # tool 消息的 tool_call_id 不在集合中 → 孤立 → 丢弃。
    known_tool_ids: set[str] = set()
    filtered: list[Message] = []

    for msg in messages:
        role = msg.role
        if role == "assistant":
            # 刷新已知 id 集合为本轮工具调用
            known_tool_ids = {tc.id for tc in (msg.tool_calls or [])}
            filtered.append(msg)
        elif role == "tool":
            tc_id = msg.tool_call_id
            if tc_id and tc_id in known_tool_ids:
                filtered.append(msg)
            else:
                repairs += 1   # 孤立 tool → 丢弃
        else:
            # user 轮关闭 tool-result 运行(清空已知 id);后续 tool 无新鲜 assistant → 孤立。
            # system 不清空 —— 与 Hermes 一致;且本仓 system 仅在位置 0(其后才有 assistant),
            # 清不清空等价,不影响行为。
            if role == "user":
                known_tool_ids = set()
            filtered.append(msg)

    # ── Pass 2:合并连续 user 消息 ─────────────────────────────────────────
    # 保留所有用户输入,不丢失任何内容。
    # 内容均为 str(我们的 Message.content 始终是 str),无需多模态特判,
    # 但仍防御性处理空字符串(与 Hermes 一致)。
    merged: list[Message] = []
    for msg in filtered:
        if (
            merged
            and msg.role == "user"
            and merged[-1].role == "user"
        ):
            prev = merged[-1]
            prev_content = prev.content or ""
            new_content = msg.content or ""
            prev.content = (
                (prev_content + "\n\n" + new_content)
                if prev_content and new_content
                else (prev_content or new_content)
            )
            repairs += 1
            continue
        merged.append(msg)

    if repairs > 0:
        # 仅在确实有修复时才重写,保留无修复路径的对象标识
        messages[:] = merged

    return repairs
