from __future__ import annotations

from typing import Literal, Protocol
from uuid import uuid4

from .messages import ToolCallReq
from .pending import PendingAction
from .tools import ToolResult

Decision = Literal["approve", "reject"]


class ControlCapability(Protocol):
    """控制能力子系统:冻结 + 确认后执行。承载幂等(后端 deviceCtrl 缺幂等键,此处桩实现)。"""

    def freeze(self, call: ToolCallReq, thread_id: str = "") -> PendingAction: ...

    async def resolve(self, pending: PendingAction, decision: Decision) -> ToolResult: ...


class FakeControlCapability:
    """桩实现:模拟 Postgres idem_key 唯一约束的幂等语义。
    用于测试与本地开发;生产实现替换 resolve 内部 HTTP 调用即可,幂等接口不变。"""

    def __init__(self) -> None:
        # 模拟 Postgres idem_key 唯一约束:每个 idem_key 只入库一次
        self._ledger: dict[str, ToolResult] = {}
        # 真实执行次数(测试用):幂等重入不应增加
        self.execute_count: int = 0

    def freeze(self, call: ToolCallReq, thread_id: str = "") -> PendingAction:
        """铸造 PendingAction:每次调用产生全新 idem_key,args 深拷贝防外部篡改。
        (桩无提案存储,thread_id 仅为协议一致;真实现 ProposalControlCapability 按会话取提案。)"""
        idem_key = uuid4().hex
        frozen_action = {"name": call.name, "arguments": dict(call.arguments)}
        return PendingAction(
            tool_call_id=call.id,
            idem_key=idem_key,
            frozen_action=frozen_action,
            handle=None,
        )

    async def resolve(self, pending: PendingAction, decision: Decision) -> ToolResult:
        """执行冻结动作或拒绝它。
        approve 路径:幂等键已存在则返回缓存结果(不重发);否则执行并入库。
        reject 路径:返回拒绝结果,不写入 ledger(保留 idem_key 可复用空间)。
        """
        if decision == "reject":
            name = pending.frozen_action["name"]
            return ToolResult(ok=True, content=f"[rejected] {name} not executed")

        if decision == "approve":
            # 幂等检查:idem_key 已在 ledger 中 → 直接返回缓存,不重复执行
            if pending.idem_key in self._ledger:
                return self._ledger[pending.idem_key]

            # 首次执行:调用后端(此处桩实现为 echo)并写入 ledger
            name = pending.frozen_action["name"]
            arguments = pending.frozen_action["arguments"]
            idem_key = pending.idem_key
            result = ToolResult(
                ok=True,
                content=(
                    f"[executed] {name} args={arguments} "
                    f"(idem={idem_key}) readback=ok"
                ),
            )
            self._ledger[idem_key] = result
            self.execute_count += 1
            return result

        # 防御:未知 decision
        return ToolResult(ok=False, content="", error="unknown decision")
