"""组合根(运行链):把全部工具(顶层 + agent 叶子)登记成**扁平 `ToolCatalog`**,派生引擎
registry + 顶层 toolset + deny-first `CatalogGate` + 控制能力。**完整串联见 `runtime.py`**(再叠登录链)。

主模型顶层(功能命名,8):**设备管理 facility_agent(子) / 运行查询 record_query(扁平) / 生活服务
meeting·parking·restaurant_query / 知识检索 knowledge_query / 执行工具 propose_control·execute_proposal**。
record_query 是扁平工具(单一工具不够格当子 agent:无可组织、返回计数短表无需隔离),主自己编排多 kind 综合。

- 统一治理:facility 叶子(device_status/propose_control/…)+ 顶层工具进同一 catalog、受同一 gate;
  组织(facility_agent 装哪些叶子)归 `FACILITY_LEAVES` toolset 名单,不是元数据。
- 极瘦元数据:`ToolSpec = capability_code ⊥ is_control`(见 catalog.py)。
- R1:**一个 ProposalStore 单例**同时给 agent 子里的 `propose_control` 和父侧 `ProposalControlCapability`。
"""
from __future__ import annotations

from dataclasses import dataclass

from agent_loop.llm import ModelCaller
from agent_loop.tools import LoopToolRegistry

from .backend import BackendClient, FakeBackendClient
from .catalog import ToolCatalog, ToolSpec
from .gate import CatalogGate
from .grounding import DEFAULT_REVERSIBILITY_MAP
from .domains.facility import FACILITY_LEAVES, build_facility_agent, facility_leaf_specs
from .domains.knowledge import make_knowledge_query_tool
from .domains.life import (make_meeting_query_tool, make_parking_query_tool,
                           make_restaurant_query_tool)
from .domains.records import make_record_query_tool
from .execute_proposal import make_execute_proposal_tool
from .proposal import ProposalStore
from .proposal_control import ProposalControlCapability


# 主模型顶层工具名单(组织,非元数据)。叶子(FACILITY_LEAVES)在 catalog 里、不在顶层。
# ★propose_control 多归属:既是 facility_agent 叶子(诊断流程里附带提案),也升主顶层——简单控制
# (调温/开关)主模型直接 propose,不绕子 agent(工具子系统设计 §四:单次确定动作=flat)。
# ★record_query 扁平化:运行事项只一个工具,无可"组织"、返回是计数短表无需隔离 → 不够格当子 agent
# (Agent-as-Tool=用组织对抗规模);主用 plan 直接编排(查工单+查告警由主多次调用+汇总)。
TOP_TOOLS = ("facility_agent", "record_query", "meeting_query", "parking_query",
             "restaurant_query", "knowledge_query", "propose_control", "execute_proposal")


@dataclass
class ToolSubsystem:
    catalog: ToolCatalog                 # 扁平治理注册表(顶层 + 叶子,统一治理)
    registry: LoopToolRegistry           # 引擎执行注册表(从 catalog 派生)
    toolset: list[str]                   # 主模型顶层可见(未按权限过滤;ToolLoader 在登录后过滤)
    control: ProposalControlCapability   # 注入 run_loop(control=...)
    gate: CatalogGate                    # 注入 run_loop(gate=...);deny-first + 控制 ask
    store: ProposalStore                 # 单例(暴露给 demo/测试)


def build_tool_subsystem(*, model_caller: ModelCaller, backend: BackendClient | None = None,
                         reversibility_map: dict | None = None, retriever=None,
                         assembler=None, execution_mode: str = "simulated") -> ToolSubsystem:
    store = ProposalStore()              # 单例 —— 子的 propose_control 与父侧 control 共享
    backend = backend or FakeBackendClient()   # 默认假后端;接真传 ProdApiBackendClient
    reversibility_map = reversibility_map if reversibility_map is not None else DEFAULT_REVERSIBILITY_MAP

    catalog = ToolCatalog()
    gate = CatalogGate(catalog)          # 先建:引用 catalog 对象、运行时查,注册顺序无关

    # ── facility 域叶子先进同一 catalog(统一治理),子 registry 从 catalog 派生 + gate 下沉 ──
    for spec in facility_leaf_specs(backend=backend, store=store, reversibility_map=reversibility_map):
        catalog.register(spec)
    facility_tool = build_facility_agent(
        model_caller=model_caller, leaf_registry=catalog.to_registry(list(FACILITY_LEAVES)),
        gate=gate, assembler=assembler)

    # ── 顶层工具;读工具给保守输出预算,execute_proposal 不设(控制结果不静默截) ──
    catalog.register(ToolSpec(tool=facility_tool, capability_code="device:read", output_budget=2000))
    # record_query 扁平在顶层(非子 agent):主直接调,多 kind 综合由主编排
    catalog.register(ToolSpec(tool=make_record_query_tool(backend), capability_code="record:read", output_budget=2000))
    catalog.register(ToolSpec(tool=make_meeting_query_tool(), capability_code="life:read", output_budget=1200))
    catalog.register(ToolSpec(tool=make_parking_query_tool(), capability_code="life:read", output_budget=1200))
    catalog.register(ToolSpec(tool=make_restaurant_query_tool(), capability_code="life:read", output_budget=1200))
    catalog.register(ToolSpec(tool=make_knowledge_query_tool(retriever), capability_code="knowledge:read", output_budget=1500))
    catalog.register(ToolSpec(tool=make_execute_proposal_tool(), capability_code="device:control"))

    return ToolSubsystem(
        catalog=catalog,
        registry=catalog.to_registry(),     # 全部(顶层+叶子)可执行
        toolset=list(TOP_TOOLS),            # 主模型顶层(8);按权限过滤由 ToolLoader 在登录后做
        control=ProposalControlCapability(store, backend=backend, execution_mode=execution_mode),
        gate=gate,
        store=store,
    )
