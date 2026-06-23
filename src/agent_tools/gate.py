"""治理闸 `CatalogGate` —— 逐调用判 allow / deny / ask,吃 catalog 元数据 + principal 权限。

实现 `agent_loop.gate.Gate` 协议(`classify(call, tool, ctx)`),组合根注入 `run_loop(gate=)`,
并由组合根**下沉同一闸到子 loop**(统一治理:顶层/叶子同等受查)。

**deny-first(v4):缺省不信任。**
1. **未登记**(`catalog.find` 为 None)→ **deny**:合法工具一律进 catalog;调到没登记的名 = 幻觉/漏登,拒。
2. **权限不足**:`spec.capability_code` ∉ `principal.permissions` → deny(deny 压过 ask)。
   身份从 `ctx.principal` 自动读、**LLM 不传**;`principal=None`/无权限 → deny(最小权限)。
3. **控制**:`tool.is_control` → ask(确认闸)。
4. 其余 → allow。

安全靠**调用时 deny**(loop 的 deny→`[blocked]` 合成→继续,模型看得见改策略),叠加登录时
ToolLoader 按权限加载(可见性)。两层:加载层减选择 + 第一道,deny 闸纵深兜底。

★集成方契约(footgun):deny-first 下**任何可被模型调用的工具(含引擎元工具如 plan)都必须登记进
catalog 并配 capability_code**,否则被当"未登记"拒掉。组织(哪个 loop 暴露哪些)归 toolset 名单,
但治理(进 catalog)无例外。
"""
from __future__ import annotations

from agent_loop.gate import Verdict
from agent_loop.messages import ToolCallReq
from agent_loop.tools import LoopTool, ToolContext

from .catalog import ToolCatalog


class CatalogGate:
    def __init__(self, catalog: ToolCatalog) -> None:
        self._catalog = catalog

    def classify(self, call: ToolCallReq, tool: LoopTool, ctx: ToolContext) -> Verdict:
        spec = self._catalog.find(call.name)
        if spec is None:
            return "deny"                        # ① 未登记 → deny(deny-first,无"放行"的缝)
        perms = getattr(getattr(ctx, "principal", None), "permissions", None) or ()
        if spec.capability_code not in perms:
            return "deny"                        # ② 权限不足 → deny(压过 ask)
        if tool.is_control:
            return "ask"                         # ③ 控制 → 确认
        return "allow"                           # ④ 准入只读
