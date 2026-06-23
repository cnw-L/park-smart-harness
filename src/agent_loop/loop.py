from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

from .budget import BudgetTracker
from .config import LoopConfig
from .context import ContextAssembler, LayeredContextAssembler
from .control import ControlCapability
from .conversation import Boundary, Conversation, ConversationStore
from .dispatch import SequentialToolExecutor, ToolExecutor
from .gate import DefaultGate, Gate
from .llm import ModelCaller, ModelTurn
from .messages import Message
from .repair import repair_messages
from .runcontrol import RunControl
from .tools import LoopToolRegistry, ToolContext
from .verify import NullVerifier, Verifier


class Compactor(Protocol):
    """压缩适配器(loop-facing)。具体实现在中圈 agent_context、组合根注入(保环隔离)。

    - `should_compact(prompt)`:prompt=本轮组装的 list[Message],超硬阈返 True。
    - `compact(conversation, seq, config)`:选段+摘要,返 `__compaction__` 消息对(append 进日志)
      或 None(无可压中段)。
    """
    def should_compact(self, prompt) -> bool: ...
    async def compact(self, conversation, seq: int, config) -> "list[Message] | None": ...


COMPACT_THRASH_LIMIT = 2


@dataclass
class LoopResult:
    final: str
    status: str                     # completed | awaiting_confirmation | budget_exhausted | failed | interrupted
    conversation: Conversation
    pending: list | None = None     # pending_batch when status == awaiting_confirmation
    reason: str | None = None       # 细化失败原因:model_error|empty_response|stall|no_progress|tool_failures|interrupted|persist_error|compaction_thrash


class _PersistError(Exception):
    """内部哨兵:store.*调用失败时抛出;由 run_loop 外层捕获转为 failed/persist_error。
    仅由 _safe_* 系列包装函数产生,不得在其他地方使用。"""


async def _safe_latest_boundary(store: ConversationStore, thread_id: str) -> "Boundary | None":
    """store.latest_boundary 失败时转为 _PersistError。"""
    try:
        return await store.latest_boundary(thread_id)
    except Exception as e:
        raise _PersistError("latest_boundary failed") from e


async def _safe_resolve_pending(
    store: ConversationStore,
    thread_id: str,
    resolved: "dict[str, Message]",
    boundary: "Boundary",
) -> None:
    """store.resolve_pending 失败时转为 _PersistError。"""
    try:
        await store.resolve_pending(thread_id, resolved, boundary)
    except Exception as e:
        raise _PersistError("resolve_pending failed") from e


async def _safe_commit(
    store: ConversationStore,
    thread_id: str,
    buffer: "list[Message]",
    boundary: "Boundary",
) -> None:
    """store.commit 失败时转为 _PersistError。"""
    try:
        await store.commit(thread_id, buffer, boundary)
    except Exception as e:
        raise _PersistError("commit failed") from e


_DEFAULT_ASSEMBLER = LayeredContextAssembler()
_DEFAULT_EXECUTOR = SequentialToolExecutor()
_DEFAULT_GATE = DefaultGate()
_DEFAULT_VERIFIER = NullVerifier()


async def _call_model_with_retry(
    model_caller: ModelCaller,
    config: LoopConfig,
    prompt: list[Message],
    schemas: list[dict],
    retries: int,
    base_delay: float = 0.5,
) -> ModelTurn | None:
    """模型调用带重试 + 指数退避;retries 次全失败返回 None(触发 failed 出口)。

    退避是必要的:真实 vLLM/qwen 会瞬时抖动(过载 5xx/超时),立即重试容易三次连撞;
    指数退避(base*2^attempt)给服务端恢复时间。最后一次失败不再 sleep,直接返回 None。"""
    for attempt in range(retries + 1):
        try:
            return await model_caller(config, prompt, schemas)
        except Exception:
            if attempt == retries:
                return None
            await asyncio.sleep(base_delay * (2 ** attempt))
    return None


async def run_loop(
    config: LoopConfig,
    conversation: Conversation,
    registry: LoopToolRegistry,
    budget: BudgetTracker,
    model_caller: ModelCaller,
    *,
    assembler: ContextAssembler = _DEFAULT_ASSEMBLER,
    executor: ToolExecutor = _DEFAULT_EXECUTOR,
    gate: Gate = _DEFAULT_GATE,
    store: ConversationStore,               # 必须提供;commit 驱动全部状态持久化
    control: ControlCapability | None = None,
    run_control: RunControl | None = None,
    resolution: dict[str, str] | None = None,   # {tool_call_id: "approve"|"reject"}
    cancel: bool = False,                        # True → 整批 reject-all → 干净边界 → 处理新意图
    depth: int = 0,
    verifier: Verifier = _DEFAULT_VERIFIER,
    compaction: "Compactor | None" = None,
) -> LoopResult:
    """事务型内圈引擎:一轮迭代 = 一个事务(assemble→model→tool batch→commit)。

    中断 = 不提交当前在途迭代(回滚)。
    挂起(控制工具) = 提交含占位符消息的边界 + pending_batch,返回 awaiting_confirmation。
    恢复 = 解析批次后继续正常循环。

    注:store 仅持久化引擎产生的 buffer。cancel→处理新意图时,新意图 user 消息须由
    调用方(服务端)先 store-commit(见集成测试 _commit_user_seed),仅在内存 append
    会在下次 load 丢失——入站消息落库是调用方职责,不是引擎职责。
    """
    thread_id = conversation.thread_id
    rc = run_control or RunControl()

    try:
        # ── 入口:重水化 + 恢复快速路径 ───────────────────────────────────────────
        last = await _safe_latest_boundary(store, thread_id)
        seq = last.seq if last else 0

        if last and last.budget_snapshot is not None:
            budget.restore(last.budget_snapshot)   # 恢复不得用新鲜预算上限

        if last and last.status == "awaiting_confirmation":
            # ── 模态门(§六补):pending 未决时,只接受两种输入 ────────────────────
            # ① cancel=True → 整批 reject-all(优先于 resolution);干净边界后处理新意图。
            # ② resolution{tool_call_id: approve/reject} → 解析整批。
            # 自由文本新意图绝不穿过 pending 态:既无 resolution 又无 cancel → 维持挂起。
            if cancel:
                # reject-all:把所有 pending action 统一标记为 reject,复用既有解析路径
                resolution = {p.tool_call_id: "reject" for p in last.pending_batch}
            elif resolution is None:
                # 无决策就重入:维持挂起状态,把批次再暴露给调用方
                return LoopResult("(等待确认)", "awaiting_confirmation", conversation,
                                  pending=last.pending_batch)

            # 不变式:awaiting_confirmation 边界只在 ask verdict 且 control 非 None 时产生
            # (control=None 时 ask 不进 pending_batch),故此处 control 必非 None。显式断言以防未来回归。
            assert control is not None, "BUG: awaiting_confirmation 存在 pending,但 control=None"

            # 解析批次:approve/reject 每条 pending action
            resolved: dict[str, Message] = {}
            for pending in last.pending_batch:
                decision = resolution.get(pending.tool_call_id, "reject")  # 默认拒绝(安全缺省)
                result = await control.resolve(pending, decision)
                content = result.content if result.ok else f"[error] {result.error}"
                resolved[pending.tool_call_id] = Message(
                    role="tool", content=content,
                    tool_call_id=pending.tool_call_id,
                    name=pending.frozen_action["name"],
                )

            # 把工作会话里的占位符替换为真实结果(保持位置)
            for i, m in enumerate(conversation.messages):
                if m.role == "tool" and m.tool_call_id in resolved:
                    conversation.messages[i] = resolved[m.tool_call_id]

            seq += 1
            await _safe_resolve_pending(
                store, thread_id, resolved,
                Boundary(status="iteration", turn_id=f"turn-{seq}", seq=seq,
                         pending_batch=None, budget_snapshot=budget.snapshot()),
            )
            # 继续进入正常循环

        # ── 主循环 ────────────────────────────────────────────────────────────────
        failures = 0
        empty_retries = 0
        MAX_EMPTY = 2
        stall_sigs: list = []
        STALL_LIMIT = 3
        # 无进展看门狗(对齐 Hermes:先 nudge 怼回、宽上限兜底,不 fail-fast):plan 是意图/记账
        # (且可捏造),不是动作 → 纯 plan-only 回合 = 无实际进展。连续 N 轮还不动手才停。
        no_progress = 0
        NO_PROGRESS_LIMIT = 2
        pending_nudge: str | None = None
        # 单子抽取上限(harness 设计 §S6/§九:主子共享池=总燃料闸,但每个 run_loop 调用另有自己的
        # 步数上限 = config.budget.max_iterations,子 cap 通常 < 主)。防一个子 agent 空转吃光整池。
        local_iters = 0
        # thrashing 看门狗(对齐 Claude Code 的 thrashing-error:连续几轮无"有效结果"就**如实停**,
        # 不烧到天花板、不伪装继续)。"有效"=有 ok 且非空、非 blocked 的工具结果;业务否/verify-failed/
        # deny 都不算进展 → 旧看门狗只数"光改 plan",抓不住"反复调工具但全失败"的死循环,这里补上。
        unproductive = 0
        UNPRODUCTIVE_LIMIT = 3

        while True:
            # 迭代顶部:防御性修复消息序列(孤立 tool / 连续 user),确保提供商收到合法序列
            repair_messages(conversation.messages)

            # 迭代顶部中断检查(此时没有在途工作需要回滚)
            if rc.interrupted:
                return LoopResult("(中断)", "interrupted", conversation, reason="interrupted")

            # 预算 / grace 检查
            is_grace = False
            if budget.exhausted():
                if budget.grace_available:
                    budget.use_grace()
                    is_grace = True
                else:
                    return LoopResult("(预算耗尽,已尽力收尾)", "budget_exhausted", conversation)
            # 单子抽取上限:本 run_loop 调用自己的步数上限(子 cap 通常 < 主/共享池)→ 到顶如实停,
            # 把剩余共享预算留给父会话兜底,而非一个子 agent 把整池烧穿。
            elif local_iters >= config.budget.max_iterations:
                return LoopResult("(本轮步数用尽,已尽力收尾)", "budget_exhausted", conversation)

            buffer: list[Message] = []

            # 组装本轮上下文;超硬阈则压缩(各自独立 commit、自己的边界)再重组,thrash 守卫兜底。
            prompt = assembler.assemble(config, conversation)
            if compaction is not None:
                n_compact = 0
                while compaction.should_compact(prompt):
                    if n_compact > COMPACT_THRASH_LIMIT:
                        return LoopResult("(压缩后仍超限,停止)", "failed",
                                          conversation, reason="compaction_thrash")
                    pair = await compaction.compact(conversation, seq, config)
                    if pair is None:
                        break                            # 无可压中段,已尽力
                    seq += 1
                    for m in pair:
                        conversation.append(m)
                    budget.consume(iterations=1)         # 压缩=一次 aux 模型调用,计预算(诚实+兜底)
                    await _safe_commit(store, thread_id, list(pair),
                        Boundary("iteration", f"turn-{seq}", seq, None, budget.snapshot()))
                    prompt = assembler.assemble(config, conversation)
                    n_compact += 1

            committed_len = len(conversation.messages)  # 回滚标记(压缩已 commit、纳入基线)

            # 上一轮无进展 → 本轮注入动态 nudge(只进本轮 prompt、不落日志):打断"输入不变→
            # 确定性重列计划"的死循环 + 把模型怼去执行。是 recency 位、每次只在空转那刻出现。
            if pending_nudge:
                prompt = list(prompt) + [Message(role="user", content=pending_nudge)]
                repair_messages(prompt)        # 防御:plan 渲空等情形下别造出连续 user / 非法序列

            # 模型调用(含重试)
            turn = await _call_model_with_retry(
                model_caller, config, prompt, registry.schemas(config.toolset), retries=2)
            if turn is None:
                return LoopResult("(模型调用失败)", "failed", conversation, reason="model_error")
            budget.consume(iterations=1, tokens=turn.usage_tokens)
            local_iters += 1                      # 本调用自己的步数(单子抽取上限用,独立于共享池)

            assistant_msg = Message(
                role="assistant", content=turn.content,
                reasoning=turn.reasoning, tool_calls=list(turn.tool_calls),
            )
            buffer.append(assistant_msg)
            conversation.append(assistant_msg)

            # ── 终止:grace 预算收尾(不论有无工具调用) ───────────────────────────
            if is_grace:
                seq += 1
                await _safe_commit(store, thread_id, buffer,
                    Boundary("completed", f"turn-{seq}", seq, None, budget.snapshot()))
                return LoopResult(turn.content, "budget_exhausted", conversation)

            # ── 终止:文本答案(无工具调用 + 有正文) = 完成 ─────────────────────
            # 模型不再调工具、直接给文本答案 → 任务结束(无论 plan 是否完成;plan 是模型记账、
            # 不是完成权威)。这是最简单也最稳的完成判定(OpenAI/Anthropic 原生:停止调工具即结束)。
            if not turn.tool_calls:
                if turn.content.strip():
                    seq += 1
                    await _safe_commit(store, thread_id, buffer,
                        Boundary("completed", f"turn-{seq}", seq, None, budget.snapshot()))
                    return LoopResult(turn.content, "completed", conversation)

                # 空响应:回滚本轮(不提交),重试
                del conversation.messages[committed_len:]
                empty_retries += 1
                if empty_retries > MAX_EMPTY:
                    return LoopResult("(模型空响应,重试耗尽)", "failed", conversation, reason="empty_response")
                continue

            empty_retries = 0

            # ── 无进展看门狗:纯 plan-only 回合 = 没干实事 → 先 nudge 怼回,连续超限才停 ──
            # (有非-plan 工具 = 真动作 → 清零;plan 工具不算"动作",它只是改意图、且能被捏造。)
            if any(c.name != "plan" for c in turn.tool_calls):
                no_progress = 0
                pending_nudge = None
            else:
                no_progress += 1
                if no_progress > NO_PROGRESS_LIMIT:
                    del conversation.messages[committed_len:]
                    return LoopResult("(连续多轮只更新计划、未执行,停止)", "failed",
                                      conversation, reason="no_progress")
                pending_nudge = (
                    "你刚才只更新了计划、没有执行任何步骤。计划已经记录好——"
                    "**现在立刻调用对应工具去完成下一个未完成的步骤**(查询/控制/检索等),"
                    "不要再调用 plan。所有步骤都完成了就直接用一段话给出最终答案。"
                )

            # ── 原地踏步检测:相同 tool-call 签名连续出现 STALL_LIMIT 次 ──────────
            sig = tuple(sorted(
                (c.name, repr(sorted(c.arguments.items()))) for c in turn.tool_calls))
            stall_sigs.append(sig)
            if (len(stall_sigs) >= STALL_LIMIT
                    and len(set(stall_sigs[-STALL_LIMIT:])) == 1):
                del conversation.messages[committed_len:]
                return LoopResult("(检测到原地踏步,停止)", "failed", conversation, reason="stall")

            # ── 工具批次执行(gate 路由) ────────────────────────────────────────
            # 注:熔断是「整批后」判定(failures>=max 在循环结束后查),不在批中途打断——
            # 与既有 failed/批末提交语义一致;一批内的所有调用都会先各自归一化并入 buffer。
            ctx = ToolContext(budget=budget, depth=depth, run_control=rc,
                              principal=conversation.principal)
            pending_batch: list = []
            results: list[Message | None] = [None] * len(turn.tool_calls)  # 按原顺序占位
            allow_items: list[tuple] = []  # (index, call, tool) 待并发

            # ── 第一遍:逐 call 过闸(分类);deny/ask 立即同步处理,allow 收集待并发 ──
            for i, call in enumerate(turn.tool_calls):
                tool = registry.get(call.name)
                verdict = gate.classify(call, tool, ctx)

                if verdict == "deny":
                    # 抄 Hermes:合成 blocked 结果、继续(模型看得见,可改策略);不计失败
                    results[i] = Message(
                        role="tool", content="[blocked] 无权限或被策略拦截",
                        tool_call_id=call.id, name=call.name,
                    )
                elif verdict == "ask":
                    if control is None:
                        # 防御:被判 ask 但无控制能力(理论上不应发生——子 agent 无控制工具)
                        results[i] = Message(
                            role="tool", content="[error] 需要确认但无控制能力",
                            tool_call_id=call.id, name=call.name,
                        )
                        failures += 1
                    else:
                        pending = control.freeze(call)   # 控制冻结:串行、绝不并发
                        pending_batch.append(pending)
                        results[i] = Message(
                            role="tool", content="[pending_confirmation]",
                            tool_call_id=call.id, name=call.name,
                        )
                else:  # allow → 收集,稍后并发
                    allow_items.append((i, call, tool))

            # ── 第二遍:allow 只读调用并发执行(asyncio.gather),保序;verify 各自跑 ──
            async def _run_allow(call, tool):
                outcome = await executor.execute_one(call, registry, ctx)
                # execute_one 的 executed/failed 必带 message;None 仅属 awaiting_confirmation
                # (执行器不再产生该态)。失声即 append(None) 会污染序列,故显式断言。
                assert outcome.message is not None, (
                    f"execute_one 对 {call.name} 返回了 message=None"
                    f"(disposition={outcome.disposition!r})"
                )
                if outcome.disposition == "executed":
                    # §五补:verify 接缝 — 结果边界校验(each capability's validation_policy)
                    # 仅对 executed 运行;failed = 基础设施异常,不走 verify 路径
                    vv = await verifier.verify(call, tool, outcome, ctx)
                    if not vv.business_ok:
                        # 校验失败必须作为 is_error 的 tool 结果让模型看见 → 自然触发重规划
                        outcome.message.is_error = True
                        body = outcome.message.content
                        if vv.note:
                            outcome.message.content = f"[verify-failed] {vv.note} | {body}"
                        else:
                            outcome.message.content = f"[verify-failed] {body}"
                return outcome

            if allow_items:
                outcomes = await asyncio.gather(*[_run_allow(c, t) for (_i, c, t) in allow_items])
                # 按 allow_items 的原顺序回填 + 按该顺序更新 failures(等价于串行逐个处理 allow)。
                # 注:ask(control=None)的 failures+=1 在分类遍已计;allow 的 reset 在此遍。
                # 二者跨类交错顺序与旧串行码略不同,但仅在「allow + 无 control 的 ask 同批」时有别——
                # 那是子 agent 误带控制工具的已防御死分支(工厂已拒),实务不可达。
                for (i, _c, _t), outcome in zip(allow_items, outcomes):
                    results[i] = outcome.message
                    if outcome.disposition == "failed":
                        failures += 1
                    else:
                        # executed(含业务否/verify-failed)不计基础设施失败
                        failures = 0

            # ── 按原 tool_calls 顺序写入 buffer / conversation(并发保序)──
            for msg in results:
                # results 中每个槽位都应被填充(deny/ask/allow 三类覆盖全部 call)
                assert msg is not None, "BUG: 工具批存在未填充的结果槽"
                buffer.append(msg)
                conversation.append(msg)

            # 工具批次后中断检查:回滚本轮在途工作(不提交)
            if rc.interrupted:
                del conversation.messages[committed_len:]
                return LoopResult("(中断)", "interrupted", conversation, reason="interrupted")

            # 有控制工具需要确认:提交占位符边界,挂起
            if pending_batch:
                seq += 1
                await _safe_commit(store, thread_id, buffer,
                    Boundary("awaiting_confirmation", f"turn-{seq}", seq,
                             pending_batch, budget.snapshot()))
                return LoopResult("(等待确认)", "awaiting_confirmation", conversation,
                                  pending=pending_batch)

            # 基础设施连续失败触发熔断
            if failures >= config.budget.max_tool_failures:
                seq += 1
                await _safe_commit(store, thread_id, buffer,
                    Boundary("failed", f"turn-{seq}", seq, None, budget.snapshot()))
                return LoopResult("(连续工具失败,停止)", "failed", conversation, reason="tool_failures")

            # ── thrashing 看门狗:本批工具一条"有效结果"都没有(全 业务否/verify-failed/blocked/空)→
            # 累计;连续 UNPRODUCTIVE_LIMIT 轮如实停(对齐 CC thrashing-error,不烧到天花板)。
            # 抓的是"反复调工具但全失败"的死循环(如控制 grounding 反复被拒)——旧 no_progress 只数
            # plan-only 回合、抓不到它。pending/awaiting 已在上面提前返回,不会误判为无进展。
            batch_useful = any(
                m is not None and m.role == "tool" and not m.is_error
                and (m.content or "").strip()
                and not (m.content or "").startswith(("[blocked]", "[error]"))
                for m in results)
            if batch_useful:
                unproductive = 0
            else:
                unproductive += 1
                if unproductive >= UNPRODUCTIVE_LIMIT:
                    del conversation.messages[committed_len:]
                    return LoopResult("(连续多轮无有效结果,停止)", "failed",
                                      conversation, reason="no_progress")

            # 正常迭代提交,继续下一轮
            seq += 1
            await _safe_commit(store, thread_id, buffer,
                Boundary("iteration", f"turn-{seq}", seq, None, budget.snapshot()))

    except _PersistError:
        # store.*失败:不对外暴露原始异常;conversation 内存尾未落库,调用方可安全重试
        # (控制账本幂等保证重试不会重复执行已提交动作)
        return LoopResult("(持久化失败)", "failed", conversation, reason="persist_error")
