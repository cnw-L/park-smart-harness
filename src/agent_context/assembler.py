"""ParkContextAssembler — 中圈真上下文组装器(设计 §十,整合 §三~§七)。

实现内圈 `agent_loop.context.ContextAssembler` 协议,经 `run_loop(assembler=...)` 注入替桩。
**构造期注入** knowledge_tools(工具感知:认哪个 tool 是 RAG 套强说明);`assemble` 签名不动。

一轮 assemble:
  [系统头]  compose(固定层) + render_user(记忆层) → 一条 system
  [消息流]  drop_answered_tool_results(丢已答任务的工具结果) → exclude_plan_calls(排 plan)
            → trim_dialogue_turns(对话轮数裁剪) → 使用说明包装(普通轻/RAG 强)
  [尾部]    render_plan(derive_plan(日志)) → trailing system(provider 折进最近 user)
最后过 repair_messages 防御(合并连续 user / 丢孤儿),保证发出去的序列合法。

**完成判定一致**:丢弃以"文本答案=任务交付"为信号(与 loop 完成判定一致,不依赖 plan),故
顺序无强约束。裁剪按对话轮数。压缩=摘要是 v2,本组装器 v1 不调(见 history.py)。

**派生不入日志**:只读 conversation,产新视图列表,不改 conversation.messages。
"""
from __future__ import annotations

import logging
from dataclasses import replace as _dc_replace

from agent_loop.messages import Message
from agent_loop.plan import derive_plan
from agent_loop.repair import repair_messages

from .history import (
    apply_compaction_view, derive_compaction, drop_answered_tool_results,
    is_dropped_result, trim_dialogue_turns,
)
from .knowledge import KNOWLEDGE_TOOL, wrap_knowledge
from .memory import render_user
from .plan_view import exclude_plan_calls, render_plan
from .system_prompt import PromptSelection, compose
from .tokens import estimate_tokens

_log = logging.getLogger(__name__)


class ParkContextAssembler:
    def __init__(
        self,
        *,
        knowledge_tools=frozenset({KNOWLEDGE_TOOL}),
        control_tools=frozenset(),
        subagent_tools=frozenset(),
        keep_recent_turns: int = 8,
        keep_first: int = 1,
        soft_token_cap: int = 8000,
        context_window: int = 32768,
    ) -> None:
        self._knowledge = set(knowledge_tools)
        self._control = set(control_tools)            # 控制类工具名(结果套"已执行"框,非"现状")
        self._subagent = set(subagent_tools)          # 子 agent 工具名(结果套"子 agent 回报"框)
        self._keep_recent_turns = keep_recent_turns   # 裁剪:保留的最近对话**轮数**
        self._keep_first = keep_first
        self._soft_token_cap = soft_token_cap         # 总量观测阈(§2.4 token 可见·超阈告警)
        self._context_window = context_window         # 模型上下文窗口(算余量%;qwen3.5-9b=32768)

    # ── ContextAssembler 协议 ────────────────────────────────────────────────
    def assemble(self, config, conversation) -> list[Message]:
        # 缺 user 保护(与旧桩 LayeredContextAssembler 同):role-alternation 要求 system 后先 user。
        if not any(m.role == "user" for m in conversation.messages):
            raise ValueError("上下文组装失败:会话缺少 user 消息(调用方需先 seed 用户消息)")

        # 系统头:固定层 + 记忆层(并进一条 system)
        sel = PromptSelection.from_config(config)
        system_text = compose(sel)
        user_sec = render_user(getattr(conversation, "principal", None))
        if user_sec:
            system_text = f"{system_text}\n\n{user_sec}"
        out: list[Message] = [Message(role="system", content=system_text)]

        # 消息流:有压缩摘要 → 先在**原始 messages** 上 apply(与 select_compaction_span 的 step
        # 计数一致;若先 exclude_plan 去掉 plan-only 步,step 数错位、中段切错)→ 再丢弃/排 plan;
        # 无摘要 → 丢弃 → 排 plan → 对话轮数裁剪。最后使用说明包装。
        comp = derive_compaction(conversation.messages)
        if comp is not None:
            history = apply_compaction_view(conversation.messages, comp)   # 替中段为摘要 system note
            history = drop_answered_tool_results(history)
            history = exclude_plan_calls(history)
        else:
            history = drop_answered_tool_results(conversation.messages)
            history = exclude_plan_calls(history)
        # 裁剪两路都跑:压后近窗在两次压缩之间会长(下次压缩在 hard_cap 才触发),仍按对话轮数裁;
        # 摘要 note 是 system,_must_keep_in_trim 已护、不会被裁掉。
        history = trim_dialogue_turns(
            history,
            keep_recent_turns=self._keep_recent_turns,
            keep_first=self._keep_first,
        )
        out.extend(self._wrap_tool(m) for m in history)

        # 尾部:当前 plan(从日志派生)
        plan_text = render_plan(derive_plan(conversation.messages))
        if plan_text:
            out.append(Message(role="system", content=plan_text))

        # 总量观测 + context awareness(§2.4 / Anthropic「余量实时反馈给模型」):
        # 历史层只缩减历史段,但爆窗看的是**总量**(系统头+历史+plan)。超软阈时:
        #   ① log(ops 可见)② **把"接近上限"作为尾部 system 提示喂回模型**,让它主动收敛
        #   ——不是偷偷结构丢(确认模型管丢、v1 收敛靠丢弃+裁剪、压缩=摘要是 v2)。
        total = estimate_tokens(out)
        if total > self._soft_token_cap:
            _log.warning(
                "组装上下文约 %d tokens,超软阈 %d(系统头+历史+plan 总量)。v1 仅丢弃+裁剪收敛,"
                "压缩=摘要(v2)未上——若 provider 截断/报错即触此上限。", total, self._soft_token_cap,
            )
            out.append(Message(role="system", content=self._awareness_note(total)))

        # 防御:合并连续 user / 丢孤儿,保证发给 provider 的序列合法
        repair_messages(out)
        return out

    def _awareness_note(self, total: int) -> str:
        """context awareness(Anthropic):把余量喂回**模型**让它主动收敛,而非只 ops 告警。
        放尾部(recency)、随总量每轮更新(volatile,不破缓存前缀)。"""
        head = f"[上下文余量] 当前上下文约 {total} tokens"
        if self._context_window:
            head += f"、约占窗口 {min(int(total * 100 / self._context_window), 99)}%"
        return head + ",接近上限。请主动收敛:先给关键结论、长内容分步,别再堆细节;能收尾就收尾。"

    # ── 工具结果使用说明包装(普通轻 / RAG 强;缩减标记/占位不套) ─────────────
    def _wrap_tool(self, m: Message) -> Message:
        if m.role != "tool":
            return m
        content = m.content or ""
        name = m.name or ""
        # 占位 / 历史缩减标记不套(精确判定,别误伤以 "[" 开头的真实结果)
        if not content or content == "[pending_confirmation]" or is_dropped_result(content):
            return m
        if name in self._knowledge:
            return _dc_replace(m, content=wrap_knowledge(content))                       # 强
        if name in self._control:                                                        # 控制结果≠现状
            return _dc_replace(m, content=f"【{name}】(已执行的操作·结果如下)\n{content}")
        if name in self._subagent:                                                       # 子结果=回报,非现状
            return _dc_replace(m, content=f"【{name}】(子 agent 回报·结果如下)\n{content}")
        return _dc_replace(m, content=f"【{name or '工具结果'}】(后端现状·供参考)\n{content}")  # 轻
