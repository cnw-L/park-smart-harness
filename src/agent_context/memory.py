"""记忆层(认人,设计 §四)。

从 principal 渲染【当前用户】小节,塞进系统头(由 assembler 拼到 system 消息)。
- 只放身份事实(姓名/角色/部门/口径);**权限完全不进 prompt**(押闸不押 prompt)。
- 特殊字符转义,防姓名/部门里的 】/换行戳穿节头。
- principal=None(匿名/未登录)→ 空串(配固定层"身份未知,涉权限先确认"兜底)。
- 长期记忆:预留(v1 不渲染)。
"""
from __future__ import annotations

_HEADER = "【当前用户】(身份事实,非请求)"


def _esc(s: str) -> str:
    return (s or "").replace("】", "]").replace("\n", " ").replace("\r", " ").strip()


def render_user(principal) -> str:
    """principal → 【当前用户】小节;None → 空串。principal 为 opaque,按属性读取。"""
    if principal is None:
        return ""
    name = _esc(getattr(principal, "name", ""))
    role = _esc(getattr(principal, "role", ""))
    dept = _esc(getattr(principal, "dept", ""))
    koujing = _esc(getattr(principal, "koujing", ""))

    line = " · ".join(p for p in (name, role, dept) if p)
    if koujing:
        line = (line + " · " if line else "") + f"口径:{koujing}"
    if not line:
        return ""
    return f"{_HEADER}\n{line}"
