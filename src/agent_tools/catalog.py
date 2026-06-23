"""工具治理注册表(设计 v4 §五)—— 工具管理子系统的地基。

M3:**选择可靠性靠组织结构(分组/分层/隔离/治理)根治,不靠把描述写好。** 注册表是**带治理元数据
的扁平目录**,登记**全部工具(顶层/agent/叶子,统一治理,不分特例)**。

**v4 极瘦元数据**(守"无消费者不留"):
- `tool`:引擎契约(name/desc/params/handler/**is_control**)。
- `capability_code`:**每工具显式声明的权限码**——gate 调用前判 `∈ principal.permissions` 否则 deny。
- `output_budget`:暂留(设计移交中圈,本期不破坏现有读工具截断)。
- **两轴正交**:`capability_code`(谁能用)⊥ `is_control`(用了要不要确认)。例 propose_control:
  is_control=False(不弹确认)+ capability_code=device:control(起草控制也要控制权)。
- 组织(哪个 agent 装哪些叶子)归 **toolset 名单**(组合根/agent sub_config),不是元数据。
"""
from __future__ import annotations

from dataclasses import dataclass, replace as _dc_replace

from agent_loop.tools import LoopTool, LoopToolRegistry, OutputBudget


@dataclass(frozen=True)
class ToolSpec:
    """工具 + 治理元数据(v4 极瘦)。注册表持有它;执行时把内裹的 `tool` 交引擎。"""

    tool: LoopTool                          # 引擎契约:name/desc/params/handler/is_control
    capability_code: str                    # ★需要的权限码(显式,不继承);gate deny-first 判它
    output_budget: int | None = None        # 输出预算(暂留;设计移交中圈)

    @property
    def name(self) -> str:
        return self.tool.name

    @property
    def is_control(self) -> bool:
        return self.tool.is_control          # 读/控分叉以引擎契约为准(is_control 即真相)


class ToolCatalog:
    """治理注册表:登记带元数据的工具 + 按元数据查询 + 产出引擎执行注册表。"""

    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}

    # ── 登记 ──────────────────────────────────────────────────────────────────
    def register(self, spec: ToolSpec) -> None:
        self._specs[spec.name] = spec

    # ── 查询(可见性/路由/输出治理的共同地基) ─────────────────────────────────
    def spec(self, name: str) -> ToolSpec:
        return self._specs[name]

    def find(self, name: str) -> "ToolSpec | None":
        return self._specs.get(name)

    def all(self) -> list[ToolSpec]:
        return list(self._specs.values())

    def names(self) -> list[str]:
        return list(self._specs)

    # ── 桥到引擎 ───────────────────────────────────────────────────────────────
    def to_registry(self, names: list[str] | None = None) -> LoopToolRegistry:
        """产出引擎 `LoopToolRegistry`(执行用):注册选中 spec 的(可能带输出预算的)`LoopTool`。
        默认登记全部(均可按名执行);"模型看到哪些"是 toolset 选择,与此正交。"""
        reg = LoopToolRegistry()
        for name in (names if names is not None else self._specs):
            spec = self._specs.get(name)
            if spec is not None:
                reg.register(self._engine_tool(spec))
        return reg

    @staticmethod
    def _engine_tool(spec: "ToolSpec") -> LoopTool:
        """把 spec 的 `output_budget` 接进引擎 `LoopTool.output_budget`(executor 认这个 seam)。
        **控制类不静默截**(读回/确认文本须完整)→ is_control 跳过;工具已自带预算则不覆盖。"""
        if (spec.output_budget is not None and not spec.is_control
                and spec.tool.output_budget is None):
            return _dc_replace(spec.tool, output_budget=OutputBudget(max_chars=spec.output_budget))
        return spec.tool
