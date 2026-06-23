"""身份脊柱(principal)。

记忆层、知识层权限透传、闸 deny **共用同一身份对象**。身份在会话入口(网关/服务端)
登录时解析一次(SSO 员工企微 / 市民 openid → 后端查画像),set 到 Conversation 上;
**不从消息日志加载、不持久化进 log**(身份来自 auth,不来自对话)。

对 `agent_loop` 引擎是 opaque 的——引擎只把它从 Conversation 透到 ToolContext,不解释;
解释/渲染/透传由中圈(记忆层渲【当前用户】、知识层透 token、闸读 role/scope)负责。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    """当前用户身份(画像)。权限明细不进 prompt——闸/后端用 token+role 判,prompt 只用于口径。"""
    id: str
    name: str
    role: str                 # 员工 / 市民
    dept: str = ""
    koujing: str = ""         # 口径标签(如"内部,可列技术细节")
    token: str | None = None  # 透传后端做权限过滤的原始身份;None=匿名→后端默认查(须最小权限)
    permissions: tuple[str, ...] = ()  # 工具可见性/deny 闸用的权限码;会话开始从后端 /user/info 灌一次
