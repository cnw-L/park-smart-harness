"""`ProposalControlCapability` —— 实现 agent_loop 的 `ControlCapability` 协议。

M2-refined 的落点:`execute_proposal(handle)` 被 gate 判 `ask` → loop 调本类 `freeze`。
`freeze` 据 handle 从 `ProposalStore` 还原**提案的精确动作**,冻成 `PendingAction`
(`frozen_action` = 提案的 action/params,**不是** `execute_proposal(handle=…)` 这层调用)——
即"控制参数从提案取、模型绝不重打"。`resolve` 抄 `FakeControlCapability` 的幂等账本语义。

零 loop 改动:它就是个 `ControlCapability`,组合根把它当 `control=` 注入 run_loop 即可。
"""
from __future__ import annotations

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
                 execution_mode: str = "simulated") -> None:
        self._store = store
        self._backend = backend
        # ★默认 simulated:不真下发 deviceCtrl(内圈定稿 §八硬依赖:后端无 commandId/幂等前不可逆控制
        #   不能上线)。real 显式开,且只在后端幂等就绪后。
        self._execution_mode = execution_mode
        self._ledger: dict[str, ToolResult] = {}   # 幂等:idem_key→结果,重入不重发
        self.execute_count: int = 0

    def freeze(self, call: ToolCallReq) -> PendingAction:
        """还原提案 → 冻结精确动作。★handle 不经模型:留空 = 取**最近一条未消解提案**(模态门保证同时
        只一条 pending,无歧义)。未知/无提案不抛(loop 无 try),铸哨兵。"""
        handle = str(call.arguments.get("handle", ""))
        proposal = self._store.get(handle) if handle else None
        if proposal is None:                       # 无 handle、或模型乱填的 handle 不在 store → 取最近一条
            items = self._store.items()             # (模态门保证同时只一条 pending;彻底中和"抄错/编造 handle")
            if items:
                handle, proposal = items[-1]
        if proposal is None:                       # store 真空(从没登记过提案)→ 哨兵 → demo 友好卡
            return PendingAction(
                tool_call_id=call.id, idem_key=uuid4().hex,
                frozen_action={"name": _INVALID, "arguments": {"handle": handle}},
                handle=handle,
            )
        # 关键:冻结的是**提案的** action/params(精确、已消歧),非模型重打的参数
        return PendingAction(
            tool_call_id=call.id, idem_key=uuid4().hex,
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
            if pending.idem_key in self._ledger:    # 幂等:已执行过 → 返缓存,不重发
                return self._ledger[pending.idem_key]
            args = pending.frozen_action["arguments"]
            proposal = self._store.get(pending.handle)  # 取 token + 可逆性(resolve 无 ctx)
            # ★门栓 F3(纵深防御):发射前重断言可逆。不可逆本应在 grounding 当场被拒、到不了这,
            #   但执行端独立再断一道——任何旁路让不可逆动作走到这,这里硬拦,绝不下发。
            if proposal is not None and proposal.reversibility != "可逆":
                self._store.pop(pending.handle)
                return ToolResult(ok=False, content="",
                                  error=f"拒绝执行不可逆控制(F3 门栓): {name}")
            token = proposal.token if proposal is not None else ""
            readback = await self._execute(name, args, token=token)
            result = ToolResult(ok=True, content=(
                f"[executed] {name} args={args} (idem={pending.idem_key}) readback={readback}"))
            self._ledger[pending.idem_key] = result
            self.execute_count += 1
            self._store.pop(pending.handle)         # 执行后清提案(pop-on-resolve,R1 防无界增长)
            return result

        return ToolResult(ok=False, content="", error="unknown decision")

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
