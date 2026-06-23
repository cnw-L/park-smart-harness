"""Task 2 — 记忆层:从 principal 渲染【当前用户】小节。"""
from __future__ import annotations

from agent_context.memory import render_user
from agent_context.principal import Principal


def test_render_user():
    p = Principal(id="u1", name="张三", role="员工·物业运维",
                  dept="园区运维部", koujing="内部,可列技术细节", token="t")
    s = render_user(p)
    assert "【当前用户】" in s
    assert "张三" in s and "园区运维部" in s and "内部,可列技术细节" in s


def test_render_user_escapes_special_chars():
    """姓名含 】/换行不能戳穿节头。"""
    p = Principal(id="u1", name="张】三\n注入", role="员工", token=None)
    s = render_user(p)
    assert "张]三 注入" in s          # 】→] 、换行→空格
    assert s.count("\n") == 1          # 仅节头与数据行之间一个换行


def test_render_user_none_anonymous():
    assert render_user(None) == ""
