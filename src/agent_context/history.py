"""历史层缩减(设计 §五,CONFIRMED 模型,v1 零模型)。

历史层本体 = **正常用户/模型对话 + 普通工具结果**(设备状态/工单等),来自消息日志。
plan 工具调用虽在原始日志里,但组装历史视图时由 §六 `exclude_plan_calls` 整对排除。

**CONFIRMED 模型** —— 缩减**按对象与生命周期**,不按位置/长度/token:

① **丢弃 `drop_answered_tool_results`**:对象=普通工具结果。
   **触发 = 任务已交付**——即**模型给出文本答案(content-only assistant)**,无论 plan 是否完成。
   理由:文本答案 = 本任务结束(与 loop 完成判定一致),其前的工具结果是已答任务的死重。
   规则:一条普通工具结果**可丢**(content 缩成短标记、**保 tool_call_id 配对**)当且仅当它**后面
   出现过文本答案**。最后一个文本答案**之后**(当前任务)、或还没有任何文本答案时的工具结果
   **一律保留**(当前任务还要用)。挂起占位 `[pending_confirmation]` 永不缩(恢复锚点)。
   比 plan-epoch 简单:不依赖 plan 快照/状态,也不必跑在 plan 排除之前。

② **裁剪 `trim_dialogue_turns`**:对象=自然 user/model 对话。**按对话轮数**:保最近 N 轮,
   旧对话整轮丢,留占位 `[旧对话 N 轮已省略]`。**不是**单条长度截断。
   三不丢:① 首轮(头/primacy)② 近窗(尾/recency)③ 挂起占位。
   为保工具配对:只丢 content-only 对话消息(无 tool_calls、非 tool 结果、非挂起占位),
   带 tool_calls / tool 结果 / 占位的消息一律留在原位。

③ **压缩 = 摘要**:把丢掉的旧对话摘要成一段。**需要模型 → 是 v2,v1 不实现**(留 hook)。

**v1 已知上限(显式记录,不掩盖)**:v1 没有模型摘要,也**不加任何基于 token 的结构性硬兜底**
(设计 owner 明确否决"丢弃冒充压缩")。v1 的规模收敛**只来自 ① 丢弃 + ② 裁剪**。若过完两步
上下文仍过大,那是 v1 的已知限制,由 v2 摘要解决——不在 v1 用结构丢来糊弄。
"""
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace as _dc_replace

from agent_loop.messages import Message

# 压缩快照的纯数据 + 协议常量住在这一层(零模型的派生/视图层)。compactor.py(模型/适配层)
# 单向 import 它们 —— 故意不反向 import compactor,保 history↔compactor 无环。
_COMPACTION = "__compaction__"   # 摘要伪工具名:摘要作 assistant tool_call + tool result 快照入日志


@dataclass(frozen=True)
class Compaction:
    """从日志派生的当前压缩快照(最新一条 __compaction__ 的内容)。"""
    summary: str             # 已套 SUMMARY_PREFIX 框的摘要全文
    covers_through_seq: int  # 被并入的 boundary seq(折叠/审计用)
    head_keep: int           # 压缩时保留的首轮数
    recent_turns: int        # 压缩时按 token 预算保留的近窗轮数


_PENDING = "[pending_confirmation]"
_DROPPED_SUFFIX = "旧结果已省略]"   # 丢弃缩成的 content 尾标;assembler 用 is_dropped_result 识别、跳过包装
# ★控制提案是**延迟动作**:登记后要到后续回合才执行确认 → 它的结果在被 resolve 前不能当"已答死重"丢
#   (否则模型忘了已提案 → 重复提案;真值虽在 ProposalStore,日志豁免保上下文连贯)。四不丢之一。
_STICKY_CONTROL_TOOLS = frozenset({"propose_control"})


def is_dropped_result(content: str | None) -> bool:
    """该 content 是否是 ① 丢弃缩成的标记(assembler 据此跳过使用说明包装,避免按字面串耦合)。"""
    return (content or "").endswith(_DROPPED_SUFFIX)


def _is_ordinary_tool_result(m: Message) -> bool:
    """普通工具结果 = role==tool 且不是 plan/压缩/未消解控制提案 的结果。
    (plan 由 §六排除;压缩摘要永不缩;propose_control 提案是延迟动作、resolve 前不丢——四不丢。)"""
    return (m.role == "tool"
            and (m.name or "") not in ("plan", _COMPACTION)
            and (m.name or "") not in _STICKY_CONTROL_TOOLS)


def _is_text_answer(m: Message) -> bool:
    """文本答案 = 有正文、无工具调用的 assistant 消息。loop 据此判完成(模型给文本答案=结束),
    所以它也是"任务已交付"的标记:其前的工具结果都是已答任务的死重。"""
    return m.role == "assistant" and bool((m.content or "").strip()) and not m.tool_calls


# ── ① 丢弃:任务已交付(文本答案)即丢其工具结果 ────────────────────────────────

def drop_answered_tool_results(messages: list[Message]) -> list[Message]:
    """缩减**已交付任务**的普通工具结果 content(保 tool_call_id 配对)。

    完成判定(与 loop 一致):**模型给出文本答案(content-only assistant)= 任务交付**,
    无论 plan 是否完成。故一条普通工具结果**可丢**当且仅当它**后面出现过文本答案**(所属任务
    已被回答、结果是死重)。最后一个文本答案**之后**(当前任务)、或还没有任何文本答案时的
    工具结果**一律保留**(当前任务还要用)。挂起占位 `[pending_confirmation]` 永不缩(恢复锚点)。

    比 plan-epoch 简单:不依赖 plan 快照/状态——交付信号就是文本答案本身。
    """
    last_answer = -1
    for i, m in enumerate(messages):
        if _is_text_answer(m):
            last_answer = i
    if last_answer < 0:
        return list(messages)            # 还没有任何交付 → 不丢

    out: list[Message] = []
    for i, m in enumerate(messages):
        if (_is_ordinary_tool_result(m) and (m.content or "") != _PENDING and i < last_answer):
            label = m.name or "工具"
            out.append(_dc_replace(m, content=f"[{label}·{_DROPPED_SUFFIX}"))
        else:
            out.append(m)
    return out


# ── ② 裁剪:对话轮数 ───────────────────────────────────────────────────────────

def _turn_starts(messages: list[Message]) -> list[int]:
    """对话轮起点 = 每条 user 消息的索引(自然对话以 user 开启一轮)。"""
    return [i for i, m in enumerate(messages) if m.role == "user"]


def _step_starts(messages: list[Message]) -> list[int]:
    """步起点 = user 或 assistant 消息索引。一个长请求(1 个 user 轮)内部有多个 assistant 迭代步,
    压缩按**步**选段(轮太粗:单请求只 1 轮)。每步 = [assistant, 紧随的 tool 结果...],配对天然不裂。"""
    return [i for i, m in enumerate(messages) if m.role in ("user", "assistant")]


def trim_dialogue_turns(
    messages: list[Message],
    *,
    keep_recent_turns: int = 8,
    keep_first: int = 1,
) -> list[Message]:
    """按**对话轮数**裁剪:保首 `keep_first` 轮 + 最近 `keep_recent_turns` 轮,
    中间旧对话整轮丢,留占位 `[旧对话 N 轮已省略]`。

    三不丢:① 首轮 ② 近窗 ③ 挂起占位 `[pending_confirmation]`。
    为保工具配对:只丢 content-only 对话消息(无 tool_calls、非 tool 结果、非挂起占位);
    带 tool_calls 的 assistant / tool 结果 / 占位一律留在原位(repair 不补悬空方向)。
    """
    starts = _turn_starts(messages)
    n_turns = len(starts)
    if n_turns <= keep_first + keep_recent_turns:
        return list(messages)

    # 要丢的"中段"轮的消息区间 [drop_lo, drop_hi)
    drop_lo = starts[keep_first]                         # 第 keep_first 轮起点(0-based:跳过前 keep_first 轮)
    drop_hi = starts[n_turns - keep_recent_turns]        # 最近 keep_recent_turns 轮起点

    dropped_turns = (n_turns - keep_recent_turns) - keep_first
    placeholder = Message(role="user", content=f"[旧对话 {dropped_turns} 轮已省略]")

    out: list[Message] = list(messages[:drop_lo])
    out.append(placeholder)
    # 中段:只丢 content-only 对话;保命的(占位/工具配对)留
    for m in messages[drop_lo:drop_hi]:
        if _must_keep_in_trim(m):
            out.append(m)
    out.extend(messages[drop_hi:])
    return out


def _must_keep_in_trim(m: Message) -> bool:
    """中段裁剪里**不能丢**的消息:挂起占位 / 带 tool_calls 的 assistant / 任何 tool 结果。

    (丢这些会留悬空 tool_call 或孤儿 tool result,破坏配对——repair 不补这个方向。)
    纯 content 的 user/assistant 对话才是裁剪对象。
    """
    if (m.content or "") == _PENDING:
        return True
    if m.role == "system":            # 压缩摘要 note 是 system,裁剪不能丢
        return True
    if m.role == "tool":
        return True
    if m.role == "assistant" and m.tool_calls:
        return True
    return False


# ── ③ 压缩 = 摘要(v2):派生 / 选段 / 视图变换 ──────────────────────────────────
# 摘要本体由 loop 触发、aux 模型产出(compactor.py);摘要作 __compaction__ 伪工具调用快照
# append 进日志(镜像 plan)。这里是零模型的派生/选段/投影,与丢弃/裁剪同层、纯视图。

def _is_compaction_call(m: Message) -> bool:
    return m.role == "assistant" and any(tc.name == _COMPACTION for tc in (m.tool_calls or []))


def _is_compaction_msg(m: Message) -> bool:
    """__compaction__ 对的任一半(assistant 调用 或 tool 结果)。"""
    return _is_compaction_call(m) or (m.role == "tool" and (m.name or "") == _COMPACTION)


def derive_compaction(messages: list[Message]) -> Compaction | None:
    """从日志取**最新** __compaction__ 快照(镜像 derive_plan,latest-wins)。无 → None。"""
    for i in range(len(messages) - 1, -1, -1):
        m = messages[i]
        if not _is_compaction_call(m):
            continue
        tc = next((t for t in m.tool_calls if t.name == _COMPACTION), None)
        if tc is None or not isinstance(tc.arguments, dict):
            continue
        summary = ""                              # 摘要全文在配对 tool result 里
        for j in range(i + 1, len(messages)):
            r = messages[j]
            if r.role == "tool" and r.tool_call_id == tc.id:
                summary = r.content or ""
                break
        return Compaction(
            summary=summary,
            covers_through_seq=int(tc.arguments.get("covers_through_seq", 0)),
            head_keep=int(tc.arguments.get("head_keep", 1)),
            recent_turns=int(tc.arguments.get("recent_turns", 0)),
        )
    return None


def select_compaction_span(
    messages: list[Message], *, keep_first: int, tail_token_budget: int, estimate_tokens
) -> "tuple[list[Message], list[Message], int] | None":
    """选要摘的中段。返回 (head, middle, recent_turns) 或 None(无可压中段)。

    head = 前 keep_first **步**;recent = 从尾按 token 预算保的整步(步对齐保工具配对);
    middle = 之间。挂起占位落中段 → None(挂起态不压)。**按步**(非轮):单请求只 1 轮但多步。
    """
    starts = _step_starts(messages)
    n = len(starts)
    if n <= keep_first + 1:
        return None
    recent_turns = 0
    acc = 0
    for i in range(n - 1, keep_first - 1, -1):
        end = starts[i + 1] if i + 1 < n else len(messages)
        acc += estimate_tokens(messages[starts[i]:end])
        recent_turns += 1
        if acc >= tail_token_budget:
            break
    recent_start_turn = n - recent_turns
    if recent_start_turn <= keep_first:
        return None                               # head 与 recent 覆盖全部,无中段
    head = messages[:starts[keep_first]]
    middle = messages[starts[keep_first]:starts[recent_start_turn]]
    if any((m.content or "") == _PENDING for m in middle):
        return None                               # 挂起占位在中段 → 不压
    return head, middle, recent_turns


def apply_compaction_view(messages: list[Message], compaction: Compaction) -> list[Message]:
    """纯视图:把最新 __compaction__ 之前的中段替成已框摘要 note,留头+近窗+其后。不改入参。

    摘要 note 是 role=system(`_wrap_tool` 只碰 role==tool,故不套框)。
    """
    p = None
    for i, m in enumerate(messages):
        if _is_compaction_call(m):
            p = i
    if p is None:
        return list(messages)
    after = p + 1                                 # 跳过配对的 __compaction__ tool result
    if after < len(messages) and messages[after].role == "tool":
        after += 1
    pre, future = messages[:p], messages[after:]

    starts = _step_starts(pre)
    n = len(starts)
    note = Message(role="system", content=compaction.summary)
    if n == 0:
        return [note] + list(future)
    hk = min(compaction.head_keep, n)
    recent_start_turn = max(hk, n - compaction.recent_turns)
    head = pre[:starts[hk]] if hk < n else list(pre)
    recent = pre[starts[recent_start_turn]:] if recent_start_turn < n else []
    # 滚动:被取代的旧 __compaction__ 对若落进头/近窗/其后,剔除(只留最新摘要 note,
    # 否则旧摘要会以悬空 tool_call + 错框"(后端现状)"泄漏给模型)。
    def _keep(seq):
        return [m for m in seq if not _is_compaction_msg(m)]
    return _keep(head) + [note] + _keep(recent) + _keep(future)
