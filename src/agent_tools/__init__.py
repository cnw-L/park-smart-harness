"""工具治理与管理子系统(agent_tools)。

消费 agent_loop 原语(LoopTool/subagent/control/gate),不被引擎依赖——镜像 agent_context
的"引擎外环"先例。五类功能(主模型顶层 ≤7):**设备管理(agent)/ 运行管理(agent)/
生活服务(扁平×3)/ 知识检索(扁平)/ 执行工具(execute_proposal,横切控制,M2-refined)**。

**入口 = `build_park_runtime(...)`(`runtime.py`)**:一处串起登录链(确权)+ 运行链(治理)。
详见 `桌面/harness-park-design/工具治理与管理子系统-设计.md`(v4)。
"""
from .composition import ToolSubsystem, build_tool_subsystem
from .runtime import ParkToolRuntime, build_park_runtime

__all__ = ["build_park_runtime", "ParkToolRuntime", "build_tool_subsystem", "ToolSubsystem"]
