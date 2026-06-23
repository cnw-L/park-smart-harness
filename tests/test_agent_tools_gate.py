"""V3:CatalogGate —— **deny-first**(未登记→deny / 缺权限→deny)+ 控制 ask;capability_code ⊥ is_control。"""
from __future__ import annotations

import asyncio

import httpx

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget
from agent_loop.llm import FakeModelCaller
from agent_loop.messages import ToolCallReq
from agent_loop.tools import LoopTool, ToolContext

from agent_context.principal import Principal

from agent_tools.backend import FakeBackendClient, ProdApiBackendClient
from agent_tools.catalog import ToolCatalog, ToolSpec
from agent_tools.composition import build_tool_subsystem
from agent_tools.gate import CatalogGate


def _tool(name: str, is_control: bool = False) -> LoopTool:
    async def h(args, ctx):  # pragma: no cover
        ...
    return LoopTool(name=name, description="d",
                    parameters={"type": "object", "properties": {}}, handler=h,
                    is_control=is_control)


def _spec(name, *, is_control=False, capability_code="x:read"):
    return ToolSpec(tool=_tool(name, is_control), capability_code=capability_code)


def _ctx(perms=(), *, none=False):
    p = None if none else Principal(id="u", name="x", role="员工", permissions=tuple(perms))
    return ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=5)), depth=0, principal=p)


def _call(name):
    return ToolCallReq(id="c", name=name, arguments={})


def test_deny_first_unknown_name():
    """★deny-first:未登记的名 → deny(幻觉/漏登都拒,无放行的缝)。"""
    g = CatalogGate(ToolCatalog())
    assert g.classify(_call("device_status"), _tool("device_status"), _ctx(["x:read"])) == "deny"


def test_permission_deny_and_allow():
    cat = ToolCatalog(); cat.register(_spec("facility", capability_code="device:read"))
    g = CatalogGate(cat); t = cat.find("facility").tool
    assert g.classify(_call("facility"), t, _ctx(["device:read"])) == "allow"
    assert g.classify(_call("facility"), t, _ctx([])) == "deny"
    assert g.classify(_call("facility"), t, _ctx(none=True)) == "deny"      # principal None→最小权限


def test_control_ask_unless_no_permission():
    cat = ToolCatalog(); cat.register(_spec("exec", is_control=True, capability_code="device:control"))
    g = CatalogGate(cat); t = cat.find("exec").tool
    assert g.classify(_call("exec"), t, _ctx(["device:control"])) == "ask"  # 有权限+控制→确认
    assert g.classify(_call("exec"), t, _ctx([])) == "deny"                 # 无权限→deny(压过 ask)


def test_propose_control_needs_control_code():
    """★正交:propose_control 非控制(不弹确认)但要 device:control;device:read 用户被 deny。"""
    cat = ToolCatalog(); cat.register(_spec("propose_control", is_control=False, capability_code="device:control"))
    g = CatalogGate(cat); t = cat.find("propose_control").tool
    assert g.classify(_call("propose_control"), t, _ctx(["device:control"])) == "allow"
    assert g.classify(_call("propose_control"), t, _ctx(["device:read"])) == "deny"


def test_subsystem_gate_on_real_specs():
    sub = build_tool_subsystem(model_caller=FakeModelCaller([]))
    g = sub.gate
    fac, ep = sub.registry.get("facility_agent"), sub.registry.get("execute_proposal")
    assert g.classify(_call("facility_agent"), fac, _ctx(["device:read"])) == "allow"
    assert g.classify(_call("facility_agent"), fac, _ctx([])) == "deny"
    assert g.classify(_call("execute_proposal"), ep, _ctx(["device:control"])) == "ask"
    assert g.classify(_call("execute_proposal"), ep, _ctx([])) == "deny"


def test_principal_permissions_field():
    assert Principal(id="u", name="x", role="员工", permissions=("a", "b")).permissions == ("a", "b")


def test_fake_user_info():
    assert asyncio.run(FakeBackendClient(permissions=("device:read",))
                       .user_info(username="admin", park_id=1)) == ("device:read",)


def test_prodapi_user_info_capability_only_not_device():
    """V5:user_info 只返**能力级**(permissions+apiPermissions);devicePermission 是资源级、不混入。"""
    def handler(req):
        assert req.url.path.endswith("/user/info/admin/1")
        return httpx.Response(200, json={"code": 0, "data": {
            "permissions": ["p1"], "apiPermissions": ["api1"], "devicePermission": ["dev:x"]}})
    c = ProdApiBackendClient(base_url="http://x/prod-api/project", bearer_token="t")
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    perms = asyncio.run(c.user_info(username="admin", park_id=1))
    assert "p1" in perms and "api1" in perms
    assert "dev:x" not in perms                          # ★资源级不混入能力级
