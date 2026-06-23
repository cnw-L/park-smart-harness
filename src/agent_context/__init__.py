"""中圈·上下文管理子系统(供给层)。

实现 agent_loop 的 ContextAssembler 接缝背后的真实供给:系统提示词构造、记忆/知识层、
历史缩减、任务层渲染。引擎(agent_loop)保持瘦,只携带 engine-opaque 的 principal;
真实供给在此包。设计见 `上下文管理子系统-设计.md`。
"""
