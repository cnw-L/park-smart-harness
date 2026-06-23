from __future__ import annotations

from typing import Callable, Protocol

from .config import LoopConfig
from .conversation import Conversation
from .messages import Message


class ContextAssembler(Protocol):
    """上下文子系统:每轮动态组装发给模型的输入(视图),不是一条增长的历史。"""

    def assemble(self, config: LoopConfig, conversation: Conversation) -> list[Message]: ...


# 记忆/知识层 hook 类型:接收 (config, conversation),返回注入的 Message 列表
_LayerHook = Callable[[LoopConfig, Conversation], list[Message]]


def _empty_hook(config: LoopConfig, conversation: Conversation) -> list[Message]:
    return []


class LayeredContextAssembler:
    """五层分层上下文组装器,按缓存序排列(§2.1/§2.54):

    缓存前缀(stable):
      [0] 固定层  — role + 不变指令(跨迭代稳定,不含 plan)
      [1] 记忆层  — memory hook 注入(默认空)
      [2] 知识层  — knowledge hook 注入(默认空)

    volatile zone:
      [3] 历史层  — conversation.messages(每轮增长)
      [4] 任务层  — plan 快照(每轮可变,放 LAST → 不炸缓存前缀)

    §2.54 警告:plan 摆错位置 = 每轮炸缓存 = 延迟翻倍。
    任务层用 role="system" 追加在历史之后;未来 provider adapter 可按 Hermes 规范
    将其折叠进当轮 user message,但 volatile-tail 摆放是此处的核心不变量。
    """

    def __init__(
        self,
        memory: _LayerHook | None = None,
        knowledge: _LayerHook | None = None,
    ) -> None:
        # 默认 hook 返回空列表(_empty_hook 恒真,可用 or 简写)
        self._memory: _LayerHook = memory or _empty_hook
        self._knowledge: _LayerHook = knowledge or _empty_hook

    def assemble(self, config: LoopConfig, conversation: Conversation) -> list[Message]:
        # ── 缺 user 消息保护(与旧实现语义相同) ────────────────────────────────
        if not any(m.role == "user" for m in conversation.messages):
            raise ValueError(
                "上下文组装失败:会话缺少 user 消息。role-alternation 要求 system 之后先是 user"
                "(见 Hermes conversation_loop 的交替校验/修复);调用方需先 seed 用户消息。"
            )

        # ── 固定层(stable cache prefix) ────────────────────────────────────────
        # 内容必须跨迭代不变:不含 plan、不含任何 volatile 内容
        system_content = (
            f"你是 role={config.role} 的 agent。逐步思考并调用工具完成任务。"
            "遇到需要多步/分阶段的任务,先调用 plan 工具列出步骤(每步 id/content/status,可带 spec),"
            "执行过程中随进展更新各步状态(todo→doing→done);简单的单步任务可直接做、无需列计划。"
            "完成时不要再调工具、直接给最终回答。"
            "若某控制操作被用户拒绝或取消,视为该步骤已跳过,不要再重复提议同一操作,直接如实汇总。"
        )
        result: list[Message] = [Message(role="system", content=system_content)]

        # ── 记忆层 ─────────────────────────────────────────────────────────────
        result.extend(self._memory(config, conversation))

        # ── 知识层 ─────────────────────────────────────────────────────────────
        result.extend(self._knowledge(config, conversation))

        # ── 历史层(volatile) ───────────────────────────────────────────────────
        result.extend(conversation.messages)

        # ── 任务层:plan 快照放 LAST(volatile tail) ────────────────────────────
        # plan 每轮可能变化;放最后确保不污染缓存前缀(§2.54)。
        # role="system" 与固定层同类型,但因为位置在历史之后属于 volatile zone;
        # 未来 provider adapter 可按 Hermes 规范折叠进当轮 user message。
        plan_text = conversation.plan.render()
        if plan_text:
            result.append(Message(role="system", content=plan_text))

        return result
