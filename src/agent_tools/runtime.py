"""主串联(composition root)—— 把工具管理子系统的所有组件接成一个可用运行时。

设计 §三 两条链一处串起:

    build_park_runtime(...) → ParkToolRuntime
      ├─ 运行链(治理):build_tool_subsystem → ToolSubsystem
      │     扁平 ToolCatalog + 引擎 registry + 顶层 toolset + deny-first CatalogGate
      │     + ProposalControlCapability + ProposalStore 单例
      │     (内含:设备管理/运行管理 两子 agent + 生活×3/知识 flat + execute_proposal;
      │      防腐 BackendClient + 知识 KnowledgeRetriever)
      └─ 登录链(确权):.login(...) 一次确权
            后端 user_info(能力码) → PermissionMapper(RuoYi→harness 码)
            → resolve_capabilities(叠 OrgPolicy) → 冻进 Principal.permissions
         + .toolset_for(principal):ToolLoader 按有效能力集过滤顶层(可见性减选择)

run_loop 接线(主会话每轮):
    conv.principal      = await rt.login(username=…, park_id=…, role_key=…, token=…)
    cfg.toolset         = rt.toolset_for(principal)          # 按权限加载
    run_loop(cfg, conv, rt.subsystem.registry, …,
             gate=rt.subsystem.gate, control=rt.subsystem.control)

身份自动从 ctx.principal 读、LLM 不传;deny-first 闸纵深兜底;真 deviceCtrl 只经人工确认。
"""
from __future__ import annotations

from dataclasses import dataclass

from agent_context.principal import Principal
from agent_loop.llm import ModelCaller

from .backend import BackendClient, BackendError, FakeBackendClient
from .composition import ToolSubsystem, build_tool_subsystem
from .identity import IdentityMapper, OrgPolicy, PermissionMapper, resolve_capabilities
from .loader import select_toolset


@dataclass
class ParkToolRuntime:
    """子系统运行时门面:握运行链(subsystem)+ 登录链组件(backend/mapper/org_policy)。"""

    subsystem: ToolSubsystem            # 运行链:catalog/registry/toolset/gate/control/store
    backend: BackendClient              # 权限来源 + 防腐数据底座
    mapper: PermissionMapper            # 后端 RuoYi 码 → harness 能力码(默认直通)
    org_policy: OrgPolicy | None        # org 策略(按 roleKey 强制收紧);None=不收紧

    async def login(self, *, username: str, park_id: str | int, role_key: str = "",
                    token: str | None = None, name: str = "", dept: str = "",
                    koujing: str = "") -> Principal:
        """登录确权一次:后端能力码 → 映射 → 叠 org 策略 → 冻进 Principal(会话级快照)。

        身份脊柱:`token` 透传给后端做数据级过滤;`permissions` 喂 gate/loader 判能力级。
        改权限须**重新登录**(快照),后端是写的最终权威(纵深防御)。

        ★fail-safe:后端 user_info 失败(如真机 /user/info 当前 404、网络抖)→ **不抛、降级成
        空能力集 Principal**(身份不可信 → 一个工具都看不到/调不动,deny-first 的安全降级),
        且不让一次后端故障把整个会话打崩。能力级取不到时数据级仍随 token 走后端。
        """
        try:
            raw = await self.backend.user_info(username=username, park_id=park_id, token=token)
        except BackendError:
            raw = ()                                    # 身份不可信 → 空能力集(最小权限)
        caps = resolve_capabilities(raw, role_key, mapper=self.mapper, org_policy=self.org_policy)
        return Principal(id=username, name=name or username, role=role_key, dept=dept,
                         koujing=koujing, token=token, permissions=caps)

    def toolset_for(self, principal: Principal) -> list[str]:
        """ToolLoader:按 principal 有效能力集过滤顶层 toolset(可见性 = 减选择 + 第一道安全)。"""
        return select_toolset(self.subsystem.catalog, self.subsystem.toolset,
                              principal.permissions)


def build_park_runtime(*, model_caller: ModelCaller, backend: BackendClient | None = None,
                       retriever=None, reversibility_map: dict | None = None, assembler=None,
                       mapper: PermissionMapper | None = None,
                       org_policy: OrgPolicy | None = None,
                       execution_mode: str = "simulated") -> ParkToolRuntime:
    """一处建好整个子系统:运行链(build_tool_subsystem)+ 登录链组件。

    - `backend`:配 prod-api 传 `ProdApiBackendClient.from_env()`,否则 `FakeBackendClient`(离线 demo/测)。
    - `retriever`:知识真检索(harness_rag 适配器);None → 工具内默认 Fake。
    - `mapper`/`org_policy`:登录链可插拔——真权限码样例到了填 `TableMapper`、org 口径定了填 `OrgPolicy`。
    - `execution_mode`:控制执行模式;默认 `simulated`(不真下发 deviceCtrl,硬依赖未就绪前的安全缺省),
      `real` 显式开(后端 commandId/幂等就绪后)。
    """
    backend = backend or FakeBackendClient()
    subsystem = build_tool_subsystem(model_caller=model_caller, backend=backend,
                                     retriever=retriever, reversibility_map=reversibility_map,
                                     assembler=assembler, execution_mode=execution_mode)
    return ParkToolRuntime(subsystem=subsystem, backend=backend,
                           mapper=mapper or IdentityMapper(), org_policy=org_policy)
