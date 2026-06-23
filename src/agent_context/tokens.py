"""token 估算器(设计 §五)。

不引真 tokenizer:char-based 粗估,只为压缩 fail-safe 触发用——要的是**单调 + 大致缩放**,
不要精确。中文偏保守(略高估,早点触发更安全)。
"""
from __future__ import annotations


def estimate_tokens(messages) -> int:
    chars = 0
    for m in messages:
        chars += len(m.content or "") + len(m.reasoning or "")
        for tc in (m.tool_calls or []):
            chars += len(tc.name or "") + len(str(tc.arguments))
    # 中英混合粗估:约 2 字符/token(中文偏 1、英文/JSON 偏 4,取中并偏保守)。
    return chars // 2 + 1
