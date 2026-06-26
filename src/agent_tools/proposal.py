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

import json
from dataclasses import asdict, dataclass, field, replace
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
    thread_id: str = ""                               # 会话归属:execute_proposal 取"最近一条"须按会话切片,
                                                      #   否则多用户下取到别人提案=串提案事故(latest_for)


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

    def latest_for(self, thread_id: str) -> tuple[str, ControlProposal] | tuple[None, None]:
        """该**会话**最近一条未消解提案。无 → (None, None)——**绝不回落到别会话**的提案
        (堵跨用户串提案:execute_proposal 不带 handle 时按此取,而非全局 items()[-1])。"""
        for h, p in reversed(list(self._store.items())):
            if p.thread_id == thread_id:
                return h, p
        return None, None


class RedisProposalStore:
    """提案的 **Redis 外置**实现(同接口替 ProposalStore)——多实例共享 + 跨重启不丢提案,
    补全 P4 跨重启 at-most-once(配合 idem 账本)。控制提案低频(人工确认),用**同步** redis
    客户端不动现有 async 链;偶尔 ~1ms 阻塞可接受。键:
      `{ns}:p:{handle}` = 提案 JSON(TTL);`{ns}:idx` = 全 handle 集(items 用);
      `{ns}:thr:{thread_id}` = 该会话 handle 有序表(latest_for 用)。
    `client` 可注入(测试用假 redis);None 时按 url 延迟建真客户端。"""

    def __init__(self, *, url: str | None = None, ns: str = "proposal",
                 ttl_seconds: int = 3600, client: Any | None = None) -> None:
        self._url = url or "redis://localhost:6379/0"
        self._ns = ns
        self._ttl = ttl_seconds
        self._client = client

    def _r(self):
        if self._client is None:
            import redis  # 仅用时导入(同步客户端;低频控制提案,不阻塞 async 热路径)
            self._client = redis.Redis.from_url(self._url, decode_responses=True)
        return self._client

    def put(self, proposal: ControlProposal) -> str:
        handle = proposal.handle or uuid4().hex
        stored = replace(proposal, handle=handle, params=dict(proposal.params))
        r = self._r()
        r.set(f"{self._ns}:p:{handle}", json.dumps(asdict(stored), ensure_ascii=False), ex=self._ttl)
        r.sadd(f"{self._ns}:idx", handle)
        r.rpush(f"{self._ns}:thr:{stored.thread_id}", handle)
        return handle

    def _load(self, handle: str) -> ControlProposal | None:
        raw = self._r().get(f"{self._ns}:p:{handle}")
        return ControlProposal(**json.loads(raw)) if raw else None

    def get(self, handle: str) -> ControlProposal | None:
        return self._load(handle)

    def pop(self, handle: str) -> ControlProposal | None:
        p = self._load(handle)
        r = self._r()
        r.delete(f"{self._ns}:p:{handle}")
        r.srem(f"{self._ns}:idx", handle)
        if p is not None:
            r.lrem(f"{self._ns}:thr:{p.thread_id}", 0, handle)
        return p

    def items(self) -> list[tuple[str, ControlProposal]]:
        out: list[tuple[str, ControlProposal]] = []
        r = self._r()
        for handle in r.smembers(f"{self._ns}:idx"):
            p = self._load(handle)
            if p is None:                       # TTL 过期/已 pop → 顺手清索引(惰性)
                r.srem(f"{self._ns}:idx", handle)
            else:
                out.append((handle, p))
        return out

    def latest_for(self, thread_id: str) -> tuple[str, ControlProposal] | tuple[None, None]:
        r = self._r()
        key = f"{self._ns}:thr:{thread_id}"
        for handle in reversed(r.lrange(key, 0, -1)):
            p = self._load(handle)
            if p is not None:
                return handle, p
            r.lrem(key, 0, handle)              # 陈旧(TTL过期/已pop未清)→ 顺手清,防 thread 列表无界增长
        return None, None
