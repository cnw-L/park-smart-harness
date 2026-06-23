"""主串联 runtime —— 登录链(后端权限→映射→org策略→Principal)+ ToolLoader 端到端。"""
from __future__ import annotations

import asyncio

from agent_loop.llm import FakeModelCaller

from agent_tools.backend import FakeBackendClient
from agent_tools.identity import OrgPolicy, TableMapper
from agent_tools.runtime import build_park_runtime


def test_runtime_login_resolves_principal_and_filters_toolset():
    rt = build_park_runtime(model_caller=FakeModelCaller([]), backend=FakeBackendClient(
        permissions=("device:read", "record:read", "life:read", "knowledge:read")))   # 无 control
    p = asyncio.run(rt.login(username="zhang", park_id=1, role_key="员工", token="tk"))
    assert p.token == "tk" and "device:read" in p.permissions
    loaded = rt.toolset_for(p)
    # 无 device:control → execute_proposal 不加载;读权限齐 → 设备/运行/生活/知识在
    assert "execute_proposal" not in loaded
    assert {"facility_agent", "records_agent", "knowledge_query"} <= set(loaded)


def test_runtime_org_policy_strips_control_at_login():
    """org 策略:访客角色登录时强制去 device:control → 看不到执行工具。"""
    rt = build_park_runtime(model_caller=FakeModelCaller([]), backend=FakeBackendClient(),  # 默认含 control
                            org_policy=OrgPolicy(deny_by_role={"访客": ("device:control",)}))
    p = asyncio.run(rt.login(username="guest", park_id=1, role_key="访客", token="t"))
    assert "device:control" not in p.permissions
    assert "execute_proposal" not in rt.toolset_for(p)


def test_runtime_mapper_translates_backend_codes():
    """PermissionMapper:后端真码 → harness 能力码;只 device:read → 只加载设备管理。"""
    rt = build_park_runtime(model_caller=FakeModelCaller([]),
                            backend=FakeBackendClient(permissions=("sys:dev:list",)),
                            mapper=TableMapper({"sys:dev:list": "device:read"}))
    p = asyncio.run(rt.login(username="u", park_id=1))
    assert p.permissions == ("device:read",)
    assert rt.toolset_for(p) == ["facility_agent"]


def test_runtime_login_failsafe_on_user_info_error():
    """★fail-safe:后端 user_info 失败(真机 /user/info 当前 404)→ 不抛、降级空能力集 → 零工具。"""
    from agent_tools.backend import BackendError

    class _BoomBackend(FakeBackendClient):
        async def user_info(self, *, username, park_id, token=None):
            raise BackendError("/user/info 404")

    rt = build_park_runtime(model_caller=FakeModelCaller([]), backend=_BoomBackend())
    p = asyncio.run(rt.login(username="x", park_id=1, token="t"))
    assert p.permissions == () and rt.toolset_for(p) == []   # 身份不可信 → deny-first 零工具


def test_runtime_exposes_subsystem_for_run_loop():
    rt = build_park_runtime(model_caller=FakeModelCaller([]))
    assert rt.subsystem.gate is not None and rt.subsystem.control is not None
    assert rt.subsystem.registry.get("execute_proposal").name == "execute_proposal"
