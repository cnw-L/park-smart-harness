"""`ProposalControlCapability` —— 实现 agent_loop 的 `ControlCapability` 协议。

M2-refined 的落点:`execute_proposal(handle)` 被 gate 判 `ask` → loop 调本类 `freeze`。
`freeze` 据 handle 从 `ProposalStore` 还原**提案的精确动作**,冻成 `PendingAction`
(`frozen_action` = 提案的 action/params,**不是** `execute_proposal(handle=…)` 这层调用)——
即"控制参数从提案取、模型绝不重打"。`resolve` 抄 `FakeControlCapability` 的幂等账本语义。

零 loop 改动:它就是个 `ControlCapability`,组合根把它当 `control=` 注入 run_loop 即可。
"""
from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from agent_loop.control import Decision
from agent_loop.messages import ToolCallReq
from agent_loop.pending import PendingAction
from agent_loop.tools import ToolResult

from .backend import BackendClient
from .proposal import ProposalStore

_INVALID = "__invalid_proposal__"   # 未知/过期 handle 的哨兵动作名


class ProposalControlCapability:
    """提案驱动的控制能力。`backend=None` → echo 桩(单测/无后端);注入 `BackendClient` →
    真 `deviceCtrl` 下发 + `getDevicePage` 读回对账(**已受理 ≠ 已生效**)。"""

    def __init__(self, store: ProposalStore, backend: BackendClient | None = None,
                 execution_mode: str = "simulated", ledger=None) -> None:
        self._store = store
        self._backend = backend
        # ★默认 simulated:不真下发 deviceCtrl(内圈定稿 §八硬依赖:后端无 commandId/幂等前不可逆控制
        #   不能上线)。real 显式开,且只在后端幂等就绪后。
        self._execution_mode = execution_mode
        # ★账本可插拔:注入持久化账本(PgIdempotencyLedger,get/put_if_absent/update)→ 写前账本(WAL),
        #   at-most-once 跨重入/重启;None=回退进程内 dict(向后兼容,单测/无 PG)。
        self._ledger_db = ledger
        self._ledger: dict[str, ToolResult] = {}   # ledger=None 时的回退:idem_key→结果,重入不重发
        self.execute_count: int = 0

    @staticmethod
    def _idem_key(handle: str, action: str, params: dict) -> str:
        """确定性 idem_key(从 handle+action+params 派生)——重入/重启映**同一**账本条目,
        是 WAL 跨重启 at-most-once 的前提(uuid4 每次不同 → 永远 miss → 会重发)。"""
        blob = handle + "|" + action + "|" + json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]

    def freeze(self, call: ToolCallReq, thread_id: str = "") -> PendingAction:
        """还原提案 → 冻结精确动作。★handle 不经模型:留空 = 取该**会话**最近一条未消解提案
        (模态门保证同会话同时只一条 pending)。**按 thread_id 切片**——绝不取到别用户的提案(串提案事故)。
        未知/无提案不抛(loop 无 try),铸哨兵。"""
        req_handle = str(call.arguments.get("handle", ""))     # 模型给的 handle(仅哨兵报错回显用)
        handle = req_handle
        proposal = self._store.get(handle) if handle else None
        # 安全:get 命中但不属本会话 → 当未命中(防带别人 handle 跨会话执行)
        if proposal is not None and proposal.thread_id and proposal.thread_id != thread_id:
            proposal = None
        if proposal is None:                       # 无 handle/坏 handle/跨会话 → 取**本会话**最近一条
            handle, proposal = self._store.latest_for(thread_id)  # (模态门保证同会话只一条 pending)
        if proposal is None:                       # 本会话无提案 → 哨兵 → demo 友好卡
            return PendingAction(
                tool_call_id=call.id, idem_key=uuid4().hex,
                frozen_action={"name": _INVALID, "arguments": {"handle": req_handle}},
                handle=req_handle,
            )
        # 关键:冻结的是**提案的** action/params(精确、已消歧),非模型重打的参数。
        # idem_key 确定性派生(非 uuid4)→ 重入/重启映同一账本条目,WAL at-most-once 才成立。
        return PendingAction(
            tool_call_id=call.id,
            idem_key=self._idem_key(handle, proposal.action, proposal.params),
            frozen_action={"name": proposal.action, "arguments": dict(proposal.params)},
            handle=handle,
        )

    async def resolve(self, pending: PendingAction, decision: Decision) -> ToolResult:
        name = pending.frozen_action["name"]
        if name == _INVALID:
            bad = pending.frozen_action["arguments"].get("handle")
            return ToolResult(ok=False, content="", error=f"unknown proposal handle: {bad}")

        if decision == "reject":
            self._store.pop(pending.handle)         # 拒绝也清掉提案
            return ToolResult(ok=True, content=f"[rejected] {name} not executed")

        if decision == "approve":
            idem = pending.idem_key
            args = pending.frozen_action["arguments"]
            proposal = self._store.get(pending.handle)  # 取 token + 可逆性(resolve 无 ctx)
            # ── 崩溃恢复优先(只读账本,先于 F3/发射):done→返缓存;in_flight→消解(发没发不确定)──
            existing = await self._ledger_db.get(idem) if self._ledger_db is not None else None
            status = (existing or {}).get("status")
            if status == "done":                        # 真幂等:已执行过 → 返缓存,绝不重发
                self._store.pop(pending.handle)
                return ToolResult(ok=True, content=(existing or {}).get("content", ""))
            if status == "in_flight":                   # 上次发到一半崩了 → 崩溃窗口消解(不盲目重发)
                return await self._resolve_in_flight(idem, proposal)
            # ★门栓 F3(纵深防御):首次执行才到这;不可逆硬拦,绝不下发、也不写账本。
            if proposal is not None and proposal.reversibility != "可逆":
                self._store.pop(pending.handle)
                return ToolResult(ok=False, content="",
                                  error=f"拒绝执行不可逆控制(F3 门栓): {name}")
            # ── 写前账本(WAL):首次 put in_flight;failed(上次发失败)→ 重置重试 ──
            if self._ledger_db is not None:
                if status is None:
                    await self._ledger_db.put_if_absent(idem, "in_flight", {"content": ""})
                else:                                   # "failed"
                    await self._ledger_db.update(idem, "in_flight", {"content": ""})
            elif idem in self._ledger:                  # 回退账本:已执行 → 返缓存
                self._store.pop(pending.handle)
                return self._ledger[idem]
            token = proposal.token if proposal is not None else ""
            # ★真下发可能抛(token 失效/控制接口不通/超时)——必须接住,**不能让异常炸穿确认流**
            #   (否则前端只看到 "network error",看不到真因)。失败如实回 ok=False + 真原因。
            try:
                readback = await self._execute(name, args, token=token)
            except Exception as exc:
                if self._ledger_db is not None:         # 发失败(本进程已知)→ 标 failed,允许后续重试
                    await self._ledger_db.update(idem, "failed", {"content": ""})
                self._store.pop(pending.handle)
                code = getattr(exc, "code", "") or "unknown"
                return ToolResult(ok=False, content="", error=(
                    f"控制下发失败(后端报错 code={code}):{exc}。"
                    f"**把这个真实后端报错原样转告用户**——别臆断成 token 失效(读接口此刻可能正常,失败更可能是"
                    f"控制权限/参数/接口连通问题)。"))
            result = ToolResult(ok=True, content=(
                f"[executed] {name} args={args} (idem={idem}) readback={readback}"))
            if self._ledger_db is not None:
                await self._ledger_db.update(idem, "done", {"content": result.content})  # WAL 第二阶段
            else:
                self._ledger[idem] = result
            self.execute_count += 1
            self._store.pop(pending.handle)         # 执行后清提案(pop-on-resolve,R1 防无界增长)
            return result

        return ToolResult(ok=False, content="", error="unknown decision")

    async def _resolve_in_flight(self, idem: str, proposal) -> ToolResult:
        """上次下发到一半中断(发没发不确定)。不可逆=**绝不自动重发**返状态未知;可逆=提示幂等重试。
        无后端 commandId 下,这是 at-most-once 的核心:宁可不确定,绝不重复下发不可逆控制。"""
        if proposal is None or proposal.reversibility != "可逆":
            return ToolResult(ok=False, content="", error=(
                "控制状态未知(上次下发中断,无法确认是否已生效)——**不可逆控制绝不自动重发**,"
                "请人工核对设备/操作日志后再决定。"))
        return ToolResult(ok=True, content=(
            "控制状态未知(上次下发中断);该控制可逆,可重新发起一次确认幂等重试。"))

    async def _execute(self, name: str, args: dict, *, token: str = "") -> str:
        """真后端:`deviceCtrl` 下发 → `getDevicePage` 读回对账(**已受理 ≠ 已生效**)。
        `backend=None`:echo `"ok"`(单测/无后端回归)。
        ★simulated(默认):**不调 deviceCtrl**——只读回当前态展示,标"[模拟]未真实下发"。"""
        if self._backend is None:
            return "ok"
        if self._execution_mode != "real":          # simulated:绝不真下发(硬依赖:后端无幂等前不上线)
            cur = ""
            try:                                     # 仍读回当前态给用户看(只读,无副作用)
                hits = await self._backend.device_status(token=token or None)
                hit = next((h for h in hits if h.device_id == str(args.get("deviceId", ""))), None)
                if hit is not None:
                    cur = hit.reading_of(str(args.get("paramTypeNo", ""))) or ""
            except Exception:
                cur = ""
            tgt = str(args.get("paramValue", ""))
            msg = "[模拟] 已确认,未真实下发(real 需后端 commandId/幂等)"
            return f"{msg};当前读回={cur}、目标={tgt}" if cur else msg
        if name == "doorControl":              # 门禁走 /through(deviceCtrl 控门是假成功)
            accepted = await self._backend.door_control(payload=dict(args), token=token or None)
        else:
            accepted = await self._backend.device_ctrl(payload=dict(args), token=token or None)
        if not accepted:
            return "accepted=False(后端未受理)"
        # 读回对账:比对**被控参数**的实时读数(pointTypeParamVOList)vs 目标 paramValue。
        # ★顶层 value 是聚合码、非读数(真机实测)——绝不拿它对账(旧 bug:永远 pending)。
        target = str(args.get("paramValue", ""))
        param_no = str(args.get("paramTypeNo", ""))
        device_id = str(args.get("deviceId", ""))
        try:
            hits = await self._backend.device_status(token=token or None)
        except Exception as exc:                    # 读回失败不翻转已受理事实,仅标 effective 未知
            return f"accepted=True effective=unknown(读回失败:{exc}) target={target}"
        hit = next((h for h in hits if h.device_id == device_id),
                   hits[0] if len(hits) == 1 else None)
        if hit is None:
            return f"accepted=True effective=unknown(无设备读回) target={target}"
        if "在线" not in (hit.status or "") and hit.status:
            return f"accepted=True effective=False(设备{hit.status},已受理未生效)"
        reading = hit.reading_of(param_no)          # 被控参数的实时读数
        if reading is None:                         # 设定值型常不在读数列表(读回的是测量量)→ 诚实标无法即时核
            return f"accepted=True effective=unknown(该参数无即时读回,状态型稍后生效) target={target}"
        if target and str(target) == str(reading):
            return f"accepted=True effective=True {param_no}读回={reading}"
        return f"accepted=True effective=pending(已受理,{param_no}读回 {reading}≠目标 {target})"
