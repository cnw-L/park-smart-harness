"""控制提案(M2-refined 的核心数据)。

子 agent 只读;当某步需要控制时,它产出一个 `ControlProposal`(**已消歧的精确动作** + 人话
说明),写进 `ProposalStore`、把 `handle` 随结果文本回报主会话。主模型调 `execute_proposal(handle)`
触发,harness 据 handle 还原出精确动作 freeze 成 PendingAction(参数从提案取、**模型绝不重打**)。

`ControlProposal` 形状镜像 assistant_core 的 `ControlTicket`(target/action/risk/requires_confirmation),
但**不 import**(防腐层:保 agent_tools 独立于 assistant_core)。`risk` 取值对齐 `CapabilityRisk`。

R1(设计稿):子 agent 隔离、只有 `final` 文本回父 → proposal 对象过不来,只能传 string handle;
故 `ProposalStore` 由组合根做**单例**,两侧(子里的 propose_control / 父侧 ProposalControlCapability)
共享同一实例。v1 用内存 dict 当假后端。
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal
from uuid import uuid4

# 对齐 capability_platform 的 CapabilityRisk(read/draft/ticket/execute/forbidden)。
# v1 闸只认二元(is_control→ask);risk 在此**只作描述字段**(供确认 UI 显示),不驱动闸。
ProposalRisk = Literal["read", "draft", "ticket", "execute", "forbidden"]


@dataclass(frozen=True)
class ControlProposal:
    """子 agent 产出的一次控制提案:精确到可直接执行的动作。"""

    target: str                                       # 已解析的目标(如具体设备,非"3号楼空调"泛指)
    action: str                                       # 控制动作名 = freeze 后的 frozen_action["name"]
    params: dict[str, Any] = field(default_factory=dict)  # 精确参数 = freeze 后的 arguments(grounded:deviceCtrl payload)
    risk: ProposalRisk = "ticket"
    human: str = ""                                   # 给用户/模型看的人话描述
    requires_confirmation: bool = True
    handle: str = ""                                  # 由 ProposalStore.put 分配
    reversibility: str = "可逆"                        # grounding 定;P5 _execute 发射前重断言(F3 纵深防御)
    token: str = ""                                   # propose 时存(resolve 无 ctx);P5 下发用


class ProposalStore:
    """提案的进程内单例存储(v1 假后端)。handle = uuid,跨会话天然防串。"""

    def __init__(self) -> None:
        self._store: dict[str, ControlProposal] = {}

    def put(self, proposal: ControlProposal) -> str:
        """登记提案,返回 handle。params 防御拷贝(外部事后改原 dict 不影响已存)。"""
        handle = proposal.handle or uuid4().hex
        stored = replace(proposal, handle=handle, params=dict(proposal.params))
        self._store[handle] = stored
        return handle

    def get(self, handle: str) -> ControlProposal | None:
        return self._store.get(handle)

    def pop(self, handle: str) -> ControlProposal | None:
        """取出并移除(resolve 后调用,防无界增长)。"""
        return self._store.pop(handle, None)

    def items(self) -> list[tuple[str, ControlProposal]]:
        """当前未消解的提案 [(handle, proposal)],按登记顺序。供 demo 检测"登记了但没执行"。"""
        return list(self._store.items())
