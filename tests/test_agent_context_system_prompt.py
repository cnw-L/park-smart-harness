"""Task 1 — 固定层系统提示词 composer。

主/子各一份独立完整提示词;compose 是 PromptSelection 的纯函数(字节稳定)。
"""
from __future__ import annotations

from agent_context.system_prompt import (
    PromptSelection,
    compose,
    fingerprint,
)


def _sel(role: str, family: str = "default", platform: str = "web") -> PromptSelection:
    return PromptSelection(role=role, model_family=family, platform=platform)


def test_main_profile():
    s = compose(_sel("main"))
    assert "智慧园区 AI 助手" in s
    assert "控制走确认卡" in s             # v6:卡片就是确认
    assert "等用户确认再执行" not in s     # v6 删去:与 execute_proposal 描述矛盾、致双重确认
    assert "绝不在文本里反问" in s         # v6:不文本反问"是否确认"
    assert "不猜" in s
    assert "不臆造" in s
    assert "不越权" not in s              # v2 删去:权限不进 prompt、模型无法自检越权,真拦在闸+后端
    assert "只读不控制" not in s          # 那是子的


def test_device_sub_profile():
    s = compose(_sel("device_sub"))
    assert "设备域" in s and "工具" in s     # v8:子 agent 当工具用(有界、返回结果或需澄清)
    assert "需澄清" in s                     # v8:信息不足→交回主控,不空转
    assert "只读不控制" in s
    assert "不臆造" in s
    assert "不越权" not in s              # v2 删去(同主):子也无从自检授权设备集
    assert "控制走确认卡" not in s        # 那是主的(发起确认是主会话的活)


def test_unknown_role_falls_back_to_main():
    assert compose(_sel("leaf-weird")) == compose(_sel("main"))


def test_compose_pure_byte_stable(monkeypatch):
    """同一 selection 每次产同一字节;不读时间(monkeypatch 不影响)。"""
    import time
    monkeypatch.setattr(time, "time", lambda: 999.0)
    a = compose(_sel("main"))
    b = compose(_sel("main"))
    assert a == b


def test_from_config_parses_axes():
    class _Cfg:
        role = "main"
        model = "qwen3.5-9b"
    sel = PromptSelection.from_config(_Cfg())
    assert sel.role == "main"
    assert sel.model_family == "qwen"
    assert sel.platform == "web"


def test_from_config_leaf_maps_to_device_sub():
    class _Cfg:
        role = "leaf"
        model = "chat"
    sel = PromptSelection.from_config(_Cfg())
    assert sel.role == "device_sub"
    assert sel.model_family == "default"


def test_fingerprint_changes_with_axis():
    base = fingerprint(_sel("main"))
    assert fingerprint(_sel("main")) == base
    assert fingerprint(_sel("device_sub")) != base
    assert fingerprint(_sel("main", family="qwen")) != base
